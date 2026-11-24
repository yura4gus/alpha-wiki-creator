"""Serializable batch models shared by the manifest, activities and workflow.

These are plain dataclasses, not pydantic: the batch path must run without the
optional harness extra. Paths are strings so a workflow history is portable and
the sandbox never has to import `pathlib`.

Identity rules:

- `job_id` and every `unit_id` are path-safe tokens (`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`).
- `unit_id` is explicit when the manifest provides one. Otherwise it is derived
  from the canonical unit body, so the same manifest always yields the same id.
- `fingerprint` hashes the unit body excluding `unit_id`. It is part of the
  checkpoint fence: a changed input, output list or resource limit cannot reuse
  an older checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

BATCH_SCHEMA = "agent-factory.batch-job/1"
CHECKPOINT_SCHEMA = "agent-factory.batch-checkpoint/1"

WORKFLOW_PREFIX = "batch-"
DEFAULT_TASK_QUEUE = "bsc-batch"

BATCH_SUCCESS = "BATCH_SUCCESS"
BATCH_FAILED = "BATCH_FAILED"
BATCH_CANCELED = "BATCH_CANCELED"
TERMINAL_STATUSES = (BATCH_SUCCESS, BATCH_FAILED, BATCH_CANCELED)

RUNNERS = ("python", "bash", "rust")
RUNNER_PREFIXES = (BATCH_SUCCESS, BATCH_FAILED, BATCH_CANCELED)

# Environment names a manifest may set. The worker always adds FACTORY_BATCH_*;
# a manifest can never inject those or any other FACTORY_* value.
BASE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "USER", "SHELL")
BATCH_ENV_ALLOWLIST = frozenset(
    (*BASE_ENV, "PYTHONHASHSEED", "PYTHONUNBUFFERED", "PYTHONDONTWRITEBYTECODE",
     "RUST_BACKTRACE", "RUST_LOG", "LC_CTYPE", "TZ")
)


@dataclass
class ResourceLimits:
    """Per-unit wall/CPU/memory/output caps. Values are validated before use."""

    timeout_seconds: int = 300
    cpu_seconds: int = 300
    memory_mb: int = 1024
    output_bytes: int = 1_000_000


@dataclass
class RetryPolicySpec:
    """Bounded retry, translated into a Temporal RetryPolicy per unit."""

    max_attempts: int = 2
    initial_interval_seconds: int = 1


@dataclass
class DqContract:
    """Optional deterministic data-quality gate.

    The command is allowlisted exactly like a unit: `runner` plus a workspace
    script with a pinned SHA. No shell, no arbitrary command string.
    """

    script: str
    script_sha: str
    runner: str = ""  # empty -> the job runner
    args: list[str] = field(default_factory=list)
    expected_exit: int = 0
    expected_json: Optional[dict[str, Any]] = None
    report_path: str = ""
    timeout_seconds: int = 120
    memory_mb: int = 1024
    output_bytes: int = 1_000_000


@dataclass
class BatchUnit:
    unit_id: str
    inputs: dict[str, Optional[str]] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    retry_policy: Optional[RetryPolicySpec] = None
    checkpoint: str = ""  # durable path, filled by the worker's state dir
    fingerprint: str = ""


@dataclass
class BatchJobSpec:
    job_id: str
    runner_id: str
    manifest_hash: str
    script_sha: str
    workspace: str
    script: str
    manifest_path: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    units: list[BatchUnit] = field(default_factory=list)
    retry_policy: RetryPolicySpec = field(default_factory=RetryPolicySpec)
    dq_contract: Optional[DqContract] = None
    task_queue: str = DEFAULT_TASK_QUEUE
    heartbeat_timeout_seconds: int = 30


@dataclass
class BatchUnitResult:
    unit_id: str
    status: str  # COMPLETED | REUSED
    exit_code: int = 0
    outputs: dict[str, str] = field(default_factory=dict)
    checkpoint: str = ""
    seconds: float = 0.0
    log_tail: str = ""


@dataclass
class Checkpoint:
    """A completed unit. `digest` covers every field except `digest` and `path`."""

    job_id: str
    unit_id: str
    manifest_hash: str
    script_sha: str
    unit_fingerprint: str
    inputs_hash: str
    outputs: dict[str, str]
    status: str = "COMPLETED"
    schema: str = CHECKPOINT_SCHEMA
    digest: str = ""
    path: str = ""


@dataclass
class CheckpointState:
    """Result of reading a checkpoint: reuse only when `valid` is true."""

    valid: bool
    reason: str
    checkpoint: Optional[Checkpoint] = None


@dataclass
class DqResult:
    status: str  # SKIPPED | PASS | FAIL | MISSING | INVALID | ERROR
    exit_code: int = 0
    expected_exit: int = 0
    script_sha: str = ""
    report_path: str = ""
    report_sha256: str = ""
    report: Optional[dict[str, Any]] = None
    error: str = ""
    seconds: float = 0.0
    log_tail: str = ""


@dataclass
class BatchResult:
    job_id: str
    status: str = "RUNNING"
    manifest_hash: str = ""
    script_sha: str = ""
    units: list[BatchUnitResult] = field(default_factory=list)
    dq: Optional[DqResult] = None
    receipt_path: str = ""
    receipt_digest: str = ""
    error: str = ""


def workflow_id(job_id: str) -> str:
    return f"{WORKFLOW_PREFIX}{job_id}"
