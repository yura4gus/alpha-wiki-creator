"""AH-04: a real Console HTTP session submits, observes and approves a factory task.

Opt-in because it starts a real Temporal dev server, the Harness console and both
workers:

    FACTORY_LIVE_HARNESS_CONSOLE=1 uv run --extra harness pytest \
        tests/test_harness_console_live.py -q

No model is called: the scripted fake agent edits one file and the stub reviewer is
used. The test exercises the same HTTP API the browser console uses.
"""

from __future__ import annotations

import dataclasses
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("temporal_agent_harness")

from conftest import make_spec

SRC = str(Path(__file__).resolve().parents[1] / "src")

pytestmark = pytest.mark.skipif(
    os.environ.get("FACTORY_LIVE_HARNESS_CONSOLE") != "1",
    reason="starts Temporal, the Harness console and workers; set FACTORY_LIVE_HARNESS_CONSOLE=1")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def event_types(events: list[dict]) -> list[str]:
    return [event.get("type", "") for event in events]


def chat(http, base: str, session_id: str, kind: str, payload: dict) -> list[dict]:
    events = []
    with http.stream("POST", f"{base}/api/chat", json={
            "session_id": session_id,
            "message": {"type": kind, "payload": payload}}) as response:
        for line in response.iter_lines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except ValueError:
                    pass
    return events


def handler_output(events: list[dict]) -> dict | None:
    outputs = [event.get("output") for event in events
               if event.get("type") == "message_handler_end"]
    return outputs[-1] if outputs else None


def test_console_submit_observe_and_approve(origin, dirs, tmp_path):
    work, state = dirs
    temporal_port, console_port = free_port(), free_port()
    address = f"localhost:{temporal_port}"
    base = f"http://127.0.0.1:{console_port}"
    env = {**os.environ, "PYTHONPATH": SRC, "FACTORY_WORK_ROOT": str(work),
           "FACTORY_STATE_DIR": str(state), "FACTORY_TEMPORAL_ADDRESS": address,
           "FACTORY_TASK_QUEUE": "factory"}
    for name in ("TEMPORAL_ADDRESS", "TEMPORAL_NAMESPACE", "TEMPORAL_API_KEY",
                 "TEMPORAL_TLS", "TEMPORAL_CONFIG_FILE", "TEMPORAL_PROFILE"):
        env.pop(name, None)
    spec = make_spec(origin, "factory", f"console-{uuid.uuid4().hex[:8]}", "src/a",
                     [[sys.executable, str(Path(__file__).parent / "fake_agent.py"),
                       "write", "src/a/one.txt", "console"]], require_approval=True)
    launcher = subprocess.Popen(
        [sys.executable, "-m", "agent_factory.launcher", "--address", address, "up",
         "--harness", "--harness-port", str(console_port), "--no-follow"],
        cwd=Path(__file__).resolve().parents[1], env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            line = launcher.stdout.readline()
            if line and "Harness Console" in line:
                break
            if launcher.poll() is not None:
                raise AssertionError(f"launcher exited {launcher.returncode}")
        else:
            raise AssertionError("launcher did not print READY")

        with httpx.Client(timeout=120) as http:
            agents = None
            for _ in range(90):
                agents = http.get(f"{base}/api/agents").json().get("agents", [])
                if any(agent.get("workflow_type") == "FactoryCoordinatorAgent"
                       and (agent.get("worker") or {}).get("status") == "ready"
                       for agent in agents):
                    break
                time.sleep(1)
            assert any(agent.get("workflow_type") == "FactoryCoordinatorAgent"
                       for agent in agents or []), agents

            session = f"console-session-{uuid.uuid4().hex[:8]}"
            created = http.post(f"{base}/api/sessions", json={
                "agent_workflow_type": "FactoryCoordinatorAgent", "session_id": session})
            assert created.status_code == 200, created.text

            submitted = chat(http, base, session, "submit_task",
                             {"spec": dataclasses.asdict(spec)})
            assert event_types(submitted)[:6] == [
                "turn_started", "message_handler_start", "tool_start", "tool_end",
                "message_handler_end", "turn_end"], event_types(submitted)
            first = handler_output(submitted)
            assert first and first["workflow_id"] == f"task-{spec.task_id}", first

            status = None
            for _ in range(180):
                events = chat(http, base, session, "get_status", {"task_id": spec.task_id})
                status = handler_output(events)
                if status and status.get("state") == "AWAITING_APPROVAL":
                    break
                time.sleep(0.5)
            assert status and status["state"] == "AWAITING_APPROVAL", status

            approved = chat(http, base, session, "approve_task", {
                "task_id": spec.task_id, "verdict": "approve",
                "by": "console-operator", "note": "AH-04 console cycle"})
            assert "tool_start" in event_types(approved) and "tool_end" in event_types(approved)
            assert handler_output(approved)["approval"] == (
                "approve by console-operator (AH-04 console cycle)")

            final = None
            for _ in range(180):
                events = chat(http, base, session, "get_status", {"task_id": spec.task_id})
                final = handler_output(events)
                if final and final.get("receipt_digest") and final.get("state") == "PR_OPEN":
                    break
                time.sleep(0.5)
            assert final and final["state"] == "PR_OPEN", final
            assert final["receipt_status"] == "PR_OPEN"
            assert final["review_verdict"] == "APPROVE"
            assert final["approval"].startswith("approve by console-operator")

            doc = json.loads((state / "receipts" / f"task-{spec.task_id}.json").read_text())
            assert doc["status"] == "PR_OPEN" and doc["digest"] == final["receipt_digest"]
            assert doc["entries"]["approval"]["by"] == "console-operator"
            assert (state / "prs.json").exists()

            http.post(f"{base}/api/sessions/{session}/close")
    finally:
        os.killpg(launcher.pid, signal.SIGINT)
        try:
            launcher.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(launcher.pid, signal.SIGKILL)
            launcher.wait()
