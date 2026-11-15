"""One-command local operation: Temporal dev server, workers, tasks, live status.

`python -m agent_factory.launcher up --task task.json` starts a local Temporal
server when the configured address is unreachable, runs the worker in this
process, admits the tasks and reports state, review, receipts and measured
step time. With `--harness` it also starts the Temporal Agent Harness console
and the coordinator worker; the console is a coordination surface, not the
executor or approval authority.

Nothing is deployed and no credential enters workflow history.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import tomllib
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from temporalio.client import Client
from temporalio.client import WorkflowFailureError
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.worker import Worker

from . import receipts
from .activities import ALL
from .client import validate_batch, workflow_id
from .config import Config
from .connection import (DEFAULT_ADDRESS, connect, is_loopback, resolve_connect_config)
from .models import Decision, TaskSpec
from .workflows import TaskWorkflow

TERMINAL = receipts.TERMINAL
FACTORY_ROOT = Path(__file__).resolve().parents[2]
HARNESS_STACK_SCHEMA = "agent-factory.harness-stack/1"
HARNESS_API_TIMEOUT_SECONDS = 120.0
HARNESS_STARTUP_GRACE_SECONDS = 0.75


class HarnessError(RuntimeError):
    """The harness layer cannot start or stopped during startup."""


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
            await asyncio.wait_for(connect(self.address), timeout=2)
            return True
        except Exception:
            return False

    async def start(self) -> bool:
        if await self._reachable():
            return False
        if not is_loopback(self.address):
            raise RuntimeError(
                f"Temporal target {self.address} is unreachable; refusing to start a local "
                "dev server for a remote target")
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


@dataclass(frozen=True)
class HarnessSettings:
    registry: Path
    port: int
    task_queue: str
    factory_root: Path = FACTORY_ROOT


def default_harness_registry() -> Path:
    return (FACTORY_ROOT / "harness" / "agents.toml").resolve()


def resolve_harness_registry(path: str | None) -> Path:
    return Path(path).expanduser().resolve() if path else default_harness_registry()


def harness_dev_command(settings: HarnessSettings) -> list[str]:
    """The packaged session manager + API/console, started through the harness extra."""
    return ["uv", "run", "--extra", "harness", "temporal-agent-harness", "dev",
            str(settings.registry), "--port", str(settings.port), "--host", "127.0.0.1"]


def coordinator_command() -> list[str]:
    return [sys.executable, "-m", "agent_factory.harness.worker"]


def harness_env(settings: HarnessSettings, address: str,
                base: dict[str, str] | None = None) -> dict[str, str]:
    """Connection env for the harness and coordinator; credentials stay inherited."""
    env = dict(os.environ if base is None else base)
    env["TEMPORAL_ADDRESS"] = address
    env["FACTORY_TEMPORAL_ADDRESS"] = address
    env["FACTORY_HARNESS_TASK_QUEUE"] = settings.task_queue
    if is_loopback(address):
        # A Cloud key/profile left in the shell must not add TLS to a local dev server.
        # Keep an explicit TLS setting only when no Cloud key was present.
        had_key = env.pop("TEMPORAL_API_KEY", None) is not None
        env.pop("TEMPORAL_CONFIG_FILE", None)
        env.pop("TEMPORAL_PROFILE", None)
        if had_key:
            env.pop("TEMPORAL_TLS", None)
    src = str(settings.factory_root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def harness_preflight_reason(settings: HarnessSettings) -> str | None:
    """Return a precise blocker for `--harness`, or None when the layer can start."""
    if not settings.registry.is_file():
        return (f"harness registry not found: {settings.registry}; the harness stack needs "
                f"factory/harness/agents.toml (see factory/HARNESS.md), or rerun without --harness")
    pyproject = settings.factory_root / "pyproject.toml"
    if not pyproject.is_file():
        return (f"factory project not found: {pyproject}; --harness runs "
                f"`uv run --extra harness` from the factory directory")
    try:
        extras = tomllib.loads(pyproject.read_text()).get("project", {}).get(
            "optional-dependencies", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return f"cannot read {pyproject}: {type(exc).__name__}: {exc}"
    if "harness" not in extras:
        return (f"the `harness` extra is not declared in {pyproject}; --harness needs "
                f"`uv run --extra harness temporal-agent-harness`, or rerun without --harness")
    if not shutil.which("uv"):
        return "`uv` is not on PATH; --harness starts the harness through `uv run --extra harness`"
    worker = settings.factory_root / "src" / "agent_factory" / "harness" / "worker.py"
    if not worker.is_file():
        try:
            available = importlib.util.find_spec("agent_factory.harness.worker") is not None
        except Exception:
            available = False
        if not available:
            return ("coordinator package is unavailable: agent_factory.harness.worker was not "
                    f"found ({worker}); install the coordinator package or rerun without --harness")
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _console_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def _temporal_ui(address: str, started: bool = False) -> str:
    host, _, port = address.rpartition(":")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return ""
    if port == "7233":
        return "http://localhost:8233"
    if started and port.isdigit():
        return f"http://localhost:{int(port) + 1000}"
    return ""


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _record_path(state_dir: Path) -> Path:
    return Path(state_dir) / "harness" / "stack.json"


def _read_stack_record(state_dir: Path) -> dict:
    path = _record_path(state_dir)
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def harness_liveness(state_dir: Path, port: int | None = None) -> dict:
    """Report the recorded stack and whether its port/processes are alive now."""
    record = _read_stack_record(state_dir)
    effective = port or record.get("port") or 8000
    processes = {}
    for name, pid in (record.get("processes") or {}).items():
        processes[name] = {"pid": pid, "alive": _pid_alive(pid)}
    result = {"port": effective, "console_url": _console_url(effective),
              "listening": _port_open(effective), "processes": processes}
    if record:
        result.update({"state": record.get("state"), "registry": record.get("registry"),
                       "coordinator_queue": record.get("coordinator_queue"),
                       "factory_queues": record.get("factory_queues"),
                       "record": str(_record_path(state_dir))})
    return result


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


async def _wait_for_api(port: int, proc: subprocess.Popen, log_path: Path,
                        timeout: float = HARNESS_API_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise HarnessError(
                f"harness exited before its API opened (exit {proc.returncode}); log: {log_path}")
        if _port_open(port):
            return
        await asyncio.sleep(0.25)
    raise HarnessError(
        f"harness API did not accept connections on 127.0.0.1:{port} within {timeout:.0f}s; "
        f"log: {log_path}")


class HarnessStack:
    """Harness dev server + coordinator worker, stopped as process groups."""

    def __init__(self, settings: HarnessSettings, address: str, state_dir: Path,
                 factory_queues: list[str]):
        self.settings = settings
        self.address = address
        self.state_dir = Path(state_dir)
        self.log_dir = self.state_dir / "harness"
        self.factory_queues = list(factory_queues)
        self.procs: dict[str, subprocess.Popen] = {}
        self.started_at: str | None = None
        self._record: dict | None = None
        self._stopped = False

    @property
    def console_url(self) -> str:
        return _console_url(self.settings.port)

    def _log_path(self, name: str) -> Path:
        return self.log_dir / f"{name}.log"

    def _document(self, state: str, error: str | None = None) -> dict:
        doc = {
            "schema": HARNESS_STACK_SCHEMA,
            "state": state,
            "address": self.address,
            "port": self.settings.port,
            "console_url": self.console_url,
            "registry": str(self.settings.registry),
            "coordinator_queue": self.settings.task_queue,
            "factory_queues": self.factory_queues,
            "processes": {name: proc.pid for name, proc in self.procs.items()},
            "log_dir": str(self.log_dir),
            "started_at": self.started_at,
            "updated_at": _now(),
        }
        if error:
            doc["error"] = error
        if state in {"stopped", "failed"}:
            doc["stopped_at"] = doc["updated_at"]
        return doc

    def _write_record(self, state: str, error: str | None = None) -> None:
        if self._record is None:
            return
        self._record = self._document(state, error)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = _record_path(self.state_dir)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._record, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)

    def _spawn(self, name: str, command: list[str]) -> subprocess.Popen:
        path = self._log_path(name)
        try:
            with open(path, "ab") as log:
                proc = subprocess.Popen(
                    command, cwd=str(self.settings.factory_root),
                    env=harness_env(self.settings, self.address), stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            raise HarnessError(
                f"cannot start {name}: {type(exc).__name__}: {exc}; log: {path}") from exc
        self.procs[name] = proc
        self._write_record("starting")
        return proc

    async def start(self) -> None:
        if _port_open(self.settings.port):
            raise HarnessError(
                f"port {self.settings.port} is already accepting connections; choose another "
                f"--harness-port or stop the process using it")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = _now()
        self._record = self._document("starting")
        self._write_record("starting")
        try:
            harness = self._spawn("harness", harness_dev_command(self.settings))
            await _wait_for_api(self.settings.port, harness, self._log_path("harness"))
            coordinator = self._spawn("coordinator", coordinator_command())
            await asyncio.sleep(HARNESS_STARTUP_GRACE_SECONDS)
            if coordinator.poll() is not None:
                raise HarnessError(
                    f"coordinator exited during startup (exit {coordinator.returncode}); "
                    f"log: {self._log_path('coordinator')}")
        except BaseException as exc:
            reason = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            self.stop(error=reason)
            raise
        self._write_record("running")

    def stop(self, error: str | None = None) -> None:
        if self._stopped:
            if error:
                self._write_record("failed", error)
            return
        self._stopped = True
        for name in ("coordinator", "harness"):
            proc = self.procs.get(name)
            if proc is not None:
                _stop_process(proc)
        if self._record is not None:
            self._write_record("failed" if error else "stopped", error)


def _startup_block(settings: HarnessSettings, address: str, started: bool, queues: list[str],
                   handles: list, log_dir: Path) -> str:
    ui = _temporal_ui(address, started)
    tasks = ", ".join(handle.id for handle in handles) if handles else "(none; waiting for Ctrl-C)"
    lines = [
        "READY",
        f"  Temporal        {address} ({'started' if started else 'existing'})"
        + (f"  ui={ui}" if ui else "  ui=(remote address; not reported)"),
        f"  Harness Console {_console_url(settings.port)}",
        f"  Registry        {settings.registry}",
        f"  Coordinator     {settings.task_queue}",
        f"  Factory queues  {', '.join(queues)}",
        f"  Tasks           {tasks}",
        f"  Logs            {log_dir}",
    ]
    return "\n".join(lines)


def _factory_queues(specs: list[TaskSpec], harness: bool) -> list[str]:
    queues = {spec.task_queue for spec in specs}
    if harness:
        queues.add(os.environ.get("FACTORY_TASK_QUEUE", "factory"))
    return sorted(queues)


async def _open_workers(client: Client, queues: list[str], stack: AsyncExitStack,
                        limit: int) -> None:
    for queue in sorted(set(queues)):
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
    specs = load_specs(args.task or [])
    if not specs and not args.harness:
        print("error: nothing to run; pass --task <spec.json> (repeatable) or --harness",
              file=sys.stderr)
        return 2
    address = (args.address or resolve_connect_config().get("target_host")
               or DEFAULT_ADDRESS)
    server = LocalTemporal(address, cfg.state_dir / "temporal")
    harness: HarnessStack | None = None
    settings: HarnessSettings | None = None
    queues = _factory_queues(specs, args.harness)
    if args.harness:
        settings = HarnessSettings(
            registry=resolve_harness_registry(args.harness_registry),
            port=args.harness_port,
            task_queue=os.environ.get("FACTORY_HARNESS_TASK_QUEUE", "factory-coordinator"))
        reason = harness_preflight_reason(settings)
        if reason:
            print(f"error: {reason}", file=sys.stderr)
            return 2
        harness = HarnessStack(settings, address, cfg.state_dir, queues)
    started = False
    try:
        started = await server.start()
        client = await connect(address)
        async with AsyncExitStack() as stack:
            await _open_workers(client, queues, stack, args.max_activities)
            if harness and settings:
                try:
                    await harness.start()
                except HarnessError as exc:
                    print(f"error: {exc}", file=sys.stderr)
                    return 2
            handles = [await _admit(client, spec) for spec in specs]
            if harness and settings:
                print(_startup_block(settings, address, started, queues, handles,
                                     harness.log_dir), flush=True)
            else:
                print(f"admitted {len(specs)} task(s); temporal={'started' if started else 'existing'}")
            if args.no_follow and not harness:
                for handle in handles:
                    print(handle.id)
                return 0
            if args.no_follow or not handles:
                await asyncio.Event().wait()
                return 0
            return await _follow(client, handles, args.approve_by, cfg.state_dir)
    finally:
        if harness:
            harness.stop()
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
    address = (args.address or resolve_connect_config().get("target_host")
               or DEFAULT_ADDRESS)
    harness_info = None
    if args.harness_port is not None or _record_path(cfg.state_dir).exists():
        harness_info = harness_liveness(cfg.state_dir, args.harness_port)
    if not args.task_id:
        if harness_info is None:
            print("error: status needs a task id or an existing harness stack record",
                  file=sys.stderr)
            return 2
        print(json.dumps({"harness": harness_info}, sort_keys=True))
        return 0
    try:
        client = await connect(address)
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
        if harness_info is not None:
            row["harness"] = harness_info
        if not row["receipt"]:
            code = 1
        print(json.dumps(row, sort_keys=True))
    return code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-factory")
    parser.add_argument("--address", help="Temporal address (default localhost:7233)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    up_ = sub.add_parser("up", help="start Temporal if needed, run a worker, admit tasks")
    up_.add_argument("--task", action="append", default=[],
                     help="TaskSpec JSON file; repeatable, optional with --harness")
    up_.add_argument("--harness", action="store_true",
                     help="also start the Temporal Agent Harness console and coordinator worker")
    up_.add_argument("--harness-registry", default=None,
                     help="harness agents.toml (default <factory>/harness/agents.toml)")
    up_.add_argument("--harness-port", type=int, default=8000,
                     help="harness console/API port (default 8000)")
    up_.add_argument("--no-follow", action="store_true",
                     help="do not follow workflows; with --harness stay up until Ctrl-C")
    up_.add_argument("--approve-by", default="", help="explicitly auto-approve as this operator")
    up_.add_argument("--max-activities", type=int, default=10)
    st = sub.add_parser("status", help="show harness liveness, state and receipt for a task")
    st.add_argument("task_id", nargs="*")
    st.add_argument("--harness-port", type=int, default=None,
                    help="check this port instead of the recorded harness port")
    rc = sub.add_parser("receipt", help="validate and summarize a terminal receipt")
    rc.add_argument("task_id")
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.cmd == "up":
            code = asyncio.run(up(args))
        elif args.cmd == "status":
            code = asyncio.run(status(args))
        else:
            code = _print_receipt(Config.from_env().state_dir, args.task_id)
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
