"""One-command local launch, including the approval path and receipt readback.

Opt-in because it starts a real Temporal dev server:

    FACTORY_LIVE_LAUNCHER=1 .venv/bin/python -m pytest tests/test_launcher_e2e.py -q
    FACTORY_LIVE_HARNESS_STACK=1 .venv/bin/python -m pytest tests/test_launcher_e2e.py -q
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import pytest
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest

from agent_factory import launcher, receipts
from agent_factory.connection import connect
from conftest import agent, make_spec

LAUNCHER_LIVE = pytest.mark.skipif(
    not os.environ.get("FACTORY_LIVE_LAUNCHER"),
    reason="starts a real Temporal dev server; set FACTORY_LIVE_LAUNCHER=1")
SRC = str(Path(__file__).resolve().parents[1] / "src")
FACTORY = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@LAUNCHER_LIVE
def test_one_command_up_starts_temporal_worker_and_approval(origin, dirs, tmp_path):
    work, state = dirs
    port = free_port()
    task_id = f"up-{uuid.uuid4().hex[:8]}"
    spec = make_spec(origin, f"up-{port}", task_id, "src/a",
                     [agent("write", "src/a/one.txt", "1")], require_approval=True)
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(asdict(spec)))

    env = {**os.environ, "PYTHONPATH": SRC, "FACTORY_WORK_ROOT": str(work),
           "FACTORY_STATE_DIR": str(state), "FACTORY_TEMPORAL_ADDRESS": f"localhost:{port}"}
    env.pop("FACTORY_FAULTS", None)
    cmd = [sys.executable, "-m", "agent_factory.launcher", "--address", f"localhost:{port}",
           "up", "--task", str(task_path), "--approve-by", "owner"]
    run = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stdout + run.stderr

    doc = json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())
    assert doc["status"] == "PR_OPEN" and receipts.validate(doc) == []
    assert doc["entries"]["approval"] == {"verdict": "approve", "by": "owner",
                                          "note": "launcher auto-approve"}
    assert doc["entries"]["review"]["verdict"] == "APPROVE"
    assert not (work / task_id / "wt").exists()

    status = subprocess.run(
        [sys.executable, "-m", "agent_factory.launcher", "--address", f"localhost:{port}",
         "status", task_id], env=env, capture_output=True, text=True, timeout=60)
    assert status.returncode == 0, status.stdout + status.stderr
    row = json.loads(status.stdout)
    assert row["receipt"]["status"] == "PR_OPEN" and row["receipt"]["review"] == "APPROVE"
    assert "state" not in row and "temporal" not in row, "server stopped; receipt still readable"


def _wait_for(predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.5)
    return predicate()


def _wait_for_http_agents(port: int, timeout: float = 60) -> dict | list | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/agents", timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(1)
    return None


def _wait_for_pollers(address: str, queues: list[str], timeout: float = 90) -> dict[str, int]:
    async def go() -> dict[str, int]:
        client = await connect(address)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            counts = {}
            for queue in queues:
                response = await client.workflow_service.describe_task_queue(
                    DescribeTaskQueueRequest(
                        namespace=client.namespace, task_queue=TaskQueue(name=queue),
                        task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW),
                    timeout=timedelta(seconds=3))
                counts[queue] = sum(1 for poller in response.pollers
                                    if poller.HasField("last_access_time"))
            if all(counts.values()) or loop.time() >= deadline:
                return counts
            await asyncio.sleep(2)

    return asyncio.run(go())


@pytest.mark.skipif(
    not os.environ.get("FACTORY_LIVE_HARNESS_STACK"),
    reason="starts Temporal, the harness console and the coordinator; "
           "set FACTORY_LIVE_HARNESS_STACK=1")
def test_one_command_harness_stack_starts_console_and_both_workers(dirs):
    settings = launcher.HarnessSettings(
        registry=launcher.default_harness_registry(), port=8000,
        task_queue="factory-coordinator", factory_root=FACTORY)
    reason = launcher.harness_preflight_reason(settings)
    if reason:
        pytest.skip(reason)

    work, state = dirs
    temporal_port, harness_port = free_port(), free_port()
    assert temporal_port != harness_port
    env = {**os.environ, "PYTHONPATH": SRC, "PYTHONUNBUFFERED": "1",
           "FACTORY_WORK_ROOT": str(work), "FACTORY_STATE_DIR": str(state),
           "FACTORY_TEMPORAL_ADDRESS": f"localhost:{temporal_port}"}
    env.pop("FACTORY_FAULTS", None)
    cmd = [sys.executable, "-m", "agent_factory.launcher",
           "--address", f"localhost:{temporal_port}", "up", "--harness",
           "--harness-port", str(harness_port), "--no-follow",
           "--harness-registry", str(settings.registry)]
    proc = subprocess.Popen(cmd, cwd=FACTORY, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1,
                            start_new_session=True)
    lines: list[str] = []
    ready = threading.Event()

    def drain() -> None:
        for line in proc.stdout:
            lines.append(line)
            if line.strip() == "READY":
                ready.set()

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and proc.poll() is None and not ready.is_set():
            ready.wait(0.5)
        output = "".join(lines)
        assert ready.is_set(), f"harness stack did not become ready (exit {proc.poll()}):\n{output}"
        assert f"http://127.0.0.1:{harness_port}" in output
        assert "factory-coordinator" in output and "Factory queues" in output

        agents = _wait_for_http_agents(harness_port)
        assert agents is not None, f"console API did not answer /api/agents:\n{output}"

        queues = ["factory-coordinator", env.get("FACTORY_TASK_QUEUE", "factory")]
        counts = _wait_for_pollers(f"localhost:{temporal_port}", queues)
        assert all(counts[queue] > 0 for queue in queues), counts

        record = json.loads(launcher._record_path(state).read_text())
        assert record["state"] == "running"
        assert launcher._port_open(harness_port) and launcher._port_open(temporal_port)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        reader.join(timeout=5)

    assert proc.returncode in {0, 130}, f"unexpected exit {proc.returncode}:\n{''.join(lines)}"
    assert _wait_for(lambda: not launcher._port_open(harness_port), 15)
    assert _wait_for(lambda: not launcher._port_open(temporal_port), 15)
    record = json.loads(launcher._record_path(state).read_text())
    assert record["state"] == "stopped"
    for name in ("harness", "coordinator"):
        log = state / "harness" / f"{name}.log"
        assert log.exists() and log.stat().st_size > 0
