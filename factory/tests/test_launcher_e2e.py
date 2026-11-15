"""One-command local launch, including the approval path and receipt readback.

Opt-in because it starts a real Temporal dev server:

    FACTORY_LIVE_LAUNCHER=1 .venv/bin/python -m pytest tests/test_launcher_e2e.py -q
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

import pytest

from agent_factory import receipts
from conftest import agent, make_spec

pytestmark = pytest.mark.skipif(
    not os.environ.get("FACTORY_LIVE_LAUNCHER"),
    reason="starts a real Temporal dev server; set FACTORY_LIVE_LAUNCHER=1")
SRC = str(Path(__file__).resolve().parents[1] / "src")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


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
