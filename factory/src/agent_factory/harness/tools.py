"""The only bridge between the harness surface and the existing factory execution path.

Four durable activity tools wrap `agent_factory.client` / `agent_factory.workflows`:

- `submit_task`  -> `client.start_task` (`task-<id>`, REJECT_DUPLICATE + FAIL)
- `get_status`   -> workflow state query + the durable receipt
- `approve_task` -> `client.decide` -> `TaskWorkflow.decide` (the one approval authority)
- `cancel_task`  -> the workflow's own cancellation path

No model provider is imported or called here, and no state is kept outside Temporal and
the receipt directory. Activity bodies return `TaskStatus.error` instead of raising, so a
failure is visible to the caller rather than retried into a fake success.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import timedelta

from temporalio.client import Client
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from temporal_agent_harness.harness import agent
from temporalio.workflow import ActivityConfig

from .. import receipts
from ..batch.client import cancel_batch as cancel_batch_workflow
from ..batch.client import start_batch
from ..batch.manifest import load_job_spec
from ..batch.models import workflow_id as batch_workflow_id
from ..batch.status import batch_status as batch_status_view
from ..client import decide, start_task, validate_batch, workflow_id
from ..config import Config
from ..connection import resolve_connect_config
from ..models import TaskSpec
from ..workflows import TaskWorkflow
from .models import (BatchCancellation, BatchStatus, BatchStatusQuery, FactoryTaskSpec, SubmitBatch,
                     SubmitTask, TaskApproval, TaskCancellation, TaskStatus, TaskStatusQuery)

# One attempt + one retry: transient RPC failures retry once, but a handled failure returns
# TaskStatus.error and Temporal never retries it. Kept short: these tools only start, query,
# decide or cancel a workflow; the task itself runs in TaskWorkflow.
TOOL_ACTIVITY = ActivityConfig(
    start_to_close_timeout=timedelta(seconds=60),
    retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=2),
)

DEFAULT_ADDRESS = "localhost:7233"

# Tool activities are loop-affine: a Client belongs to the event loop that created it. The
# cache holds the connect *task* so two concurrent tool calls share one connection, and it
# is keyed by loop identity so a new test loop (or a restarted worker) reconnects instead of
# reusing a dead channel.
_clients: dict[tuple[int, str], tuple[asyncio.AbstractEventLoop, asyncio.Task[Client]]] = {}


async def _temporal_client() -> Client:
    """Connect lazily on first use, reusing the client for this loop and address.

    The address and Cloud settings come from the factory's own resolver
    (`FACTORY_TEMPORAL_ADDRESS`, then the SDK `TEMPORAL_*` profile, then
    `localhost:7233`), so the coordinator and the TaskWorkflow worker cannot disagree.
    """
    loop = asyncio.get_running_loop()
    config = resolve_connect_config()
    address = str(config.get("target_host") or DEFAULT_ADDRESS)
    key = (id(loop), address)
    cached = _clients.get(key)
    if cached is not None:
        cached_loop, task = cached
        if cached_loop is not loop:
            _clients.pop(key, None)
        elif not task.done() or not (task.cancelled() or task.exception() is not None):
            return await task
        else:
            _clients.pop(key, None)
    task = loop.create_task(Client.connect(**config))
    _clients[key] = (loop, task)
    return await task


def _error_message(exc: BaseException) -> str:
    cause = getattr(exc, "cause", None)
    detail = f"{type(exc).__name__}"
    if cause is not None:
        detail += f": {type(cause).__name__}: {cause}"
    elif str(exc).strip():
        detail += f": {exc}"
    return detail[:500]


def _failed(task_id: str, exc: BaseException) -> TaskStatus:
    return TaskStatus(task_id=task_id, workflow_id=workflow_id(task_id),
                      error=_error_message(exc))


def _head_sha(entries: dict) -> str:
    """The last pushed checkpoint, else the pinned base."""
    best, sha = -1, ""
    for key, value in entries.items():
        if not key.startswith("step-") or not isinstance(value, dict):
            continue
        try:
            index = int(key.split("-", 1)[1])
        except ValueError:
            continue
        if index >= best:
            best, sha = index, str(value.get("sha", ""))
    if sha:
        return sha
    pinned = entries.get("pinned")
    return str(pinned.get("base_sha", "")) if isinstance(pinned, dict) else ""


def _receipt(task_id: str) -> dict | None:
    path = receipts.receipt_path(Config.from_env().state_dir, workflow_id(task_id))
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


async def _status(client: Client, task_id: str, error: str = "") -> TaskStatus:
    """Project the live workflow state and the durable receipt into one TaskStatus."""
    status = TaskStatus(task_id=task_id, workflow_id=workflow_id(task_id), error=error)
    doc = _receipt(task_id)
    if doc is not None:
        entries = doc.get("entries") or {}
        status.receipt_status = str(doc.get("status", ""))
        status.receipt_digest = str(doc.get("digest", ""))
        status.entries = list(entries)
        status.metrics = {key: value for key, value in (doc.get("metrics") or {}).items()
                          if isinstance(value, dict)}
        status.head_sha = _head_sha(entries)
        review = entries.get("review") or {}
        status.review_verdict = str(review.get("verdict", ""))
        status.reviewer = str(review.get("reviewer", ""))
        approval = entries.get("approval") or {}
        if approval:
            status.approval = f"{approval.get('verdict', '')} by {approval.get('by', '')}".strip()
            if approval.get("note"):
                status.approval += f" ({approval['note']})"
        status.evidence_status = str((entries.get("evidence") or {}).get("status", ""))
        status.xplan_decision = str((entries.get("xplan_dry_run") or {}).get("decision", ""))

    handle = client.get_workflow_handle(workflow_id(task_id))
    try:
        described = await asyncio.wait_for(handle.describe(), timeout=5)
        status.temporal_status = described.status.name
    except Exception as exc:  # unknown workflow, or the server went away
        if not status.receipt_status:
            status.state = "NOT_FOUND"
            status.error = status.error or _error_message(exc)
            return status
        status.error = status.error or f"describe failed: {_error_message(exc)}"
    try:
        status.state = await asyncio.wait_for(handle.query(TaskWorkflow.state), timeout=5)
    except Exception as exc:
        # A closed workflow is not queryable without a worker on its queue. Its frozen
        # receipt is the durable answer; a non-terminal task has no such fallback.
        if status.receipt_status in receipts.TERMINAL:
            status.state = status.receipt_status
        else:
            status.error = status.error or f"state query failed: {_error_message(exc)}"
    if not status.state:
        status.state = "UNKNOWN"
    return status


async def _approval_recorded(task_id: str, timeout: float = 5.0) -> None:
    """Wait briefly for the workflow to record the decision it just accepted."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        doc = _receipt(task_id)
        if doc is not None and "approval" in (doc.get("entries") or {}):
            return
        await asyncio.sleep(0.1)


