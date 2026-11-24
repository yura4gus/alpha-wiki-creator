"""Frozen batch manifest parsing and validation.

A manifest is a JSON document. Its `manifest_hash` is the SHA-256 of the same
document with the `manifest_hash` key removed, encoded as canonical JSON
(sorted keys, no whitespace). A second SHA pins the script bytes.

Every path is relative to the declared workspace and is resolved before use, so
`..`, absolute paths and symlinks that escape the workspace are rejected. The
manifest is strict: unknown keys fail instead of being ignored, because an
ignored `env` or `args` key would be an unreviewed execution path.

No process is started here and no network/model call is made.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from .models import (BATCH_ENV_ALLOWLIST, DqContract, BatchJobSpec, BatchUnit, ResourceLimits,
                     RetryPolicySpec, RUNNERS)
from .util import sha256_file, sha256_json

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TOP_LEVEL = {
    "job_id", "runner_id", "manifest_hash", "workspace", "script", "script_sha",
    "args", "env", "units", "retry_policy", "dq_contract", "task_queue",
    "heartbeat_timeout_seconds",
}
UNIT_KEYS = {"unit_id", "inputs", "outputs", "resource_limits", "retry_policy"}
LIMIT_KEYS = {"timeout_seconds", "cpu_seconds", "memory_mb", "output_bytes"}
RETRY_KEYS = {"max_attempts", "initial_interval_seconds"}
DQ_KEYS = {"runner", "script", "script_sha", "args", "expected_exit", "expected_json",
           "report_path", "timeout_seconds", "memory_mb", "output_bytes"}

SCRIPT_SUFFIX = {"python": ".py", "bash": ".sh"}


class BatchManifestError(ValueError):
    """The manifest, its hash, its script or one of its paths is not acceptable."""


def compute_manifest_hash(manifest: dict[str, Any]) -> str:
    body = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return sha256_json(body)


def _reject_unknown(mapping: dict, allowed: set[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise BatchManifestError(f"{where}: unknown keys {unknown}")


def validate_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value) or value in {".", ".."}:
        raise BatchManifestError(
            f"{where}: must match [A-Za-z0-9][A-Za-z0-9._-]{{0,63}}")
    return value


def _string(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise BatchManifestError(f"{where}: must be a non-empty string")
    if "\x00" in value:
        raise BatchManifestError(f"{where}: NUL byte is not allowed")
    return value


def _integer(value: Any, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise BatchManifestError(f"{where}: must be an integer in [{low}, {high}]")
    return value


def _hex(value: Any, where: str) -> str:
    if not isinstance(value, str) or not HEX_RE.fullmatch(value):
        raise BatchManifestError(f"{where}: must be a lowercase SHA-256 hex digest")
    return value


def safe_relative(value: Any, where: str) -> str:
    """Reject absolute paths, traversal and platform separator tricks."""
    text = _string(value, where)
    if text.startswith(("/", "~")) or "\\" in text or "\x00" in text:
        raise BatchManifestError(f"{where}: must be a relative POSIX path inside the workspace")
    parts = text.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise BatchManifestError(f"{where}: path traversal or empty segment is not allowed")
    return text


def resolve_inside(root: Path, relative: str, where: str) -> Path:
    """Resolve a validated relative path and prove it stays inside `root`."""
    root = root.resolve()
    candidate = (root / PurePosixPath(relative)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise BatchManifestError(f"{where}: path escapes the workspace: {relative}") from exc
    return candidate


def _validate_args(args: Any, where: str) -> list[str]:
    if args is None:
        return []
    if not isinstance(args, list) or len(args) > 64:
        raise BatchManifestError(f"{where}: must be a list of at most 64 strings")
    result: list[str] = []
    for index, item in enumerate(args):
        text = _string(item, f"{where}[{index}]", allow_empty=True)
        if len(text) > 4096 or any(char in text for char in "\r\n"):
            raise BatchManifestError(f"{where}[{index}]: too long or contains a newline")
        lowered = text.lower()
        if text.startswith(("/", "~")) or lowered.startswith("file://"):
            raise BatchManifestError(f"{where}[{index}]: absolute paths are not allowed")
        for value in text.split("=")[1:]:
            if value.startswith(("/", "~")):
                raise BatchManifestError(
                    f"{where}[{index}]: absolute paths are not allowed")
        for piece in text.replace("=", "/").split("/"):
            if piece == "..":
                raise BatchManifestError(f"{where}[{index}]: path traversal is not allowed")
        result.append(text)
    return result


def _validate_env(env: Any) -> dict[str, str]:
    if env is None:
        return {}
    if not isinstance(env, dict):
        raise BatchManifestError("env: must be an object of name -> string")
    result: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(key, str) or not ENV_RE.fullmatch(key):
            raise BatchManifestError(f"env: invalid variable name {key!r}")
        if key not in BATCH_ENV_ALLOWLIST:
            raise BatchManifestError(f"env: {key!r} is not in the batch allowlist")
        if not isinstance(value, str) or len(value) > 4096 or "\x00" in value:
            raise BatchManifestError(f"env.{key}: must be a string of at most 4096 bytes")
        result[key] = value
    return result


def _resource_limits(data: Any, where: str) -> ResourceLimits:
    if data is None:
        return ResourceLimits()
    if not isinstance(data, dict):
        raise BatchManifestError(f"{where}: must be an object")
    _reject_unknown(data, LIMIT_KEYS, where)
    return ResourceLimits(
        timeout_seconds=_integer(data.get("timeout_seconds", 300),
                                 f"{where}.timeout_seconds", 1, 86400),
        cpu_seconds=_integer(data.get("cpu_seconds", 300), f"{where}.cpu_seconds", 1, 86400),
        memory_mb=_integer(data.get("memory_mb", 1024), f"{where}.memory_mb", 64, 131072),
        output_bytes=_integer(data.get("output_bytes", 1_000_000),
                              f"{where}.output_bytes", 1024, 100_000_000),
    )


def _retry_policy(data: Any, where: str) -> RetryPolicySpec:
    if data is None:
        return RetryPolicySpec()
    if not isinstance(data, dict):
        raise BatchManifestError(f"{where}: must be an object")
    _reject_unknown(data, RETRY_KEYS, where)
    return RetryPolicySpec(
        max_attempts=_integer(data.get("max_attempts", 2), f"{where}.max_attempts", 1, 5),
        initial_interval_seconds=_integer(data.get("initial_interval_seconds", 1),
                                          f"{where}.initial_interval_seconds", 1, 60),
    )


def unit_material(unit: BatchUnit) -> dict[str, Any]:
    """Canonical identity of one unit, excluding its assigned id and checkpoint."""
    return {
        "inputs": dict(sorted(unit.inputs.items())),
        "outputs": list(unit.outputs),
        "resource_limits": {
            "timeout_seconds": unit.resource_limits.timeout_seconds,
            "cpu_seconds": unit.resource_limits.cpu_seconds,
            "memory_mb": unit.resource_limits.memory_mb,
            "output_bytes": unit.resource_limits.output_bytes,
        },
        "retry_policy": None if unit.retry_policy is None else {
            "max_attempts": unit.retry_policy.max_attempts,
            "initial_interval_seconds": unit.retry_policy.initial_interval_seconds,
        },
    }


def unit_fingerprint(unit: BatchUnit) -> str:
    return sha256_json(unit_material(unit))


def inputs_hash(inputs: dict[str, Optional[str]]) -> str:
    return sha256_json(dict(sorted(inputs.items())))


def _unit(data: Any, index: int, workspace: Path, seen_ids: set[str],
          seen_outputs: dict[str, str]) -> BatchUnit:
    where = f"units[{index}]"
    if not isinstance(data, dict):
        raise BatchManifestError(f"{where}: must be an object")
    _reject_unknown(data, UNIT_KEYS, where)

    raw_inputs = data.get("inputs") or {}
    if not isinstance(raw_inputs, dict):
        raise BatchManifestError(f"{where}.inputs: must be an object")
    inputs: dict[str, Optional[str]] = {}
    for rel, expected in raw_inputs.items():
        safe = safe_relative(rel, f"{where}.inputs")
        path = resolve_inside(workspace, safe, f"{where}.inputs.{safe}")
        if not path.is_file():
            raise BatchManifestError(f"{where}.inputs.{safe}: file does not exist")
        if expected is not None:
            pinned = _hex(expected, f"{where}.inputs.{safe}")
            actual = sha256_file(path)
            if actual != pinned:
                raise BatchManifestError(
                    f"{where}.inputs.{safe}: sha256 mismatch (expected {pinned}, got {actual})")
        inputs[safe] = expected

    raw_outputs = data.get("outputs") or []
    if not isinstance(raw_outputs, list):
        raise BatchManifestError(f"{where}.outputs: must be a list")
    outputs: list[str] = []
    for rel in raw_outputs:
        safe = safe_relative(rel, f"{where}.outputs")
        if safe in outputs:
            raise BatchManifestError(f"{where}.outputs: duplicate path {safe}")
        path = resolve_inside(workspace, safe, f"{where}.outputs.{safe}")
        if path.exists() and path.is_dir():
            raise BatchManifestError(f"{where}.outputs.{safe}: must be a file path")
        outputs.append(safe)

    limits = _resource_limits(data.get("resource_limits"), f"{where}.resource_limits")
    retry = None
    if data.get("retry_policy") is not None:
        retry = _retry_policy(data["retry_policy"], f"{where}.retry_policy")

    candidate = BatchUnit(unit_id="", inputs=inputs, outputs=outputs,
                          resource_limits=limits, retry_policy=retry)
    material_hash = sha256_json(unit_material(candidate))
    if "unit_id" in data:
        unit_id = validate_id(data["unit_id"], f"{where}.unit_id")
    else:
        unit_id = f"u-{material_hash[:16]}"
    if unit_id in seen_ids:
        raise BatchManifestError(f"{where}.unit_id: duplicate unit id {unit_id!r}")
    seen_ids.add(unit_id)
    for safe in outputs:
        if safe in seen_outputs:
            raise BatchManifestError(
                f"{where}.outputs: {safe} is already declared by {seen_outputs[safe]}")
        seen_outputs[safe] = f"units[{index}]"
    candidate.unit_id = unit_id
    candidate.fingerprint = material_hash
    return candidate


def _dq_contract(data: Any, workspace: Path, runner_id: str) -> DqContract:
    if not isinstance(data, dict):
        raise BatchManifestError("dq_contract: must be an object")
    _reject_unknown(data, DQ_KEYS, "dq_contract")
    runner = data.get("runner") or runner_id
    if runner not in RUNNERS:
        raise BatchManifestError(f"dq_contract.runner: unknown runner {runner!r}")
    script = safe_relative(data.get("script"), "dq_contract.script")
    path = resolve_inside(workspace, script, "dq_contract.script")
    if not path.is_file():
        raise BatchManifestError("dq_contract.script: file does not exist")
    suffix = SCRIPT_SUFFIX.get(runner)
    if suffix and path.suffix != suffix:
        raise BatchManifestError(
            f"dq_contract.script: {runner} scripts must end with {suffix}")
    script_sha = _hex(data.get("script_sha"), "dq_contract.script_sha")
    actual = sha256_file(path)
    if actual != script_sha:
        raise BatchManifestError(
            f"dq_contract.script: sha256 mismatch (expected {script_sha}, got {actual})")
    report_path = data.get("report_path") or ""
    if report_path:
        report_path = safe_relative(report_path, "dq_contract.report_path")
        # Resolve now, but the report is allowed to be absent: MISSING is a
        # reported outcome, not a manifest error.
        resolve_inside(workspace, report_path, "dq_contract.report_path")
    expected_json = data.get("expected_json")
    if expected_json is not None and not isinstance(expected_json, dict):
        raise BatchManifestError("dq_contract.expected_json: must be an object")
    return DqContract(
        script=script,
        script_sha=script_sha,
        runner=runner,
        args=_validate_args(data.get("args"), "dq_contract.args"),
        expected_exit=_integer(data.get("expected_exit", 0),
                               "dq_contract.expected_exit", 0, 255),
        expected_json=expected_json,
        report_path=report_path,
        timeout_seconds=_integer(data.get("timeout_seconds", 120),
                                 "dq_contract.timeout_seconds", 1, 3600),
        memory_mb=_integer(data.get("memory_mb", 1024), "dq_contract.memory_mb", 64, 131072),
        output_bytes=_integer(data.get("output_bytes", 1_000_000),
                              "dq_contract.output_bytes", 1024, 100_000_000),
    )


def parse_manifest(manifest: dict[str, Any], manifest_path: str = "") -> BatchJobSpec:
    """Validate one decoded manifest. Raises BatchManifestError on any mismatch."""
    if not isinstance(manifest, dict):
        raise BatchManifestError("manifest: must be a JSON object")
    _reject_unknown(manifest, TOP_LEVEL, "manifest")
    if "manifest_hash" not in manifest:
        raise BatchManifestError("manifest: manifest_hash is required")
    expected_hash = _hex(manifest["manifest_hash"], "manifest.manifest_hash")
    actual_hash = compute_manifest_hash(manifest)
    if actual_hash != expected_hash:
        raise BatchManifestError(
            f"manifest_hash mismatch: expected {actual_hash}, manifest has {expected_hash}")

    job_id = validate_id(manifest.get("job_id"), "job_id")
    runner_id = manifest.get("runner_id")
    if runner_id not in RUNNERS:
        raise BatchManifestError(f"runner_id: must be one of {list(RUNNERS)}")

    base = Path(manifest_path).resolve().parent if manifest_path else Path.cwd()
    raw_workspace = _string(manifest.get("workspace"), "workspace")
    workspace = Path(raw_workspace).expanduser()
    if not workspace.is_absolute():
        workspace = base / workspace
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise BatchManifestError(f"workspace: directory does not exist: {workspace}")

    script = safe_relative(manifest.get("script"), "script")
    script_path = resolve_inside(workspace, script, "script")
    if not script_path.is_file():
        raise BatchManifestError(f"script: file does not exist: {script}")
    suffix = SCRIPT_SUFFIX.get(runner_id)
    if suffix and script_path.suffix != suffix:
        raise BatchManifestError(f"script: {runner_id} scripts must end with {suffix}")
    if runner_id == "rust":
        import os
        if not os.access(script_path, os.X_OK):
            raise BatchManifestError("script: rust scripts must be executable")
    script_sha = _hex(manifest.get("script_sha"), "script_sha")
    actual_script = sha256_file(script_path)
    if actual_script != script_sha:
        raise BatchManifestError(
            f"script_sha mismatch: expected {actual_script}, manifest has {script_sha}")

    raw_units = manifest.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise BatchManifestError("units: at least one unit is required")
    seen_ids: set[str] = set()
    seen_outputs: dict[str, str] = {}
    units = [_unit(item, index, workspace, seen_ids, seen_outputs)
             for index, item in enumerate(raw_units)]

    task_queue = manifest.get("task_queue", "bsc-batch")
    if not isinstance(task_queue, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", task_queue):
        raise BatchManifestError("task_queue: must match [A-Za-z0-9._-]{1,64}")

    dq = manifest.get("dq_contract")
    return BatchJobSpec(
        job_id=job_id,
        runner_id=runner_id,
        manifest_hash=expected_hash,
        script_sha=script_sha,
        workspace=str(workspace),
        script=script,
        manifest_path=str(Path(manifest_path).resolve()) if manifest_path else "",
        args=_validate_args(manifest.get("args"), "args"),
        env=_validate_env(manifest.get("env")),
        units=units,
        retry_policy=_retry_policy(manifest.get("retry_policy"), "retry_policy"),
        dq_contract=_dq_contract(dq, workspace, runner_id) if dq is not None else None,
        task_queue=task_queue,
        heartbeat_timeout_seconds=_integer(
            manifest.get("heartbeat_timeout_seconds", 30),
            "heartbeat_timeout_seconds", 5, 300),
    )


def load_job_spec(path: str | Path) -> BatchJobSpec:
    """Read a manifest file, verify its frozen hashes and return the executable spec."""
    source = Path(path).expanduser().resolve()
    try:
        data = json.loads(source.read_text())
    except FileNotFoundError as exc:
        raise BatchManifestError(f"manifest not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise BatchManifestError(f"manifest is not valid JSON: {exc}") from exc
    return parse_manifest(data, manifest_path=str(source))


def verify_script(spec: BatchJobSpec) -> None:
    """Re-check the pinned script bytes immediately before execution."""
    workspace = Path(spec.workspace).resolve()
    path = resolve_inside(workspace, spec.script, "script")
    if not path.is_file():
        raise BatchManifestError(f"script: file does not exist: {spec.script}")
    actual = sha256_file(path)
    if actual != spec.script_sha:
        raise BatchManifestError(
            f"script_sha mismatch: expected {spec.script_sha}, got {actual}")


def verify_inputs(spec: BatchJobSpec, unit: BatchUnit) -> None:
    """Re-check every pinned input before a run or a reuse decision."""
    workspace = Path(spec.workspace).resolve()
    for rel, expected in unit.inputs.items():
        path = resolve_inside(workspace, rel, f"unit {unit.unit_id} input")
        if not path.is_file():
            raise BatchManifestError(f"unit {unit.unit_id}: input missing: {rel}")
        if expected is not None and sha256_file(path) != expected:
            raise BatchManifestError(f"unit {unit.unit_id}: input sha256 mismatch: {rel}")


def dq_script_path(spec: BatchJobSpec) -> Optional[Path]:
    if spec.dq_contract is None:
        return None
    return resolve_inside(Path(spec.workspace), spec.dq_contract.script, "dq_contract.script")
