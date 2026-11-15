"""AH-07: three real OpenCode tasks through the native Harness coordinator.

Opt-in because it spends real model calls:

    FACTORY_LIVE_HARNESS=1 uv run --extra harness pytest tests/test_harness_live.py -q

The coordinator is the only entry point: every task is submitted, polled, approved and
re-read through typed Harness messages. The existing TaskWorkflow still does the work.
The test also stops and recreates both workers, then reconnects with a new AgentClient —
the session, task state and receipts must survive without duplicate work.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from temporalio.client import Client
from temporalio.worker import Worker

pytest.importorskip("temporal_agent_harness")

from temporal_agent_harness.harness.agent_client import AgentClient, AgentTurnError, AgentTurnTimeout
from temporal_agent_harness.harness.agent_protocol import AgentConfig, AgentEvent, AgentEventType
from temporal_agent_harness.plugin import AgentHarnessPlugin

from agent_factory import receipts
from agent_factory.harness import (ALL_TOOLS, FactoryCoordinatorAgent, FactoryTaskSpec,
                                   TaskStatus)
from agent_factory.workflows import TaskWorkflow
from conftest import make_spec, remote_log, sh, worker

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(os.environ.get("FACTORY_LIVE_HARNESS") != "1",
                       reason="live OpenCode calls through Harness; set FACTORY_LIVE_HARNESS=1"),
]

MODEL = os.environ.get("FACTORY_REVIEW_MODEL", "opencode-go/deepseek-v4.1-flash")
OPENCODE = os.environ.get("FACTORY_OPENCODE_BIN", shutil.which("opencode") or "opencode")


def cli_step(prompt: str) -> list[str]:
    return [OPENCODE, "run", "--auto", "-m", MODEL, prompt]


def prompt(name: str) -> str:
    return (f"Create a file named src/{name}/one.txt containing exactly: {name}. "
            f"Only modify files under src/{name}/. Do not run git commands.")


@pytest_asyncio.fixture
async def harness(env, monkeypatch):
    address = env.client.service_client.config.target_host
    monkeypatch.setenv("FACTORY_TEMPORAL_ADDRESS", address)
    client = await Client.connect(address, namespace=env.client.namespace,
                                  plugins=[AgentHarnessPlugin(tools=ALL_TOOLS)])
    yield client


@asynccontextmanager
async def coordinator(client: Client, task_queue: str):
    async with Worker(client, task_queue=task_queue, workflows=[FactoryCoordinatorAgent],
                      max_concurrent_activities=4):
        yield


def keep(item, _offset):
    return item


async def ask(client: AgentClient, kind: str, payload: dict,
              timeout: float = 180.0) -> tuple[TaskStatus, list[AgentEvent]]:
    events: list[AgentEvent] = []
    stream = await client.send_message(kind, payload, on_item=keep, timeout=timeout)
    async for item in stream:
        if isinstance(item, (AgentTurnError, AgentTurnTimeout)):
            raise AssertionError(f"{kind} failed: {item}")
        events.append(item)
    replies = [event for event in events
               if event.event.type == AgentEventType.MESSAGE_HANDLER_END]
    assert len(replies) == 1, [event.event.type for event in events]
    return TaskStatus.model_validate(replies[0].event.output), events


async def wait_state(client: AgentClient, task_id: str, predicate, attempts: int = 240,
                     delay: float = 0.5) -> TaskStatus:
    last = None
    for _ in range(attempts):
        last, _ = await ask(client, "get_status", {"task_id": task_id})
        if predicate(last):
            return last
        await asyncio.sleep(delay)
    raise AssertionError(f"{task_id} did not reach the expected state; last={last}")


def payload(spec) -> dict:
    return FactoryTaskSpec(**dataclasses.asdict(spec)).model_dump(mode="json")


def receipt(state, task_id: str) -> dict:
    return json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())


def prs(state) -> dict:
    path = state / "prs.json"
    return json.loads(path.read_text()) if path.exists() else {}


async def test_three_real_open_code_tasks_through_harness(env, origin, dirs, queue, harness):
    _work, state = dirs
    coord_queue = f"coord-live-{uuid.uuid4().hex[:8]}"
    agent_id = f"FactoryCoordinatorAgent-{uuid.uuid4().hex[:8]}"
    client = AgentClient(harness, agent_id)
    specs = [make_spec(origin, queue, f"hx-live-{x}-{uuid.uuid4().hex[:6]}", f"src/{x}",
                       [cli_step(prompt(x))], reviewer="opencode", review_model=MODEL,
                       max_step_seconds=240, heartbeat_timeout_seconds=10)
             for x in "abc"]
    specs[0].require_approval = True

    async with worker(env, queue):  # the existing TaskWorkflow worker, unchanged
        async with coordinator(harness, coord_queue):
            await harness.start_workflow(FactoryCoordinatorAgent.run, AgentConfig(),
                                         id=agent_id, task_queue=coord_queue)
            for spec in specs:
                status, events = await ask(client, "submit_task", {"spec": payload(spec)})
                assert status.error == "", status.error
                assert status.workflow_id == f"task-{spec.task_id}"
                assert any(e.event.type == AgentEventType.TOOL_START for e in events)

            gated = specs[0]
            waiting = await wait_state(client, gated.task_id,
                                       lambda s: s.state == "AWAITING_APPROVAL")
            assert waiting.review_verdict == "APPROVE"
            approved, _ = await ask(client, "approve_task", {
                "task_id": gated.task_id, "verdict": "approve",
                "by": "harness-operator", "note": "AH-07 acceptance"})
            assert approved.error == "", approved.error
            assert approved.approval == "approve by harness-operator (AH-07 acceptance)"

            final = {}
            for spec in specs:
                status = await wait_state(client, spec.task_id, lambda s: s.state == "PR_OPEN",
                                          attempts=360)
                assert status.error == "", (spec.task_id, status.error)
                assert status.receipt_status == "PR_OPEN"
                assert status.review_verdict == "APPROVE", status
                assert status.reviewer == f"opencode:{MODEL}", status
                assert status.temporal_status == "COMPLETED", status
                final[spec.task_id] = status

    # Workers are gone. A new client/worker pair reconnects to the same durable session.
    async with worker(env, queue):
        async with coordinator(harness, coord_queue):
            reconnected = AgentClient(harness, agent_id)
            again, _ = await ask(reconnected, "get_status",
                                 {"task_id": specs[0].task_id})
            assert again.error == "" and again.state == "PR_OPEN", again
            assert again.receipt_digest == final[specs[0].task_id].receipt_digest

            duplicate, _ = await ask(reconnected, "submit_task", {"spec": payload(specs[0])})
            assert "already started" in duplicate.error.lower(), duplicate

    assert len(prs(state)) == 3
    assert len(list((state / "receipts").glob("*.json"))) == 3
    for spec in specs:
        assert final[spec.task_id].head_sha
        assert receipts.validate(receipt(state, spec.task_id)) == []
        changed = sh("git", "diff", "--name-only", "main",
                     f"factory/{spec.task_id}", cwd=origin).splitlines()
        assert changed == [f"{spec.owned_paths[0]}/one.txt"], (spec.task_id, changed)
        assert remote_log(origin, f"factory/{spec.task_id}").count("Factory-Step:") == 1
    print(json.dumps({"tasks": {k: v.receipt_digest for k, v in final.items()},
                      "prs": len(prs(state)), "model": MODEL}, sort_keys=True))
