"""Temporal activities for the batch path.

The workflow never touches the filesystem. These activities do, are repeat-safe
and heartbeat while a child process runs:

- `validate_manifest` re-reads the frozen manifest, checks `manifest_hash` and
  `script_sha`, and fills the durable checkpoint paths;
- `load_checkpoint` re-verifies inputs and the checkpoint fence before reuse;
- `run_unit` runs one allowlisted argv under resource limits;
- `write_checkpoint` atomically records the completed unit;
- `run_dq` applies the optional deterministic data-quality contract;
- `record_batch` / `finalize_batch` write the existing receipt format.

No model, no provider SDK, no arbitrary shell.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from .. import faults, receipts
from ..activities import BASE_ENV
from ..config import Config
from . import checkpoints, manifest
from .models import (DqContract, DqResult, BatchJobSpec, BatchUnit, BatchUnitResult,
                     Checkpoint, CheckpointState, ResourceLimits, TERMINAL_STATUSES)
from .runner import BatchRunError, run_limited, runner_argv
from .util import sha256_bytes

NON_RETRYABLE = (
    "BatchManifestInvalid", "BatchScriptTampered", "BatchInputMismatch",
    "BatchOutputMissing", "BatchUnitConfig", "BatchCheckpointInvalid",
    "BatchDqInvalid",
)


def _invalid(message: str, kind: str = "BatchManifestInvalid") -> ApplicationError:
    return ApplicationError(message[:1000], type=kind, non_retryable=True)


def _tail(text: str, size: int = 2000) -> str:
    return text[-size:]


def _env(plan: BatchJobSpec, unit_id: str) -> dict[str, str]:
    env = {key: os.environ[key] for key in BASE_ENV if key in os.environ}
    env.update(plan.env)
    env.update(
        FACTORY_BATCH_JOB_ID=plan.job_id,
        FACTORY_BATCH_UNIT_ID=unit_id,
        FACTORY_BATCH_MANIFEST_HASH=plan.manifest_hash,
        FACTORY_BATCH_SCRIPT_SHA=plan.script_sha,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPYCACHEPREFIX=str(Config.from_env().work_root / "batch" / plan.job_id / "pycache"),
        PWD=plan.workspace,
    )
    return env


def _paths(plan: BatchJobSpec) -> tuple[Path, Path]:
    cfg = Config.from_env()
    return cfg.state_dir, cfg.work_root / "batch" / plan.job_id


def _remove_outputs(plan: BatchJobSpec, unit: BatchUnit) -> None:
    root = Path(plan.workspace).resolve()
    for rel in unit.outputs:
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise _invalid(f"output escapes workspace: {rel}", "BatchUnitConfig") from exc
        if path.is_dir():
            raise _invalid(f"declared output is a directory: {rel}", "BatchUnitConfig")
        path.unlink(missing_ok=True)


@activity.defn
async def validate_manifest(spec: BatchJobSpec, expected_workflow_id: str) -> BatchJobSpec:
    """Freeze the submitted identity and verify the manifest file still matches it."""

    def check() -> BatchJobSpec:
        if not spec.manifest_path:
            raise manifest.BatchManifestError("manifest_path is required for batch execution")
        frozen = manifest.load_job_spec(spec.manifest_path)
        if frozen.job_id != spec.job_id:
            raise manifest.BatchManifestError(
                f"manifest job_id changed: submitted {spec.job_id}, file has {frozen.job_id}")
        if frozen.manifest_hash != spec.manifest_hash:
            raise manifest.BatchManifestError("manifest changed after submission")
        if frozen.script_sha != spec.script_sha:
            raise manifest.BatchManifestError("script_sha changed after submission")
        expected = f"batch-{frozen.job_id}"
        if expected_workflow_id != expected:
            raise manifest.BatchManifestError(
                f"workflow id {expected_workflow_id!r} does not match {expected!r}")
        state_dir = Config.from_env().state_dir
        for unit in frozen.units:
            unit.checkpoint = str(
                checkpoints.checkpoint_path(state_dir, frozen.job_id, unit.unit_id))
        return frozen

    try:
        return await asyncio.to_thread(check)
    except manifest.BatchManifestError as exc:
        raise _invalid(str(exc)) from exc


@activity.defn
async def load_checkpoint(plan: BatchJobSpec, unit: BatchUnit) -> CheckpointState:
    """Verify inputs, the checkpoint digest and every output hash before reuse."""

    def read() -> CheckpointState:
        try:
            manifest.verify_inputs(plan, unit)
        except manifest.BatchManifestError as exc:
            raise exc
        return checkpoints.read_checkpoint(Config.from_env().state_dir, plan, unit)

    try:
        state = await asyncio.to_thread(read)
    except manifest.BatchManifestError as exc:
        raise _invalid(str(exc), "BatchInputMismatch") from exc
    activity.heartbeat({"unit_id": unit.unit_id, "phase": "checkpoint",
                        "valid": state.valid, "reason": state.reason})
    return state


@activity.defn
async def run_unit(plan: BatchJobSpec, unit: BatchUnit) -> BatchUnitResult:
    """Run one unit once. A valid checkpoint is reused before any side effect.

    The activity writes its own checkpoint before returning. If the worker dies
    after the unit's files exist but before this activity reports completion,
    the retry reads that checkpoint and returns REUSED instead of running the
    unit twice.
    """
    started = time.monotonic()
    state_dir = Config.from_env().state_dir

    def reuse() -> CheckpointState:
        manifest.verify_script(plan)
        manifest.verify_inputs(plan, unit)
        return checkpoints.read_checkpoint(state_dir, plan, unit)

    try:
        existing = await asyncio.to_thread(reuse)
    except manifest.BatchManifestError as exc:
        raise _invalid(str(exc), "BatchInputMismatch") from exc
    if existing is not None and existing.valid and existing.checkpoint is not None:
        activity.heartbeat({"unit_id": unit.unit_id, "phase": "reused"})
        return BatchUnitResult(
            unit_id=unit.unit_id, status="REUSED", exit_code=0,
            outputs=existing.checkpoint.outputs,
            checkpoint=str(checkpoints.checkpoint_path(state_dir, plan.job_id, unit.unit_id)),
            seconds=time.monotonic() - started)

    def prepare() -> Path:
        try:
            manifest.verify_script(plan)
            manifest.verify_inputs(plan, unit)
            _remove_outputs(plan, unit)
        except manifest.BatchManifestError as exc:
            raise exc
        return manifest.resolve_inside(Path(plan.workspace), plan.script, "script")

    try:
        script = await asyncio.to_thread(prepare)
    except manifest.BatchManifestError as exc:
        kind = "BatchScriptTampered" if "script" in str(exc).lower() else "BatchInputMismatch"
        raise _invalid(str(exc), kind) from exc

    _, logs = _paths(plan)
    log_path = logs / f"{unit.unit_id}.log"
    argv = runner_argv(plan.runner_id, script, plan.args)
    limits = unit.resource_limits

    def on_beat(proc) -> None:
        activity.heartbeat({"unit_id": unit.unit_id, "phase": "running", "pid": proc.pid})

    activity.heartbeat({"unit_id": unit.unit_id, "phase": "starting"})
    try:
        outcome = await run_limited(argv, Path(plan.workspace), _env(plan, unit.unit_id),
                                    log_path, limits, on_beat)
    except BatchRunError as exc:
        retryable = exc.kind in {"output", "timeout", "signal", "cpu"}
        raise ApplicationError(
            f"unit {unit.unit_id} {exc.kind}: {exc}"[:1000],
            type="BatchUnitFailed" if retryable else "BatchUnitConfig",
            non_retryable=not retryable) from exc

    if outcome.exit_code != 0:
        raise ApplicationError(
            f"unit {unit.unit_id} exited {outcome.exit_code}: "
            f"{_tail(outcome.log_tail)}"[:1000], type="BatchUnitFailed")

    def checkpoint() -> Checkpoint:
        return checkpoints.write_checkpoint(state_dir, plan, unit)

    try:
        written = await asyncio.to_thread(checkpoint)
    except checkpoints.CheckpointError as exc:
        raise _invalid(f"unit {unit.unit_id}: {exc}", "BatchOutputMissing") from exc

    index = next(index for index, candidate in enumerate(plan.units)
                 if candidate.unit_id == unit.unit_id)
    if faults.hit(state_dir, "batch_after_checkpoint", index) == "crash":
        os._exit(137)  # test-only: simulate a worker killed after the checkpoint

    activity.heartbeat({"unit_id": unit.unit_id, "phase": "completed"})
    return BatchUnitResult(
        unit_id=unit.unit_id,
        status="COMPLETED",
        exit_code=outcome.exit_code,
        outputs=written.outputs,
        checkpoint=written.path,
        seconds=time.monotonic() - started,
        log_tail=_tail(outcome.log_tail),
    )


@activity.defn
async def write_checkpoint(plan: BatchJobSpec, unit: BatchUnit) -> Checkpoint:
    """Hash the outputs again and atomically write the durable checkpoint."""

    def write() -> Checkpoint:
        return checkpoints.write_checkpoint(Config.from_env().state_dir, plan, unit)

    try:
        checkpoint = await asyncio.to_thread(write)
    except checkpoints.CheckpointError as exc:
        raise _invalid(f"unit {unit.unit_id}: {exc}", "BatchOutputMissing") from exc
    activity.heartbeat({"unit_id": unit.unit_id, "phase": "checkpointed"})
    return checkpoint


def _dq_limits(contract: DqContract) -> ResourceLimits:
    return ResourceLimits(
        timeout_seconds=contract.timeout_seconds,
        cpu_seconds=contract.timeout_seconds,
        memory_mb=contract.memory_mb,
        output_bytes=contract.output_bytes,
    )


@activity.defn
async def run_dq(plan: BatchJobSpec) -> DqResult:
    """Run the optional DQ script and report PASS/FAIL/MISSING/INVALID explicitly."""
    contract = plan.dq_contract
    if contract is None:
        return DqResult(status="SKIPPED")

    started = time.monotonic()
    try:
        script = await asyncio.to_thread(
            manifest.resolve_inside, Path(plan.workspace), contract.script,
            "dq_contract.script")
        actual = await asyncio.to_thread(manifest.sha256_file, script)
        if actual != contract.script_sha:
            raise manifest.BatchManifestError(
                f"dq script_sha mismatch: expected {contract.script_sha}, got {actual}")
    except (manifest.BatchManifestError, OSError) as exc:
        raise _invalid(str(exc), "BatchDqInvalid") from exc

    _, logs = _paths(plan)
    log_path = logs / "dq.log"
    argv = runner_argv(contract.runner or plan.runner_id, script, contract.args)
    env = _env(plan, "dq")

    def on_beat(proc) -> None:
        activity.heartbeat({"phase": "dq", "pid": proc.pid})

    activity.heartbeat({"phase": "dq"})
    try:
        outcome = await run_limited(argv, Path(plan.workspace), env, log_path,
                                    _dq_limits(contract), on_beat)
    except BatchRunError as exc:
        return DqResult(status="ERROR", exit_code=exc.exit_code,
                        expected_exit=contract.expected_exit,
                        script_sha=contract.script_sha, error=str(exc)[:500],
                        seconds=time.monotonic() - started, log_tail=_tail(exc.log_tail))

    report: dict[str, Any] | None = None
    report_sha = ""
    report_path = contract.report_path
    result = DqResult(status="PASS", exit_code=outcome.exit_code,
                      expected_exit=contract.expected_exit,
                      script_sha=contract.script_sha, report_path=report_path,
                      seconds=time.monotonic() - started,
                      log_tail=_tail(outcome.log_tail))
    if outcome.exit_code != contract.expected_exit:
        result.status = "FAIL"
        result.error = (f"dq exit {outcome.exit_code} != expected "
                        f"{contract.expected_exit}")
        return result
    if report_path:
        path = manifest.resolve_inside(Path(plan.workspace), report_path,
                                       "dq_contract.report_path")
        if not path.is_file():
            result.status = "MISSING"
            result.error = f"dq report is missing: {report_path}"
            return result
        data = path.read_bytes()
        report_sha = sha256_bytes(data)
        try:
            report = json.loads(data)
        except ValueError as exc:
            result.status = "INVALID"
            result.report_sha256 = report_sha
            result.error = f"dq report is not valid JSON: {exc}"
            return result
        if not isinstance(report, dict):
            result.status = "INVALID"
            result.report_sha256 = report_sha
            result.error = "dq report is not a JSON object"
            return result
        expected = contract.expected_json or {}
        mismatch = [key for key, value in expected.items() if report.get(key) != value]
        if mismatch:
            result.status = "FAIL"
            result.report_sha256 = report_sha
            result.report = report
            result.error = f"dq report mismatch on {sorted(mismatch)}"
            return result
    result.report_sha256 = report_sha
    result.report = report
    return result


@activity.defn
async def record_batch(key: str, data: dict, metrics: dict | None = None) -> str:
    """Write one receipt entry for the batch workflow; repeats are no-ops."""
    info = activity.info()
    workflow_id = info.workflow_id
    if not workflow_id.startswith("batch-"):
        raise ApplicationError(f"not a batch workflow id: {workflow_id}",
                               type="BatchReceiptInvalid", non_retryable=True)
    job_id = workflow_id.removeprefix("batch-")
    cfg = Config.from_env()
    return await asyncio.to_thread(
        receipts.record, cfg.state_dir, workflow_id, job_id, key, data, metrics)


@activity.defn
async def finalize_batch(status: str) -> dict:
    """Freeze the receipt with BATCH_SUCCESS / BATCH_FAILED / BATCH_CANCELED."""
    if status not in TERMINAL_STATUSES:
        raise ApplicationError(f"invalid batch terminal status {status!r}",
                               type="BatchReceiptInvalid", non_retryable=True)
    info = activity.info()
    workflow_id = info.workflow_id
    if not workflow_id.startswith("batch-"):
        raise ApplicationError(f"not a batch workflow id: {workflow_id}",
                               type="BatchReceiptInvalid", non_retryable=True)
    job_id = workflow_id.removeprefix("batch-")
    cfg = Config.from_env()
    doc = await asyncio.to_thread(receipts.finalize, cfg.state_dir, workflow_id, job_id, status)
    problems = receipts.validate(doc)
    if problems:
        raise ApplicationError(f"invalid receipt: {problems}", type="ReceiptInvalid",
                               non_retryable=True)
    return {"path": str(receipts.receipt_path(cfg.state_dir, workflow_id)),
            "digest": doc["digest"], "status": doc["status"]}


ALL = [validate_manifest, load_checkpoint, run_unit, write_checkpoint, run_dq,
       record_batch, finalize_batch]


__all__ = ["ALL", "finalize_batch", "load_checkpoint", "record_batch", "run_dq",
           "run_unit", "validate_manifest", "write_checkpoint"]
