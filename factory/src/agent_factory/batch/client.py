"""Admission and cancellation helpers for `BatchWorkflow`."""

from __future__ import annotations

import asyncio
from pathlib import Path

from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy

from ..config import Config
from .manifest import load_job_spec
from .models import BatchJobSpec, workflow_id
from .status import batch_status, receipt_doc
from .workflow import BatchWorkflow

TERMINAL = {"BATCH_SUCCESS", "BATCH_FAILED", "BATCH_CANCELED"}


async def start_batch(client: Client, spec: BatchJobSpec) -> WorkflowHandle:
    """Start exactly one workflow per job id; duplicates are rejected by Temporal."""
    return await client.start_workflow(
        BatchWorkflow.run, spec, id=workflow_id(spec.job_id), task_queue=spec.task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        id_conflict_policy=WorkflowIDConflictPolicy.FAIL)


async def submit(client: Client, manifest_path: str | Path) -> WorkflowHandle:
    return await start_batch(client, load_job_spec(manifest_path))


async def cancel_batch(client: Client, job_id: str, timeout: float = 30) -> dict:
    """Request cancellation and wait for the durable BATCH_CANCELED receipt.

    The workflow, not this helper, owns the terminal state. Polling the receipt
    avoids returning a stale RUNNING snapshot while the workflow task that writes
    the terminal receipt is still queued.
    """
    handle = client.get_workflow_handle(workflow_id(job_id))
    await handle.cancel()
    # The workflow, not this helper, owns the terminal state. Poll the durable
    # receipt instead of returning a stale RUNNING snapshot while the workflow
    # task that writes the terminal receipt is still queued.
    state_dir = Config.from_env().state_dir
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        document = receipt_doc(state_dir, job_id)
        if document is not None and document.get("status") in TERMINAL:
            return await batch_status(client, job_id)
        await asyncio.sleep(0.2)
    return await batch_status(client, job_id)


__all__ = ["cancel_batch", "start_batch", "submit", "workflow_id"]
