"""Deterministic batch execution over the existing factory primitives.

Small, separate path for data jobs:

- frozen JSON manifest with `manifest_hash` and `script_sha`;
- allowlisted `python` / `bash` / `rust` runners, argv only, no shell;
- per-unit durable checkpoint under `FACTORY_STATE_DIR/checkpoints/`;
- optional deterministic DQ contract;
- `BatchWorkflow` id `batch-<job_id>` and the existing receipt format.

No coding review, PR, model call, scheduler or database is involved.
"""

from .models import (BATCH_CANCELED, BATCH_FAILED, BATCH_SUCCESS, DEFAULT_TASK_QUEUE,
                     BatchJobSpec, BatchResult, BatchUnit, BatchUnitResult, Checkpoint,
                     CheckpointState, DqContract, DqResult, ResourceLimits, RetryPolicySpec,
                     workflow_id)

__all__ = [
    "BATCH_CANCELED", "BATCH_FAILED", "BATCH_SUCCESS", "DEFAULT_TASK_QUEUE",
    "BatchJobSpec", "BatchResult", "BatchUnit", "BatchUnitResult", "Checkpoint",
    "CheckpointState", "DqContract", "DqResult", "ResourceLimits", "RetryPolicySpec",
    "workflow_id",
]