def _spec(model: FactoryTaskSpec) -> TaskSpec:
    return TaskSpec(**model.model_dump())


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def submit_task(request: SubmitTask) -> TaskStatus:
    """Start this task's TaskWorkflow (`task-<task_id>`) and return its current status.

    Admission is exactly the factory's own: `validate_batch` then `start_task`, so
    duplicate ids fail with REJECT_DUPLICATE instead of forking a second run.
    """
    task_id = request.spec.task_id
    try:
        spec = _spec(request.spec)
        validate_batch([spec])  # fail before connecting when the contract is invalid
        client = await _temporal_client()
        await start_task(client, spec)
    except WorkflowAlreadyStartedError as exc:
        return await _status(await _temporal_client(), task_id, _error_message(exc))
    except Exception as exc:  # noqa: BLE001 - reported, never faked as success
        return _failed(task_id, exc)
    return await _status(client, task_id)


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def get_status(request: TaskStatusQuery) -> TaskStatus:
    """Read one task's workflow state and durable receipt. Read-only; starts nothing."""
    try:
        return await _status(await _temporal_client(), request.task_id)
    except Exception as exc:  # noqa: BLE001
        return _failed(request.task_id, exc)


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def approve_task(request: TaskApproval) -> TaskStatus:
    """Forward a human decision to TaskWorkflow.decide, the existing approval authority.

    No second approval queue exists here: the workflow's own Update validator decides
    whether the task is actually awaiting a decision.
    """
    try:
        client = await _temporal_client()
        await decide(client, request.task_id, request.verdict, request.by, request.note)
    except Exception as exc:  # noqa: BLE001
        try:
            return await _status(await _temporal_client(), request.task_id, _error_message(exc))
        except Exception:  # noqa: BLE001
            return _failed(request.task_id, exc)
    await _approval_recorded(request.task_id)
    return await _status(client, request.task_id)


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def cancel_task(request: TaskCancellation) -> TaskStatus:
    """Cancel the task's TaskWorkflow and wait for it to close.

    Uses the workflow's cancellation path, so the receipt is finalized as CANCELED by the
    same code that handles any other cancellation.
    """
    try:
        client = await _temporal_client()
        handle = client.get_workflow_handle(workflow_id(request.task_id))
        await handle.cancel()
        with contextlib.suppress(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=45)
    except Exception as exc:  # noqa: BLE001
        try:
            client = await _temporal_client()
            return await _status(client, request.task_id, _error_message(exc))
        except Exception:  # noqa: BLE001
            return _failed(request.task_id, exc)
    status = await _status(client, request.task_id)
    if not status.error and status.temporal_status != "CANCELED":
        status.error = (f"workflow is {status.temporal_status or 'unknown'}; "
                        f"cancellation had no effect")
    return status


