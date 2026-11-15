"""DoD proof: the harness coordinator is a real, durable surface over TaskWorkflow.

No model is involved. The test runs the normal factory worker (TaskWorkflow + every
activity) plus a FactoryCoordinatorAgent worker whose tool activities come from
`AgentHarnessPlugin`, starts the agent through `AgentClient`, and asserts:

1. `submit_task` returns a typed TaskStatus, publishes `tool_start`/`tool_end`, and the
   existing TaskWorkflow really runs to `PR_OPEN`.
2. `get_status` projects the durable receipt (review, evidence, xPlan, checkpoint SHA).
3. A `require_approval` task waits in AWAITING_APPROVAL with no harness approval gate;
   `approve_task` applies `TaskWorkflow.decide` and the receipt records that approver.
4. `cancel_task` finalizes the task `CANCELED` and opens no PR.
5. After the coordinator worker is stopped and recreated (same workflow id), `get_status`
   still answers, a duplicate `submit_task` is rejected, and no extra workflow/receipt
   exists.

Gated only by the optional `harness` extra: `pytest.importorskip`, no live-model flag.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from temporalio.client import Client
from temporalio.worker import Worker

pytest.importorskip("temporal_agent_harness")

from temporal_agent_harness.harness.agent_client import AgentClient, AgentTurnError, AgentTurnTimeout
from temporal_agent_harness.harness.agent_protocol import (
    AgentConfig,
    AgentEvent,
    AgentEventType,
)
from temporal_agent_harness.plugin import AgentHarnessPlugin

from agent_factory import receipts
from agent_factory.harness import (
    ALL_TOOLS,
    FactoryCoordinatorAgent,
    FactoryTaskSpec,
    TaskStatus,
)
from agent_factory.workflows import TaskWorkflow

from conftest import agent, make_spec, worker

pytestmark = pytest.mark.asyncio(loop_scope="module")

APPROVAL = ("tool_approval_requested", "tool_approval_resolved")


@pytest_asyncio.fixture
async def harness(env, monkeypatch):
    """A client carrying the harness plugin, pointed at *this* test's Temporal server."""
    address = env.client.service_client.config.target_host
    monkeypatch.setenv("FACTORY_TEMPORAL_ADDRESS", address)
    client = await Client.connect(address, namespace=env.client.namespace,
                                  plugins=[AgentHarnessPlugin(tools=ALL_TOOLS)])
    # temporalio 1.36 has no client close(); the env-owned runtime closes on shutdown.
    yield client


@asynccontextmanager
async def coordinator_worker(client: Client, task_queue: str):
    """The coordinator worker: no model plugin, tool activities from the harness plugin."""
    async with Worker(client, task_queue=task_queue, workflows=[FactoryCoordinatorAgent],
                      max_concurrent_activities=4):
        yield


def _keep(item, _resume_offset):
    return item


async def ask(client: AgentClient, kind: str, payload: dict,
              timeout: float = 120.0) -> tuple[TaskStatus, list[AgentEvent]]:
    """Send one typed message through the native client and return its reply + events."""
    events: list[AgentEvent] = []
    stream = await client.send_message(kind, payload, on_item=_keep, timeout=timeout)
    async for item in stream:
        if isinstance(item, (AgentTurnError, AgentTurnTimeout)):
            raise AssertionError(f"{kind} failed: {item}")
        events.append(item)
    replies = [event for event in events
               if event.event.type == AgentEventType.MESSAGE_HANDLER_END]
    assert len(replies) == 1, [event.event.type for event in events]
    return TaskStatus.model_validate(replies[0].event.output), events


async def wait_for_state(client: AgentClient, task_id: str, predicate, attempts: int = 80,
                         delay: float = 0.25) -> TaskStatus:
    last: TaskStatus | None = None
    for _ in range(attempts):
        last, _events = await ask(client, "get_status", {"task_id": task_id})
        if predicate(last):
            return last
        await asyncio.sleep(delay)
    raise AssertionError(f"task {task_id} never reached the expected state; last={last}")


def factory_spec(spec) -> dict:
    return FactoryTaskSpec(**dataclasses.asdict(spec)).model_dump(mode="json")


def receipt(state, task_id: str) -> dict:
    return json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())


def pr_count(state) -> int:
    path = state / "prs.json"
    return len(json.loads(path.read_text())) if path.exists() else 0


