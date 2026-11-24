"""One `BatchWorkflow` per manifest. Workflow ID: `batch-<job_id>`.

The batch path is deliberately independent of coding review and PRs:

manifest/script freeze -> per-unit checkpoint check -> run unit -> checkpoint ->
optional DQ -> frozen receipt (`BATCH_SUCCESS` / `BATCH_FAILED` / `BATCH_CANCELED`).

Work is sequential per unit. A completed unit is reused only when its checkpoint
fence and output hashes match. A worker crash leaves the durable checkpoint in
`FACTORY_STATE_DIR`; a fresh worker reads it before running anything again.

No model call, no approval gate, no PR, no scheduler.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, is_cancelled_exception

with workflow.unsafe.imports_passed_through():
    from . import activities as act
    from .models import (BATCH_CANCELED, BATCH_FAILED, BATCH_SUCCESS, BatchJobSpec,
                         BatchResult, BatchUnitResult, Checkpoint, DqResult)

SHORT = dict(
    start_to_close_timeout=timedelta(minutes=2),
    retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5),
)

DQ_BAD = {"FAIL", "MISSING", "INVALID", "ERROR"}


@workflow.defn
class BatchWorkflow:
    def __init__(self) -> None:
        self._state = "PENDING"

    @workflow.query
    def state(self) -> str:
        return self._state

    async def _rec(self, key: str, data: dict[str, Any], metrics: dict | None = None) -> None:
        await workflow.execute_activity(
            act.record_batch, args=[key, data, metrics], **SHORT)

    async def _finish(self, job_id: str, status: str, result: BatchResult) -> BatchResult:
        self._state = status
        receipt = await workflow.execute_activity(act.finalize_batch, status, **SHORT)
        result.status = status
        result.receipt_path = receipt["path"]
        result.receipt_digest = receipt["digest"]
        return result

    async def _run_unit(self, plan: BatchJobSpec, unit) -> BatchUnitResult:
        retry = unit.retry_policy or plan.retry_policy
        return await workflow.execute_activity(
            act.run_unit, args=[plan, unit],
            start_to_close_timeout=timedelta(seconds=unit.resource_limits.timeout_seconds + 30),
            heartbeat_timeout=timedelta(seconds=plan.heartbeat_timeout_seconds),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=retry.initial_interval_seconds),
                maximum_attempts=retry.max_attempts,
                non_retryable_error_types=list(act.NON_RETRYABLE)),
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED)

    @workflow.run
    async def run(self, spec: BatchJobSpec) -> BatchResult:
        result = BatchResult(job_id=spec.job_id, manifest_hash=spec.manifest_hash,
                             script_sha=spec.script_sha)
        try:
            return await self._run(spec, result)
        except (asyncio.CancelledError, ActivityError) as exc:
            if is_cancelled_exception(exc):
                await self._rec("canceled", {"at_state": self._state})
                await self._finish(spec.job_id, BATCH_CANCELED, result)
                raise
            cause = exc.cause
            result.error = f"{exc.activity_type}: {type(cause).__name__}: {cause}"[:500]
            await self._rec("failure", {"activity": exc.activity_type,
                                        "cause": type(cause).__name__})
            return await self._finish(spec.job_id, BATCH_FAILED, result)

    async def _run(self, spec: BatchJobSpec, result: BatchResult) -> BatchResult:
        self._state = "VALIDATING"
        plan = await workflow.execute_activity(
            act.validate_manifest, args=[spec, workflow.info().workflow_id], **SHORT)
        result.manifest_hash = plan.manifest_hash
        result.script_sha = plan.script_sha
        await self._rec("manifest", {
            "job_id": plan.job_id,
            "runner_id": plan.runner_id,
            "manifest_hash": plan.manifest_hash,
            "script_sha": plan.script_sha,
            "script": plan.script,
            "task_queue": plan.task_queue,
            "units": [{"unit_id": unit.unit_id, "fingerprint": unit.fingerprint,
                       "checkpoint": unit.checkpoint} for unit in plan.units],
        })

        for unit in plan.units:
            self._state = f"UNIT_{unit.unit_id}"
            state = await workflow.execute_activity(
                act.load_checkpoint, args=[plan, unit], **SHORT)
            if state.valid:
                assert state.checkpoint is not None
                unit_result = BatchUnitResult(
                    unit_id=unit.unit_id, status="REUSED", exit_code=0,
                    outputs=state.checkpoint.outputs, checkpoint=unit.checkpoint)
            else:
                unit_result = await self._run_unit(plan, unit)
                checkpoint: Checkpoint = await workflow.execute_activity(
                    act.write_checkpoint, args=[plan, unit], **SHORT)
                unit_result.checkpoint = checkpoint.path
            result.units.append(unit_result)
            await self._rec(
                f"unit-{unit.unit_id}",
                {"unit_id": unit.unit_id, "status": unit_result.status,
                 "outputs": unit_result.outputs, "checkpoint": unit_result.checkpoint,
                 "fingerprint": unit.fingerprint,
                 "checkpoint_reason": state.reason},
                {"seconds": round(unit_result.seconds, 2),
                 "exit_code": unit_result.exit_code,
                 "reused": unit_result.status == "REUSED"})

        self._state = "DQ"
        dq: DqResult = await workflow.execute_activity(
            act.run_dq, plan,
            start_to_close_timeout=timedelta(
                seconds=(plan.dq_contract.timeout_seconds if plan.dq_contract else 60) + 30),
            heartbeat_timeout=timedelta(seconds=plan.heartbeat_timeout_seconds),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1), maximum_attempts=2,
                non_retryable_error_types=["BatchDqInvalid"]),
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED)
        result.dq = dq
        await self._rec("dq", _dq_data(dq), {"seconds": round(dq.seconds, 2)})
        if dq.status in DQ_BAD:
            result.error = f"DQ {dq.status}: {dq.error}"[:500]
            return await self._finish(plan.job_id, BATCH_FAILED, result)

        self._state = "SUCCESS"
        return await self._finish(plan.job_id, BATCH_SUCCESS, result)


def _dq_data(dq: DqResult) -> dict[str, Any]:
    """Receipt content: deterministic fields only, no elapsed time."""
    return {
        "status": dq.status,
        "exit_code": dq.exit_code,
        "expected_exit": dq.expected_exit,
        "script_sha": dq.script_sha,
        "report_path": dq.report_path,
        "report_sha256": dq.report_sha256,
        "report": dq.report,
        "error": dq.error,
    }


__all__ = ["BatchWorkflow"]
