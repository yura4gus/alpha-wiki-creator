"""Harness surface proof: submit_batch/get_batch_status/cancel_batch are typed.

The coordinator is the existing `FactoryCoordinatorAgent`; batch jobs still run in
`BatchWorkflow` and skip coding review/PR. No model is called.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

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
from agent_factory.batch.activities import ALL as BATCH_ACTIVITIES
from agent_factory.batch.manifest import compute_manifest_hash
from agent_factory.batch.util import sha256_file
from agent_factory.batch.workflow import BatchWorkflow
from agent_factory.harness import ALL_TOOLS, BatchStatus, FactoryCoordinatorAgent

pytestmark = pytest.mark.asyncio(loop_scope="module")

FAST = """\
import pathlib
pathlib.Path("out").mkdir(exist_ok=True)
pathlib.Path("out/result.json").write_text('{"ok": true}')
pathlib.Path("effects.log").write_text("once")
"""

SLOW = """\
import os, pathlib, time
pathlib.Path("slow.pid").write_text(str(os.getpid()))
time.sleep(30)
"""


@pytest_asyncio.fixture
async def harness(env, monkeypatch):
    address = env.client.service_client.config.target_host
    monkeypatch.setenv("FACTORY_TEMPORAL_ADDRESS", address)
    client = await Client.connect(address, namespace=env.client.namespace,
                                  plugins=[AgentHarnessPlugin(tools=ALL_TOOLS)])
    yield client


@asynccontextmanager
async def coordinator_worker(client: Client, task_queue: str):
    async with Worker(client, task_queue=task_queue, workflows=[FactoryCoordinatorAgent],
                      max_concurrent_activities=4):
        yield


@asynccontextmanager
async def batch_worker(server, queue: str):
    async with Worker(server.client, task_queue=queue, workflows=[BatchWorkflow],
                      activities=BATCH_ACTIVITIES, max_concurrent_activities=4):
        yield


def make_job(tmp_path: Path, job_id: str, queue: str, body: str) -> tuple[Path, Path]:
    workspace = tmp_path / f"ws-{job_id}"
    workspace.mkdir()
    script = workspace / "job.py"
    script.write_text(body)
    manifest = {
        "job_id": job_id,
        "runner_id": "python",
        "workspace": str(workspace),
        "script": "job.py",
        "script_sha": sha256_file(script),
        "units": [{"unit_id": "u1", "outputs": ["out/result.json"],
                   "resource_limits": {"timeout_seconds": 30, "cpu_seconds": 30,
                                       "memory_mb": 1024, "output_bytes": 100000}}],
        "task_queue": queue,
        "heartbeat_timeout_seconds": 5,
        "retry_policy": {"max_attempts": 2, "initial_interval_seconds": 1},
    }
    manifest["manifest_hash"] = compute_manifest_hash(manifest)
    path = tmp_path / f"{job_id}.json"
    path.write_text(json.dumps(manifest))
    return path, workspace


def _keep(item, _resume_offset):
    return item


async def ask(client: AgentClient, kind: str, payload: dict,
              timeout: float = 120.0) -> tuple[BatchStatus, list[AgentEvent]]:
    events: list[AgentEvent] = []
    stream = await client.send_message(kind, payload, on_item=_keep, timeout=timeout)
    async for item in stream:
        if isinstance(item, (AgentTurnError, AgentTurnTimeout)):
            raise AssertionError(f"{kind} failed: {item}")
        events.append(item)
    replies = [event for event in events
               if event.event.type == AgentEventType.MESSAGE_HANDLER_END]
    assert len(replies) == 1, [event.event.type for event in events]
    return BatchStatus.model_validate(replies[0].event.output), events


async def wait_for(client: AgentClient, job_id: str, predicate, attempts: int = 120,
                   delay: float = 0.25) -> BatchStatus:
    last = None
    for _ in range(attempts):
        last, _events = await ask(client, "get_batch_status", {"job_id": job_id})
        if predicate(last):
            return last
        await asyncio.sleep(delay)
    raise AssertionError(f"batch {job_id} never reached the expected state; last={last}")


async def test_coordinator_submits_reads_and_cancels_batch_jobs(
        env, dirs, queue, tmp_path, harness):
    _work, state = dirs
    coord_queue = f"coord-{uuid.uuid4().hex[:8]}"
    wf_id = f"FactoryCoordinatorAgent-{uuid.uuid4().hex[:8]}"
    client = AgentClient(harness, wf_id)
    ok_path, ok_ws = make_job(tmp_path, "hb-ok", queue, FAST)
    cancel_path, cancel_ws = make_job(tmp_path, "hb-cancel", queue, SLOW)

    async with batch_worker(env, queue):
        async with coordinator_worker(harness, coord_queue):
            await harness.start_workflow(FactoryCoordinatorAgent.run, AgentConfig(),
                                         id=wf_id, task_queue=coord_queue)
            status, events = await ask(client, "submit_batch", {"manifest_path": str(ok_path)})
            assert status.error == "", status.error
            assert status.workflow_id == "batch-hb-ok"
            assert any(e.event.type == AgentEventType.TOOL_START and
                       e.event.tool_name == "submit_batch" for e in events)

            done = await wait_for(client, "hb-ok",
                                  lambda s: s.receipt_status == "BATCH_SUCCESS")
            assert done.state == "BATCH_SUCCESS" and done.temporal_status == "COMPLETED"
            manifest = json.loads(ok_path.read_text())
            assert done.manifest_hash == manifest["manifest_hash"]
            assert done.script_sha == manifest["script_sha"]
            assert done.units[0].unit_id == "u1" and done.units[0].status == "COMPLETED"
            assert done.units[0].outputs["out/result.json"]
            assert done.dq_status == "SKIPPED"
            assert (ok_ws / "effects.log").read_text() == "once"
            doc = json.loads(receipts.receipt_path(state, "batch-hb-ok").read_text())
            assert receipts.validate(doc) == [] and doc["digest"] == done.receipt_digest

            duplicate, _events = await ask(client, "submit_batch",
                                           {"manifest_path": str(ok_path)})
            assert "already started" in duplicate.error.lower()
            assert duplicate.workflow_id == "batch-hb-ok"
            assert (ok_ws / "effects.log").read_text() == "once"  # no second run

            status, _events = await ask(client, "submit_batch",
                                        {"manifest_path": str(cancel_path)})
            assert status.error == "" and status.workflow_id == "batch-hb-cancel"
            deadline = time.time() + 60
            pid = 0
            while time.time() < deadline:
                if (cancel_ws / "slow.pid").exists():
                    pid = int((cancel_ws / "slow.pid").read_text())
                    break
                await asyncio.sleep(0.2)
            assert pid, "slow batch unit never started"
            canceled, _events = await ask(client, "cancel_batch", {"job_id": "hb-cancel"})
            assert canceled.error == "", canceled.error
            assert canceled.temporal_status == "CANCELED"
            assert canceled.receipt_status == "BATCH_CANCELED"
            assert receipts.validate(
                json.loads(receipts.receipt_path(state, "batch-hb-cancel").read_text())) == []
            time.sleep(0.5)
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