async def test_coordinator_is_a_durable_typed_surface_over_task_workflow(
        env, origin, dirs, queue, harness):
    _work, state = dirs
    coord_queue = f"coord-{uuid.uuid4().hex[:8]}"
    wf_id = f"FactoryCoordinatorAgent-{uuid.uuid4().hex[:8]}"
    client = AgentClient(harness, wf_id)

    ok = make_spec(origin, queue, "hx-ok", "src/a", [agent("write", "src/a/one.txt", "1")])
    gated = make_spec(origin, queue, "hx-gated", "src/b",
                      [agent("write", "src/b/one.txt", "1")], require_approval=True)
    doomed = make_spec(origin, queue, "hx-cancel", "src/c",
                       [agent("slow-write", "src/c/one.txt", "1", "30")],
                       max_step_seconds=60)

    observed: list[AgentEvent] = []
    async with worker(env, queue):  # the normal TaskWorkflow worker, unchanged
        async with coordinator_worker(harness, coord_queue):
            await harness.start_workflow(FactoryCoordinatorAgent.run, AgentConfig(),
                                         id=wf_id, task_queue=coord_queue)

            # -- 1. submit_task: typed reply, real tool events, the real task runs --------
            status, events = await ask(client, "submit_task", {"spec": factory_spec(ok)})
            observed += events
            assert status.error == "", status.error
            assert status.task_id == "hx-ok"
            assert status.workflow_id == "task-hx-ok"
            assert status.state not in {"", "NOT_FOUND", "UNKNOWN"}
            starts = {e.event.tool_id: e.event for e in events
                      if e.event.type == AgentEventType.TOOL_START}
            ends = {e.event.tool_id: e.event for e in events
                    if e.event.type == AgentEventType.TOOL_END}
            assert any(s.tool_name == "submit_task" for s in starts.values())
            assert set(starts) == set(ends)  # every native tool call also ended
            assert any(e.tool_output.get("workflow_id") == "task-hx-ok"
                       for e in ends.values())

            # The tool started this workflow, so this client has no cached result type;
            # the typed handle supplies TaskWorkflow.run's return type.
            ok_result = await asyncio.wait_for(
                env.client.get_workflow_handle_for(
                    TaskWorkflow.run, "task-hx-ok").result(), timeout=120)
            assert ok_result.status == "PR_OPEN"

            # -- 2. get_status projects the durable receipt --------------------------------
            status, events = await ask(client, "get_status", {"task_id": "hx-ok"})
            observed += events
            assert status.error == "" and status.state == "PR_OPEN"
            assert status.temporal_status == "COMPLETED"
            assert status.receipt_status == "PR_OPEN"
            assert status.receipt_digest == ok_result.receipt_digest
            assert status.head_sha == ok_result.head_sha
            assert status.review_verdict == "APPROVE" and status.reviewer == "stub-rule-based"
            assert status.evidence_status == "MISSING"  # no evidence configured, not invented
            assert status.xplan_decision == "SKIPPED"
            assert {"pinned", "step-0", "tests", "review", "pr"} <= set(status.entries)
            assert status.metrics["step-0"]["seconds"] >= 0
            assert receipts.validate(receipt(state, "hx-ok")) == []

            # -- 3. approval goes through TaskWorkflow.decide, not a harness queue ---------
            status, events = await ask(client, "submit_task", {"spec": factory_spec(gated)})
            observed += events
            assert status.error == "" and status.workflow_id == "task-hx-gated"
            waiting = await wait_for_state(client, "hx-gated",
                                           lambda s: s.state == "AWAITING_APPROVAL")
            assert waiting.receipt_status == "RUNNING"
            assert waiting.review_verdict == "APPROVE"
            # The harness agent itself has nothing to approve: TaskWorkflow owns the decision.
            agent_status = await client.get_status()
            assert agent_status.approval_policy.dangerously_skip_all_approvals is True
            assert await client.get_pending_approvals() == []

            approved, events = await ask(client, "approve_task", {
                "task_id": "hx-gated", "verdict": "approve",
                "by": "console-operator", "note": "ship it"})
            observed += events
            assert approved.error == "", approved.error
            assert approved.approval == "approve by console-operator (ship it)"
            # The decision is durable; the workflow may already be past OPENING_PR.
            assert approved.state not in {"", "NOT_FOUND", "UNKNOWN"}

            gated_result = await asyncio.wait_for(
                env.client.get_workflow_handle_for(
                    TaskWorkflow.run, "task-hx-gated").result(), timeout=120)
            assert gated_result.status == "PR_OPEN"
            doc = receipt(state, "hx-gated")
            assert doc["entries"]["approval"] == {
                "verdict": "approve", "by": "console-operator", "note": "ship it"}
            assert receipts.validate(doc) == []
            assert pr_count(state) == 2

            # -- 4. cancel_task finalizes CANCELED through the workflow's own path --------
            status, events = await ask(client, "submit_task", {"spec": factory_spec(doomed)})
            observed += events
            assert status.error == "" and status.workflow_id == "task-hx-cancel"
            await wait_for_state(client, "hx-cancel", lambda s: s.state.startswith("AGENT_STEP"))

            canceled, events = await ask(client, "cancel_task", {"task_id": "hx-cancel"})
            observed += events
            assert canceled.error == "", canceled.error
            assert canceled.temporal_status == "CANCELED"
            assert canceled.receipt_status == "CANCELED" and canceled.state == "CANCELED"
            canceled_doc = receipt(state, "hx-cancel")
            assert canceled_doc["status"] == "CANCELED"
            assert receipts.validate(canceled_doc) == []
            assert pr_count(state) == 2  # no PR for the canceled task

        # -- 5. new coordinator worker, same workflow id: status still works ---------------
        async with coordinator_worker(harness, coord_queue):
            assert (await harness.get_workflow_handle(wf_id).describe()).status.name == "RUNNING"
            again, events = await ask(client, "get_status", {"task_id": "hx-ok"})
            observed += events
            assert again.error == "" and again.state == "PR_OPEN"
            assert again.receipt_digest == ok_result.receipt_digest

            duplicate, events = await ask(client, "submit_task", {"spec": factory_spec(ok)})
            observed += events
            assert "already started" in duplicate.error.lower()
            assert duplicate.workflow_id == "task-hx-ok"
            # Exactly one workflow/receipt per task: the duplicate started nothing.
            assert len(list((state / "receipts").glob("*.json"))) == 3
            assert (await harness.get_workflow_handle("task-hx-ok").describe()).status.name \
                == "COMPLETED"

    # The harness gate never opened: TaskWorkflow was the only approval authority.
    assert not [event for event in observed if event.event.type in {
        AgentEventType.TOOL_APPROVAL_REQUESTED, AgentEventType.TOOL_APPROVAL_RESOLVED}]