def _batch_failed(job_id: str, exc: BaseException) -> BatchStatus:
    return BatchStatus(job_id=job_id, workflow_id=batch_workflow_id(job_id),
                       error=_error_message(exc))


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def submit_batch(request: SubmitBatch) -> BatchStatus:
    """Validate one frozen batch manifest and start `batch-<job_id>`.

    The manifest is read and verified on this host: `manifest_hash`, `script_sha`,
    workspace paths, env and args. A duplicate job id is rejected by Temporal
    (REJECT_DUPLICATE + FAIL) and returns that job's status; it never starts a
    second run. Batch jobs do not enter coding review or a PR path.
    """
    job_id = ""
    try:
        spec = await asyncio.to_thread(load_job_spec, request.manifest_path)
        job_id = spec.job_id
        client = await _temporal_client()
        await start_batch(client, spec)
    except WorkflowAlreadyStartedError as exc:
        try:
            view = await batch_status_view(await _temporal_client(), job_id)
            view["error"] = _error_message(exc)
            return BatchStatus.model_validate(view)
        except Exception:  # noqa: BLE001
            return _batch_failed(job_id, exc)
    except Exception as exc:  # noqa: BLE001 - reported, never faked as success
        return _batch_failed(job_id, exc)
    return BatchStatus.model_validate(await batch_status_view(client, job_id))


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def get_batch_status(request: BatchStatusQuery) -> BatchStatus:
    """Read one batch job's workflow state and durable receipt. Read-only; starts nothing."""
    try:
        return BatchStatus.model_validate(
            await batch_status_view(await _temporal_client(), request.job_id))
    except Exception as exc:  # noqa: BLE001
        return _batch_failed(request.job_id, exc)


@agent.activity_tool_defn(activity_config=TOOL_ACTIVITY)
async def cancel_batch(request: BatchCancellation) -> BatchStatus:
    """Cancel one batch job through its workflow and return the frozen receipt status."""
    try:
        client = await _temporal_client()
        return BatchStatus.model_validate(
            await cancel_batch_workflow(client, request.job_id))
    except Exception as exc:  # noqa: BLE001
        try:
            view = await batch_status_view(await _temporal_client(), request.job_id)
            view["error"] = _error_message(exc)
            return BatchStatus.model_validate(view)
        except Exception:  # noqa: BLE001
            return _batch_failed(request.job_id, exc)


ALL_TOOLS = [submit_task, get_status, approve_task, cancel_task, submit_batch,
             get_batch_status, cancel_batch]

__all__ = ["ALL_TOOLS", "approve_task", "cancel_batch", "cancel_task", "get_batch_status",
           "get_status", "submit_batch", "submit_task"]
