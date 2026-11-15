"""One-command local operation: Temporal dev server, workers, tasks, live status.

`python -m agent_factory.launcher up --task task.json` starts a local Temporal
server when the configured address is unreachable, runs the worker in this
process, admits the tasks and reports state, review, receipts and measured
step time. Nothing is deployed and no credential enters workflow history.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path

from temporalio.client import Client
from temporalio.client import WorkflowFailureError
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.worker import Worker

from . import receipts
from .activities import ALL
from .client import validate_batch, workflow_id
from .config import Config
from .models import Decision, TaskSpec
from .workflows import TaskWorkflow

TERMINAL = receipts.TERMINAL


def load_specs(paths: list[str]) -> list[TaskSpec]:
    specs = []
    for path in paths:
        data = json.loads(Path(path).read_text())
        for item in data if isinstance(data, list) else [data]:
            specs.append(TaskSpec(**item))
    validate_batch(specs)
    return specs


def _port(address: str) -> int:
    return int(address.rsplit(":", 1)[-1])


class LocalTemporal:
    """Start `temporal server start-dev` only when the address has no server."""

    def __init__(self, address: str, state_dir: Path):
        self.address, self.state_dir = address, state_dir
        self.proc: subprocess.Popen | None = None

    async def _reachable(self) -> bool:
        try:
            await asyncio.wait_for(Client.connect(self.address), timeout=2)
            return True
        except Exception:
            return False

    async def start(self) -> bool:
        if await self._reachable():
            return False
        binary = shutil.which("temporal")
        if not binary:
            raise RuntimeError("Temporal is unreachable and the `temporal` CLI is not installed")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        log = open(self.state_dir / "temporal.log", "ab")
        self.proc = subprocess.Popen(
            [binary, "server", "start-dev", "--headless", "--port", str(_port(self.address)),
             "--db-filename", str(self.state_dir / "temporal.db"), "--log-level", "error"],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(60):
            if self.proc.poll() is not None:
                raise RuntimeError(f"Temporal dev server exited; see {self.state_dir / 'temporal.log'}")
            if await self._reachable():
                return True
            await asyncio.sleep(0.5)
        raise RuntimeError("Temporal dev server did not become ready")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait()


async def _open_workers(client: Client, specs: list[TaskSpec], stack: AsyncExitStack,
                        limit: int) -> None:
    for queue in sorted({spec.task_queue for spec in specs}):
        await stack.enter_async_context(
            Worker(client, task_queue=queue, workflows=[TaskWorkflow], activities=ALL,
                   max_concurrent_activities=limit))


async def _admit(client: Client, spec: TaskSpec):
    return await client.start_workflow(
        TaskWorkflow.run, spec, id=workflow_id(spec.task_id), task_queue=spec.task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        id_conflict_policy=WorkflowIDConflictPolicy.FAIL)


def _status_line(handle, state: str) -> str:
    return f"{handle.id:<28} {state:<18}"


def _receipt_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    doc = json.loads(path.read_text())
    metrics = doc.get("metrics", {})
    seconds = round(sum(m.get("seconds", 0) for m in metrics.values()
                        if isinstance(m, dict)), 2)
    review = doc.get("entries", {}).get("review", {})
    wall = None
    try:
        from datetime import datetime
        wall = round((datetime.fromisoformat(doc["finalized_at"])
                      - datetime.fromisoformat(doc["recorded_at"])).total_seconds(), 2)
    except (KeyError, TypeError, ValueError):
        pass
    return {"status": doc.get("status"), "digest": doc.get("digest", "")[:16],
            "measured_step_seconds": seconds, "wall_seconds": wall,
            "review": review.get("verdict"), "reviewer": review.get("reviewer"),
            "entries": len(doc.get("entries", {}))}


async def _follow(client: Client, handles: list, auto_approve: str, state_dir: Path) -> int:
    """Poll until every workflow closes; print state and any approval request."""
    pending = list(handles)
    approved: set[str] = set()
    last: dict[str, str] = {}
    print(f"{'WORKFLOW':<28} {'STATE':<18}")
    while pending:
        for handle in list(pending):
            try:
                state = await handle.query(TaskWorkflow.state)
            except Exception:
                state = "CLOSED"
            if last.get(handle.id) != state:
                print(_status_line(handle, state))
                last[handle.id] = state
            if state == "AWAITING_APPROVAL" and auto_approve and handle.id not in approved:
                await handle.execute_update(TaskWorkflow.decide,
                                            Decision("approve", auto_approve, "launcher auto-approve"))
                approved.add(handle.id)
            described = await handle.describe()
            if described.status.name in {"COMPLETED", "FAILED", "CANCELED", "TERMINATED",
                                         "TIMED_OUT", "CONTINUED_AS_NEW"}:
                pending.remove(handle)
        if pending:
            await asyncio.sleep(2)
    failures = 0
    for handle in handles:
        print(_status_line(handle, "closed"))
        try:
            result = await handle.result()
            summary = _receipt_summary(receipts.receipt_path(state_dir, handle.id))
            print(json.dumps({"workflow": handle.id, "result": result.status,
                              "head": result.head_sha[:12], "review": result.review,
                              "receipt": summary}, sort_keys=True))
            if result.status not in {"PR_OPEN", "REJECTED"}:
                failures += 1
        except WorkflowFailureError:
            summary = _receipt_summary(receipts.receipt_path(state_dir, handle.id))
            print(json.dumps({"workflow": handle.id, "result": "FAILED_OR_CANCELED",
                              "receipt": summary}, sort_keys=True))
            failures += 1
    return 1 if failures else 0


async def up(args) -> int:
    cfg = Config.from_env()
    specs = load_specs(args.task)
    address = args.address or os.environ.get("FACTORY_TEMPORAL_ADDRESS", "localhost:7233")
    server = LocalTemporal(address, cfg.state_dir / "temporal")
    started = False
    try:
        started = await server.start()
        client = await Client.connect(address)
        async with AsyncExitStack() as stack:
            await _open_workers(client, specs, stack, args.max_activities)
            handles = [await _admit(client, spec) for spec in specs]
            print(f"admitted {len(specs)} task(s); temporal={'started' if started else 'existing'}")
            if args.no_follow:
                for handle in handles:
                    print(handle.id)
                return 0
            return await _follow(client, handles, args.approve_by, cfg.state_dir)
    finally:
        server.stop()


def _print_receipt(state_dir: Path, task_id: str) -> int:
    path = receipts.receipt_path(state_dir, workflow_id(task_id))
    if not path.exists():
        print(f"no receipt for {task_id}", file=sys.stderr)
        return 1
    doc = json.loads(path.read_text())
    problems = receipts.validate(doc)
    print(json.dumps({"path": str(path), "valid": not problems, "problems": problems,
                      "summary": _receipt_summary(path),
                      "status": doc["status"], "entries": sorted(doc["entries"])},
                     indent=2, sort_keys=True))
    return 0 if not problems else 1


async def status(args) -> int:
    cfg = Config.from_env()
    address = args.address or os.environ.get("FACTORY_TEMPORAL_ADDRESS", "localhost:7233")
    try:
        client = await Client.connect(address)
    except Exception:
        client = None
    code = 0
    for task_id in args.task_id:
        row = {"task": task_id}
        if client:
            handle = client.get_workflow_handle(workflow_id(task_id))
            try:
                row["state"] = await handle.query(TaskWorkflow.state)
                row["temporal"] = (await handle.describe()).status.name
            except Exception as exc:
                row["temporal_error"] = type(exc).__name__
        row["receipt"] = _receipt_summary(receipts.receipt_path(cfg.state_dir, workflow_id(task_id)))
        if not row["receipt"]:
            code = 1
        print(json.dumps(row, sort_keys=True))
    return code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-factory")
    parser.add_argument("--address", help="Temporal address (default localhost:7233)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    up_ = sub.add_parser("up", help="start Temporal if needed, run a worker, admit tasks")
    up_.add_argument("--task", action="append", required=True, help="TaskSpec JSON file")
    up_.add_argument("--no-follow", action="store_true")
    up_.add_argument("--approve-by", default="", help="explicitly auto-approve as this operator")
    up_.add_argument("--max-activities", type=int, default=10)
    st = sub.add_parser("status", help="show state and receipt for a task")
    st.add_argument("task_id", nargs="+")
    rc = sub.add_parser("receipt", help="validate and summarize a terminal receipt")
    rc.add_argument("task_id")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.cmd == "up":
        code = asyncio.run(up(args))
    elif args.cmd == "status":
        code = asyncio.run(status(args))
    else:
        code = _print_receipt(Config.from_env().state_dir, args.task_id)
    sys.exit(code)


if __name__ == "__main__":
    main()
