"""Remote acceptance runner for the factory control plane and compute worker.

This module is the single executable acceptance surface for the remote gates:

1. ``preflight``   - Temporal Cloud auth, namespace and a non-loopback target.
2. ``services``    - remote systemd services and task-queue pollers.
3. ``resources``   - process RSS/CPU and host headroom, with explicit caps.
4. ``task``        - one real OpenCode engineering task with independent review.
5. ``readback``    - fresh-client readback, receipt provenance and uniqueness.
6. ``independence``- a detached Mac client; remote progress is proven by history.
7. ``restart``     - an isolated batch-worker restart and checkpoint reuse.
8. ``bsc``         - one real read-only BSC batch through the A2 BatchWorkflow.

It is opt-in:

    FACTORY_REMOTE_ACCEPTANCE=1 \
    FACTORY_ACCEPTANCE_REMOTE_SSH=<ssh-alias> \
    ... uv run python tests/acceptance_remote.py --gate preflight --gate services

No host, address, origin or credential is stored in this file. Private values
come from the environment or a private config file and are hashed in evidence.
Sensitive environment values are redacted from every error and report.

Exit codes: 0 all selected gates PASS, 1 a gate FAILED, 2 BLOCKED or misuse.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import gc
import hashlib
import json
import os
import platform
import posixpath
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping

from temporalio.api.enums.v1 import EventType, TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest, DescribeTaskQueueRequest
from temporalio.client import Client, WorkflowFailureError

from agent_factory import gitops, receipts
from agent_factory.client import decide, start_task
from agent_factory.config import Config
from agent_factory.connection import connect, is_loopback, resolve_connect_config
from agent_factory.models import TaskSpec
from agent_factory.workflows import TaskWorkflow

SCHEMA = "agent-factory.remote-acceptance/1"
GLOBAL_FLAG = "FACTORY_REMOTE_ACCEPTANCE"
DEFAULT_QUEUES = ("factory-code", "factory-coordinator", "bsc-batch")
SAFE_STATUSES = {"PASS", "FAIL", "BLOCKED", "SKIP"}
SENSITIVE_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)", re.I)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINAL_TASK_STATES = set(receipts.TERMINAL)
REMOTE_HEALTH_STATES = {"active", "running", "up", "healthy"}

CALC_BUG = """def add(a, b):
    return a - b
"""

TEST_CALC = """import unittest

from app.calc import add, mul


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_mul(self):
        self.assertEqual(mul(2, 3), 6)


if __name__ == "__main__":
    unittest.main()
"""

PROMPT_FIX_ADD = (
    "In this repository, app/calc.py has a bug: add(a, b) returns a - b. "
    "Fix add so it returns the sum. Only modify files under app/. "
    "Do not run any git commands. Do not modify anything under tests/. "
    "Do not add mul in this step; a later step does that. "
    "Reply with one short line when done."
)

PROMPT_ADD_MUL = (
    "In this repository, app/calc.py already has a correct add(a, b). "
    "Add a new function mul(a, b) that returns the product of a and b. "
    "tests/test_calc.py already tests mul and must not be changed. "
    "Only modify files under app/. Do not run any git commands. "
    "Do not modify anything under tests/. Reply with one short line when done."
)

BATCH_RESTART_SCRIPT = """#!/bin/bash
set -euo pipefail
case "${FACTORY_BATCH_UNIT_ID:-}" in
  u0)
    printf 'u0\n' > effects.log
    printf 'zero\n' > out0.txt
    ;;
  u1)
    printf '%s\n' "$$" > slow.pid
    printf 'u0\nu1\n' > effects.log
    sleep 45
    printf 'one\n' > out1.txt
    ;;
  *)
    echo "unexpected unit ${FACTORY_BATCH_UNIT_ID:-}" >&2
    exit 2
    ;;
esac
"""

BATCH_RESTART_DQ = """#!/bin/bash
set -euo pipefail
test -f out0.txt
test -f out1.txt
printf '{"status":"PASS","units":2,"mode":"read_only","writes":0}\\n' > dq.json
"""


class AcceptanceBlocked(RuntimeError):
    """A prerequisite is absent; the gate did not run and did not pass."""

    def __init__(self, reason: str, *, missing: Iterable[str] = ()) -> None:
        super().__init__(reason)
        self.missing = tuple(missing)


class AcceptanceFailed(RuntimeError):
    """The gate ran and produced a result that cannot be accepted."""


@dataclass(frozen=True)
class Settings:
    run_id: str
    queues: tuple[str, ...]
    min_pollers: int
    poller_requirements: Mapping[str, str]
    remote_ssh: str
    services: tuple[str, ...]
    health_cmd: str
    remote_state_dir: str
    remote_work_dir: str
    remote_factory_dir: str
    remote_python: str
    remote_env_file: str
    origin: str
    origin_scratch: bool
    base_ref: str
    task_queue: str
    batch_queue: str
    review_model: str
    opencode_bin: str
    test_python: str
    approver: str
    allow_paid: bool
    timeout_seconds: float
    detach_seconds: float
    independence_sleep: float
    restart_sleep: float
    allow_restart: bool
    restart_cmd: str
    bsc_manifest: str
    allow_bsc: bool
    bsc_dq_expected: Mapping[str, Any]
    bsc_reuse_job: bool
    task_id: str
    report_path: Path
    show_targets: bool
    max_rss_mb: float
    max_cpu_percent: float
    require_activity_pollers: bool
    require_telemetry: bool
    target_host: str
    namespace: str
    tls: bool
    api_key_configured: bool
    local_markers: tuple[str, ...]
    allow_repo_report: bool
    source_branch: str = ""
    source_sha: str = ""
    source_dirty: bool = False


@dataclass
class GateSpec:
    name: str
    summary: str
    required_env: tuple[str, ...]
    destructive: bool = False
    required_flags: tuple[str, ...] = ()


GATES: dict[str, GateSpec] = {
    "preflight": GateSpec(
        "preflight", "Temporal Cloud auth, namespace and remote target", ()),
    "services": GateSpec(
        "services", "Remote services and task-queue pollers",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_SERVICES")),
    "resources": GateSpec(
        "resources", "Worker process RSS/CPU and host headroom",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_SERVICES")),
    "task": GateSpec(
        "task", "One real OpenCode task and independent review",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
         "FACTORY_ACCEPTANCE_ORIGIN"),
        required_flags=("FACTORY_ACCEPTANCE_ORIGIN_SCRATCH", "FACTORY_ACCEPTANCE_ALLOW_PAID")),
    "readback": GateSpec(
        "readback", "Fresh-client receipt provenance and zero duplicate side effects",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
         "FACTORY_ACCEPTANCE_ORIGIN")),
    "independence": GateSpec(
        "independence", "Detached Mac client; remote history proves progress",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
         "FACTORY_ACCEPTANCE_ORIGIN"),
        required_flags=("FACTORY_ACCEPTANCE_ORIGIN_SCRATCH",)),
    "restart": GateSpec(
        "restart", "Isolated batch-worker restart, checkpoint reuse, no duplicate effects",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
         "FACTORY_ACCEPTANCE_RESTART_CMD"),
        destructive=True, required_flags=("FACTORY_ACCEPTANCE_ALLOW_RESTART",)),
    "bsc": GateSpec(
        "bsc", "One real read-only BSC batch with DQ and output readback",
        ("FACTORY_ACCEPTANCE_REMOTE_SSH", "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
         "FACTORY_ACCEPTANCE_BSC_MANIFEST"),
        required_flags=("FACTORY_ACCEPTANCE_ALLOW_BSC",)),
}

DEFAULT_GATES = (
    "preflight", "services", "resources", "task", "readback", "independence", "bsc")

DEPENDENCIES = {
    "readback": ("preflight",),
    "task": ("preflight",),
    "independence": ("preflight",),
    "restart": ("preflight",),
    "bsc": ("preflight",),
}


# ---------------------------------------------------------------------------
# Small deterministic helpers (unit-tested without a network)
# ---------------------------------------------------------------------------


def _env(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return os.environ if env is None else env


def _value(env: Mapping[str, str], name: str, default: str = "") -> str:
    return str(env.get(name, default) or "").strip()


def _flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _integer(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _value(env, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _number(env: Mapping[str, str], name: str, default: float) -> float:
    raw = _value(env, name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _csv(env: Mapping[str, str], name: str, default: Iterable[str] = ()) -> tuple[str, ...]:
    raw = _value(env, name)
    if not raw:
        return tuple(default)
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _json_map(env: Mapping[str, str], name: str,
              default: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    raw = _value(env, name)
    if not raw:
        return dict(default or {})
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def fingerprint(value: str, length: int = 16) -> str:
    """Stable non-reversible label for a private target, path or identity."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def local_markers(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    markers = []
    for value in (socket.gethostname(), platform.node(), platform.node().split(".")[0]):
        if value and value.lower() not in {marker.lower() for marker in markers}:
            markers.append(value)
    markers.extend(_csv(_env(env), "FACTORY_ACCEPTANCE_LOCAL_MARKERS"))
    return tuple(marker for marker in markers if len(marker) >= 3)


def sensitive_values(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    current = _env(env)
    values = {
        value for name, value in current.items()
        if value and len(value) >= 8 and SENSITIVE_NAME.search(name)
    }
    return tuple(sorted(values, key=len, reverse=True))


def source_info(repo_root: Path) -> tuple[str, str, bool]:
    """Best-effort source identity; never fails the acceptance run."""
    def run(*args: str) -> str:
        proc = subprocess.run(["git", "-C", str(repo_root), *args],
                              capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    return run("rev-parse", "--abbrev-ref", "HEAD"), run("rev-parse", "HEAD"), bool(
        run("status", "--porcelain"))


def settings_from_env(env: Mapping[str, str] | None = None,
                      repo_root: Path | None = None) -> Settings:
    current = _env(env)
    run_id = _value(current, "FACTORY_ACCEPTANCE_RUN_ID") or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    try:
        resolved = resolve_connect_config(env=dict(current))
    except Exception:
        resolved = {}
    report = _value(current, "FACTORY_ACCEPTANCE_REPORT")
    state = Path(_value(current, "FACTORY_STATE_DIR") or Config.from_env().state_dir)
    report_path = Path(report).expanduser() if report else (
        state / "acceptance" / f"remote-{run_id}.json")
    branch, sha, dirty = source_info(repo_root) if repo_root else ("", "", False)
    return Settings(
        run_id=run_id,
        queues=_csv(current, "FACTORY_ACCEPTANCE_QUEUES", DEFAULT_QUEUES),
        min_pollers=_integer(current, "FACTORY_ACCEPTANCE_MIN_POLLERS", 1),
        poller_requirements=_json_map(current, "FACTORY_ACCEPTANCE_POLLER_REQUIREMENTS"),
        remote_ssh=_value(current, "FACTORY_ACCEPTANCE_REMOTE_SSH"),
        services=_csv(current, "FACTORY_ACCEPTANCE_SERVICES"),
        health_cmd=_value(current, "FACTORY_ACCEPTANCE_HEALTH_CMD"),
        remote_state_dir=_value(
            current, "FACTORY_ACCEPTANCE_REMOTE_STATE_DIR",
            "/var/lib/alpha-wiki-factory/state"),
        remote_work_dir=_value(
            current, "FACTORY_ACCEPTANCE_REMOTE_WORK_DIR",
            "/var/lib/alpha-wiki-factory/work"),
        remote_factory_dir=_value(
            current, "FACTORY_ACCEPTANCE_REMOTE_FACTORY_DIR",
            "/opt/alpha-wiki-factory/current/factory"),
        remote_python=_value(
            current, "FACTORY_ACCEPTANCE_REMOTE_PYTHON",
            "/opt/alpha-wiki-factory/current-venv/bin/python"),
        remote_env_file=_value(
            current, "FACTORY_ACCEPTANCE_REMOTE_ENV_FILE", "/etc/alpha-wiki/factory.env"),
        origin=_value(current, "FACTORY_ACCEPTANCE_ORIGIN"),
        origin_scratch=_flag(current, "FACTORY_ACCEPTANCE_ORIGIN_SCRATCH"),
        base_ref=_value(current, "FACTORY_ACCEPTANCE_BASE_REF", "main"),
        task_queue=_value(current, "FACTORY_ACCEPTANCE_TASK_QUEUE", "factory-code"),
        batch_queue=_value(current, "FACTORY_ACCEPTANCE_BATCH_QUEUE", "bsc-batch"),
        review_model=_value(current, "FACTORY_ACCEPTANCE_REVIEW_MODEL",
                            "opencode-go/deepseek-v4.1-flash"),
        opencode_bin=_value(current, "FACTORY_ACCEPTANCE_OPENCODE_BIN", "opencode"),
        test_python=_value(current, "FACTORY_ACCEPTANCE_TEST_PYTHON", "python3"),
        approver=_value(current, "FACTORY_ACCEPTANCE_APPROVER", "remote-acceptance"),
        allow_paid=_flag(current, "FACTORY_ACCEPTANCE_ALLOW_PAID"),
        timeout_seconds=_number(current, "FACTORY_ACCEPTANCE_TIMEOUT", 900.0),
        detach_seconds=_number(current, "FACTORY_ACCEPTANCE_DETACH_SECONDS", 25.0),
        independence_sleep=_number(current, "FACTORY_ACCEPTANCE_INDEPENDENCE_SLEEP", 35.0),
        restart_sleep=_number(current, "FACTORY_ACCEPTANCE_RESTART_SLEEP", 45.0),
        allow_restart=_flag(current, "FACTORY_ACCEPTANCE_ALLOW_RESTART"),
        restart_cmd=_value(current, "FACTORY_ACCEPTANCE_RESTART_CMD"),
        bsc_manifest=_value(current, "FACTORY_ACCEPTANCE_BSC_MANIFEST"),
        allow_bsc=_flag(current, "FACTORY_ACCEPTANCE_ALLOW_BSC"),
        bsc_dq_expected=_json_map(
            current, "FACTORY_ACCEPTANCE_BSC_DQ_EXPECT",
            {"mode": "read_only", "writes": 0}),
        bsc_reuse_job=_flag(current, "FACTORY_ACCEPTANCE_BSC_REUSE_JOB"),
        task_id=_value(current, "FACTORY_ACCEPTANCE_TASK_ID"),
        report_path=report_path,
        show_targets=_flag(current, "FACTORY_ACCEPTANCE_SHOW_TARGETS"),
        max_rss_mb=_number(current, "FACTORY_ACCEPTANCE_MAX_RSS_MB", 4096.0),
        max_cpu_percent=_number(current, "FACTORY_ACCEPTANCE_MAX_CPU_PERCENT", 200.0),
        require_activity_pollers=_flag(
            current, "FACTORY_ACCEPTANCE_REQUIRE_ACTIVITY_POLLERS"),
        require_telemetry=_flag(current, "FACTORY_ACCEPTANCE_REQUIRE_TELEMETRY"),
        target_host=str(resolved.get("target_host", "")),
        namespace=str(resolved.get("namespace", "default")),
        tls=bool(resolved.get("tls")),
        api_key_configured=bool(resolved.get("api_key")),
        local_markers=local_markers(current),
        allow_repo_report=_flag(current, "FACTORY_ACCEPTANCE_ALLOW_REPO_REPORT"),
        source_branch=branch,
        source_sha=sha,
        source_dirty=dirty,
    )


def private_values(settings: Settings,
                   env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    values = {
        settings.remote_ssh,
        settings.origin,
        settings.bsc_manifest,
        settings.restart_cmd,
    }
    if not settings.show_targets:
        values.add(settings.target_host)
        if settings.namespace not in {"", "default"}:
            values.add(settings.namespace)
    values.update(sensitive_values(env))
    return tuple(sorted((value for value in values if value), key=len, reverse=True))


def redact(text: str, settings: Settings, env: Mapping[str, str] | None = None) -> str:
    result = str(text)
    for value in private_values(settings, env):
        if value and value in result:
            result = result.replace(value, "<redacted>")
    return result


def public_target(value: str, settings: Settings) -> str:
    if not value:
        return ""
    return value if settings.show_targets else f"sha256:{fingerprint(value)}"


def assertion(name: str, expected: Any, actual: Any, *, ok: bool | None = None) -> dict:
    passed = actual == expected if ok is None else bool(ok)
    return {"name": name, "expected": expected, "actual": actual, "pass": passed}


def assertion_result(result: dict) -> bool:
    return bool(result.get("pass"))


@dataclass
class Context:
    settings: Settings
    env: Mapping[str, str]
    temp_dir: Path
    client: Client | None = None
    documents: dict[str, dict] = field(default_factory=dict)

    async def ensure_client(self) -> Client:
        if self.client is None:
            self.client = await asyncio.wait_for(connect(), timeout=30)
        return self.client

    async def reset_client(self) -> Client:
        self.drop_client()
        return await self.ensure_client()

    def drop_client(self) -> None:
        """Drop the local client object; the Python SDK exposes no close()."""
        self.client = None
        gc.collect()

    async def close(self) -> None:
        self.drop_client()

    async def ssh(self, script: str, *, timeout: float = 120,
                  input_text: str | None = None) -> "CommandResult":
        if not self.settings.remote_ssh:
            raise AcceptanceBlocked(
                "remote SSH is not configured", missing=("FACTORY_ACCEPTANCE_REMOTE_SSH",))
        argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                self.settings.remote_ssh, script]
        return await asyncio.to_thread(run_command, argv, timeout, input_text)

    async def read_remote_text(self, path: str) -> str:
        result = await self.ssh(f"cat -- {shlex.quote(path)}", timeout=60)
        if result.returncode != 0:
            raise AcceptanceFailed(
                f"cannot read remote file ({result.returncode}): "
                f"{redact(result.stderr[-500:], self.settings, self.env)}")
        return result.stdout

    async def read_remote_bytes(self, path: str) -> bytes:
        result = await self.ssh(f"cat -- {shlex.quote(path)}", timeout=60)
        if result.returncode != 0:
            raise AcceptanceFailed(
                f"cannot read remote file ({result.returncode}): "
                f"{redact(result.stderr[-500:], self.settings, self.env)}")
        return result.stdout.encode("utf-8", errors="surrogateescape")

    async def remote_sha256(self, path: str) -> str:
        result = await self.ssh(f"sha256sum -- {shlex.quote(path)}", timeout=60)
        if result.returncode != 0:
            return ""
        return result.stdout.split()[0] if result.stdout.split() else ""

    async def remote_exists(self, path: str) -> bool:
        result = await self.ssh(f"test -e {shlex.quote(path)}", timeout=30)
        return result.returncode == 0

    async def write_remote_text(self, path: str, text: str, *, mode: str = "600") -> None:
        import base64
        parent = posixpath.dirname(path) or "."
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        script = (f"umask 077; mkdir -p {shlex.quote(parent)}; "
                  f"base64 -d > {shlex.quote(path)}; chmod {mode} {shlex.quote(path)}")
        result = await self.ssh(script, timeout=60, input_text=encoded + "\n")
        if result.returncode != 0:
            raise AcceptanceFailed(
                f"cannot write remote file ({result.returncode}): "
                f"{redact(result.stderr[-500:], self.settings, self.env)}")

    async def remote_python(self, script: str, *, timeout: float = 120,
                            env_file: bool = False) -> "CommandResult":
        prefix = ""
        if env_file and self.settings.remote_env_file:
            prefix = (f"set -a; . {shlex.quote(self.settings.remote_env_file)}; set +a; ")
        command = prefix + f"exec {shlex.quote(self.settings.remote_python)} -"
        result = await self.ssh(command, timeout=timeout, input_text=script)
        return result


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    seconds: float


def run_command(argv: list[str], timeout: float,
                input_text: str | None = None) -> CommandResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv, input=input_text, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired as exc:
        return CommandResult(-1, (exc.stdout or "") if isinstance(exc.stdout, str) else "",
                             f"timed out after {timeout:.0f}s", time.monotonic() - started)
    return CommandResult(proc.returncode, proc.stdout, proc.stderr, time.monotonic() - started)


def run_git(args: list[str], cwd: Path | str | None = None) -> str:
    result = run_command(["git", *args], timeout=180)
    if result.returncode != 0:
        raise AcceptanceFailed(
            f"git {args[0]} failed ({result.returncode}): {result.stderr.strip()[-500:]}")
    return result.stdout.strip()


def canonical_status(result: dict) -> dict:
    return {
        "gate": result["gate"],
        "status": result["status"],
        "assertions": result.get("assertions", []),
        "evidence": result.get("evidence", {}),
        "error": result.get("error", ""),
        "started_at": result.get("started_at", ""),
        "finished_at": result.get("finished_at", ""),
        "duration_seconds": result.get("duration_seconds", 0.0),
    }


def summarize(results: list[dict]) -> dict:
    counts = {status: 0 for status in SAFE_STATUSES}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    if counts["FAIL"]:
        outcome = "FAIL"
    elif counts["BLOCKED"] or counts["SKIP"]:
        outcome = "BLOCKED"
    else:
        outcome = "PASS"
    return {"counts": counts, "result": outcome,
            "failed_gates": [r["gate"] for r in results if r["status"] == "FAIL"],
            "blocked_gates": [r["gate"] for r in results if r["status"] == "BLOCKED"],
            "skipped_gates": [r["gate"] for r in results if r["status"] == "SKIP"]}


# ---------------------------------------------------------------------------
# Gate execution
# ---------------------------------------------------------------------------


async def run_gates(settings: Settings, names: Iterable[str],
                    env: Mapping[str, str] | None = None,
                    temp_root: Path | None = None) -> dict:
    selected = list(dict.fromkeys(names))
    unknown = [name for name in selected if name not in GATES]
    if unknown:
        raise ValueError(f"unknown gates: {unknown}")
    if "preflight" not in selected:
        selected.insert(0, "preflight")
    started = datetime.now(timezone.utc)
    temp = temp_root or Path(tempfile.mkdtemp(prefix="factory-acceptance-"))
    ctx = Context(settings=settings, env=_env(env), temp_dir=temp)
    results: list[dict] = []
    try:
        for name in selected:
            spec = GATES[name]
            gate_started = time.monotonic()
            started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            missing = [item for item in spec.required_env
                       if not _value(_env(env), item)]
            missing_flags = [item for item in spec.required_flags
                             if not _flag(_env(env), item)]
            dependency_failures = [
                dependency for dependency in DEPENDENCIES.get(name, ())
                if any(r["gate"] == dependency and r["status"] != "PASS" for r in results)]
            if dependency_failures:
                result = _gate_result(
                    name, "SKIP", [], {},
                    error=f"dependency did not pass: {', '.join(dependency_failures)}",
                    started_at=started_at, started=gate_started)
            elif missing or missing_flags:
                reason = "missing environment or explicit flags"
                result = _gate_result(
                    name, "BLOCKED", [], {"missing_env": missing,
                                          "missing_flags": missing_flags},
                    error=reason, started_at=started_at, started=gate_started)
            else:
                try:
                    assertions, evidence = await GATE_FUNCS[name](ctx)
                    status = "PASS" if all(assertion_result(item) for item in assertions) \
                        else "FAIL"
                    result = _gate_result(name, status, assertions, evidence,
                                          started_at=started_at, started=gate_started)
                except AcceptanceBlocked as exc:
                    result = _gate_result(
                        name, "BLOCKED", [], {"missing_env": list(exc.missing)},
                        error=redact(str(exc), settings, ctx.env),
                        started_at=started_at, started=gate_started)
                except AcceptanceFailed as exc:
                    result = _gate_result(
                        name, "FAIL", [], {},
                        error=redact(str(exc), settings, ctx.env),
                        started_at=started_at, started=gate_started)
                except Exception as exc:  # noqa: BLE001 - acceptance must report, not crash
                    result = _gate_result(
                        name, "FAIL", [], {},
                        error=redact(f"{type(exc).__name__}: {exc}", settings, ctx.env),
                        started_at=started_at, started=gate_started)
            results.append(canonical_status(result))
    finally:
        await ctx.close()
    report = {
        "schema": SCHEMA,
        "run_id": settings.run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_seconds": round(
            (datetime.now(timezone.utc) - started).total_seconds(), 2),
        "source": {
            "branch": settings.source_branch,
            "sha": settings.source_sha,
            "dirty": settings.source_dirty,
        },
        "environment": {
            "temporal": {
                "target": public_target(settings.target_host, settings),
                "target_sha256": fingerprint(settings.target_host) if settings.target_host else "",
                "namespace_sha256": fingerprint(settings.namespace) if settings.namespace else "",
                "tls": settings.tls,
                "api_key_configured": settings.api_key_configured,
            },
            "queues": list(settings.queues),
            "remote_ssh_sha256": fingerprint(settings.remote_ssh) if settings.remote_ssh else "",
            "services": list(settings.services),
            "origin_sha256": fingerprint(settings.origin) if settings.origin else "",
            "bsc_manifest_sha256": (
                fingerprint(settings.bsc_manifest) if settings.bsc_manifest else ""),
            "review_model": settings.review_model,
            "paid_review_authorized": settings.allow_paid,
            "restart_authorized": settings.allow_restart,
            "bsc_authorized": settings.allow_bsc,
        },
        "selected_gates": selected,
        "gates": results,
    }
    report["summary"] = summarize(results)
    report["result"] = report["summary"]["result"]
    report["redaction"] = {
        "sensitive_values": len(sensitive_values(ctx.env)),
        "private_values": len(private_values(settings, ctx.env)),
        "leaks": _leak_count(report, ctx.env),
    }
    _sanitize_report(report, settings, ctx.env)
    return report


def _gate_result(name: str, status: str, assertions: list[dict], evidence: dict, *,
                 error: str = "", started_at: str, started: float) -> dict:
    return {
        "gate": name,
        "status": status,
        "assertions": assertions,
        "evidence": evidence,
        "error": error,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - started, 2),
    }


def _leak_count(report: dict, env: Mapping[str, str]) -> int:
    text = json.dumps(report, sort_keys=True)
    return sum(1 for value in sensitive_values(env) if value and value in text)


def _sanitize_report(value: Any, settings: Settings,
                     env: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        for key, item in list(value.items()):
            value[key] = _sanitize_report(item, settings, env)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _sanitize_report(item, settings, env)
    elif isinstance(value, str):
        return redact(value, settings, env)
    return value


# ---------------------------------------------------------------------------
# Gate 1: preflight
# ---------------------------------------------------------------------------


async def gate_preflight(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    assertions = [
        assertion("temporal_target_configured", True, bool(s.target_host)),
        assertion("temporal_target_is_remote", True, bool(s.target_host)
                  and not is_loopback(s.target_host)),
        assertion("temporal_tls_enabled", True, s.tls),
        assertion("temporal_api_key_configured", True, s.api_key_configured),
        assertion("queues_configured", True, bool(s.queues)),
    ]
    client = await ctx.ensure_client()
    described = await asyncio.wait_for(
        client.workflow_service.describe_namespace(
            DescribeNamespaceRequest(namespace=client.namespace or "default")),
        timeout=15)
    namespace = str(described.namespace_info.name)
    assertions.append(assertion("namespace_matches_config", True,
                                namespace == (s.namespace or "default"),
                                ok=bool(namespace)))
    evidence = {
        "target": public_target(s.target_host, s),
        "target_sha256": fingerprint(s.target_host) if s.target_host else "",
        "namespace_sha256": fingerprint(namespace),
        "tls": bool(s.tls),
        "api_key_configured": bool(s.api_key_configured),
        "queues": list(s.queues),
        "min_pollers": s.min_pollers,
        "poller_requirements_configured": sorted(s.poller_requirements),
    }
    ctx.documents["preflight"] = evidence
    return assertions, evidence


# ---------------------------------------------------------------------------
# Gate 2/3: services and resources
# ---------------------------------------------------------------------------


async def describe_queue(ctx: Context, queue: str,
                         queue_type: TaskQueueType) -> dict:
    client = await ctx.ensure_client()
    response = await asyncio.wait_for(
        client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(
                namespace=client.namespace, task_queue=TaskQueue(name=queue),
                task_queue_type=queue_type),
            timeout=timedelta(seconds=10)),
        timeout=15)
    pollers = []
    for poller in response.pollers:
        if getattr(poller, "identity", ""):
            pollers.append(poller.identity)
    return {
        "count": len(pollers),
        "identities": [fingerprint(identity) for identity in pollers],
        "raw_identities": pollers,
    }


async def poller_snapshot(ctx: Context, queues: Iterable[str] | None = None) -> dict:
    snapshot = {}
    for queue in queues or ctx.settings.queues:
        workflow = await describe_queue(ctx, queue, TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW)
        activity = await describe_queue(ctx, queue, TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY)
        snapshot[queue] = {"workflow": workflow, "activity": activity}
    return snapshot


def _queue_key(queue: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", queue).strip("_") or "queue"


def _identity_markers(identities: Iterable[str], markers: Iterable[str]) -> list[str]:
    lowered = [marker.lower() for marker in markers if marker]
    return [identity for identity in identities
            if any(marker in identity.lower() for marker in lowered)]


def poller_assertions(snapshot: dict, settings: Settings) -> list[dict]:
    results = []
    local_hits: list[str] = []
    for queue, counts in snapshot.items():
        key = _queue_key(queue)
        workflow_count = counts["workflow"]["count"]
        results.append(assertion(
            f"queue_{key}_workflow_pollers", f">={settings.min_pollers}",
            workflow_count, ok=workflow_count >= settings.min_pollers))
        if settings.require_activity_pollers:
            activity_count = counts["activity"]["count"]
            results.append(assertion(
                f"queue_{key}_activity_pollers", f">={settings.min_pollers}",
                activity_count, ok=activity_count >= settings.min_pollers))
        expected = settings.poller_requirements.get(queue, "")
        if expected:
            matches = sum(
                1 for identity in counts["workflow"]["raw_identities"] + [
                    *counts["activity"]["raw_identities"]]
                if expected.lower() in identity.lower())
            results.append(assertion(
                f"queue_{key}_identity_requirement", ">=1 matching poller",
                matches, ok=matches >= 1))
        local_hits.extend(_identity_markers(
            counts["workflow"]["raw_identities"] + counts["activity"]["raw_identities"],
            settings.local_markers))
    results.append(assertion("no_local_poller_identity", 0, len(local_hits),
                             ok=len(local_hits) == 0))
    return results


def safe_poller_evidence(snapshot: dict) -> dict:
    return {
        queue: {
            "workflow_pollers": counts["workflow"]["count"],
            "activity_pollers": counts["activity"]["count"],
            "workflow_identity_sha256": counts["workflow"]["identities"],
            "activity_identity_sha256": counts["activity"]["identities"],
        }
        for queue, counts in snapshot.items()
    }


def parse_service_table(text: str, services: Iterable[str]) -> tuple[dict, dict]:
    expected = list(services)
    found: dict[str, dict] = {}
    host: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if parts[0] == "HOST":
            if len(parts) >= 4:
                host = {"load1": _optional_float(parts[1]),
                        "mem_available_mb": _optional_int(parts[2]),
                        "disk_free_mb": _optional_int(parts[3])}
            continue
        if len(parts) < 3:
            continue
        name = parts[0]
        if name not in expected:
            continue
        pid = _optional_int(parts[3]) if len(parts) > 3 else None
        found[name] = {
            "state": (parts[1] or "").strip().lower(),
            "enabled": (parts[2] or "").strip().lower(),
            "pid": pid if pid and pid > 0 else None,
            "rss_kb": _optional_int(parts[4]) if len(parts) > 4 else None,
            "cpu_percent": _optional_float(parts[5]) if len(parts) > 5 else None,
            "elapsed_seconds": _optional_int(parts[6]) if len(parts) > 6 else None,
        }
    for name in expected:
        found.setdefault(name, {
            "state": "unknown", "enabled": "unknown", "pid": None,
            "rss_kb": None, "cpu_percent": None, "elapsed_seconds": None,
        })
    return found, host


def parse_health_json(text: str, services: Iterable[str]) -> tuple[dict, dict]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AcceptanceFailed(f"health command did not return JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AcceptanceFailed("health command JSON must be an object")
    raw = payload.get("services") if isinstance(payload.get("services"), dict) else payload
    found = {}
    for name in services:
        item = raw.get(name) if isinstance(raw, dict) else None
        if not isinstance(item, dict):
            item = {}
        pid = _optional_int(item.get("pid"))
        found[name] = {
            "state": str(item.get("state", "unknown")).strip().lower(),
            "enabled": str(item.get("enabled", "unknown")).strip().lower(),
            "pid": pid if pid and pid > 0 else None,
            "rss_kb": _optional_int(item.get("rss_kb")),
            "cpu_percent": _optional_float(item.get("cpu_percent")),
            "elapsed_seconds": _optional_int(item.get("elapsed_seconds")),
        }
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    return found, host


def _optional_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


async def service_snapshot(ctx: Context) -> tuple[dict, dict]:
    s = ctx.settings
    if not s.services:
        raise AcceptanceBlocked("no remote services configured",
                                missing=("FACTORY_ACCEPTANCE_SERVICES",))
    if s.health_cmd:
        result = await ctx.ssh(s.health_cmd, timeout=60)
        if result.returncode != 0:
            raise AcceptanceFailed(
                f"health command failed ({result.returncode}): "
                f"{redact(result.stderr[-500:], s, ctx.env)}")
        return parse_health_json(result.stdout, s.services)
    quoted = " ".join(shlex.quote(name) for name in s.services)
    script = f"""set -u
for service in {quoted}; do
  state="$(systemctl is-active "$service" 2>/dev/null || true)"
  enabled="$(systemctl is-enabled "$service" 2>/dev/null || true)"
  pid="$(systemctl show -p MainPID --value "$service" 2>/dev/null || true)"
  rss=""; cpu=""; etimes=""
  if [ -n "$pid" ] && [ "$pid" != "0" ] && [ -d "/proc/$pid" ]; then
    set -- $(ps -o rss=,pcpu=,etimes= -p "$pid" 2>/dev/null || true)
    rss="${{1:-}}"; cpu="${{2:-}}"; etimes="${{3:-}}"
  fi
  printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "$service" "$state" "$enabled" "$pid" "$rss" "$cpu" "$etimes"
done
read -r load1 _ < /proc/loadavg
mem="$(awk '/MemAvailable/{{print int($2/1024)}}' /proc/meminfo 2>/dev/null || true)"
disk="$(df -Pm /var/lib 2>/dev/null | awk 'NR==2{{print $4}}' || true)"
printf 'HOST\\t%s\\t%s\\t%s\\n' "$load1" "$mem" "$disk"
"""
    result = await ctx.ssh(script, timeout=60)
    if result.returncode != 0:
        raise AcceptanceFailed(
            f"service query failed ({result.returncode}): "
            f"{redact(result.stderr[-500:], s, ctx.env)}")
    return parse_service_table(result.stdout, s.services)


async def gate_services(ctx: Context) -> tuple[list[dict], dict]:
    services, host = await service_snapshot(ctx)
    snapshot = await poller_snapshot(ctx)
    assertions = poller_assertions(snapshot, ctx.settings)
    for name, item in services.items():
        assertions.append(assertion(
            f"service_{_queue_key(name)}_active", "active/running", item["state"],
            ok=item["state"] in REMOTE_HEALTH_STATES))
    evidence = {
        "services": services,
        "host": host,
        "pollers": safe_poller_evidence(snapshot),
        "local_marker_count": len(ctx.settings.local_markers),
    }
    ctx.documents["services"] = evidence
    return assertions, evidence


async def gate_resources(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    services, host = await service_snapshot(ctx)
    assertions = []
    evidence_services = {}
    for name, item in services.items():
        key = _queue_key(name)
        assertions.append(assertion(f"resource_{key}_pid_present", True,
                                    bool(item["pid"]), ok=bool(item["pid"])))
        rss_mb = None if item["rss_kb"] is None else round(item["rss_kb"] / 1024, 1)
        assertions.append(assertion(
            f"resource_{key}_rss_mb", f"<={s.max_rss_mb:g}", rss_mb,
            ok=rss_mb is not None and rss_mb <= s.max_rss_mb))
        cpu = item["cpu_percent"]
        assertions.append(assertion(
            f"resource_{key}_cpu_percent", f"<={s.max_cpu_percent:g}", cpu,
            ok=cpu is not None and cpu <= s.max_cpu_percent))
        evidence_services[name] = {
            "pid_present": bool(item["pid"]),
            "rss_mb": rss_mb,
            "cpu_percent": cpu,
            "elapsed_seconds": item["elapsed_seconds"],
        }
    assertions.append(assertion("host_memory_available_present", True,
                                host.get("mem_available_mb") is not None,
                                ok=host.get("mem_available_mb") is not None))
    evidence = {"services": evidence_services, "host": host,
                "caps": {"max_rss_mb": s.max_rss_mb,
                         "max_cpu_percent": s.max_cpu_percent}}
    ctx.documents["resources"] = evidence
    return assertions, evidence


# ---------------------------------------------------------------------------
# Gate 4: real OpenCode engineering task
# ---------------------------------------------------------------------------


FIXTURE_FILES = {
    "AGENTS.md": "# contract\n\nOnly change files under app/.\n",
    "wiki/graph/context_brief.md": "# brief\n\nA tiny calculator package.\n",
    ".gitignore": "__pycache__/\n*.pyc\n.opencode/\n.DS_Store\n",
    "app/__init__.py": "",
    "app/calc.py": CALC_BUG,
    "tests/test_calc.py": TEST_CALC,
}


def seed_origin(settings: Settings, temp_dir: Path, run_id: str,
                marker: str) -> tuple[str, str, Path]:
    """Push a unique base branch; never touches main."""
    if not settings.origin_scratch:
        raise AcceptanceBlocked("origin writes require FACTORY_ACCEPTANCE_ORIGIN_SCRATCH=1",
                                missing=("FACTORY_ACCEPTANCE_ORIGIN_SCRATCH",))
    if not settings.origin:
        raise AcceptanceBlocked("origin is not configured",
                                missing=("FACTORY_ACCEPTANCE_ORIGIN",))
    clone = temp_dir / f"origin-{marker}"
    base_branch = f"acceptance/{run_id}-{marker}"
    remote = run_command(["git", "ls-remote", settings.origin,
                          f"refs/heads/{settings.base_ref}"], timeout=120)
    if remote.returncode != 0 or not remote.stdout.strip():
        raise AcceptanceFailed(
            f"origin/base_ref is not reachable from this host ({remote.returncode})")
    clone_result = run_command(["git", "clone", "--quiet", settings.origin, str(clone)],
                               timeout=300)
    if clone_result.returncode != 0:
        raise AcceptanceFailed(f"git clone failed ({clone_result.returncode})")
    run_git(["config", "user.email", "acceptance@localhost"], cwd=clone)
    run_git(["config", "user.name", "Remote Acceptance"], cwd=clone)
    run_git(["fetch", "--quiet", "origin", settings.base_ref], cwd=clone)
    run_git(["checkout", "--quiet", "-B", base_branch, "FETCH_HEAD"], cwd=clone)
    for name, body in FIXTURE_FILES.items():
        path = clone / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    run_git(["add", "-A"], cwd=clone)
    run_git(["commit", "--quiet", "-m", f"acceptance fixture {run_id}"], cwd=clone)
    base_sha = run_git(["rev-parse", "HEAD"], cwd=clone)
    push = run_command(["git", "push", "--quiet", settings.origin,
                        f"HEAD:refs/heads/{base_branch}"], timeout=180)
    if push.returncode != 0:
        raise AcceptanceFailed(f"git push of acceptance base failed ({push.returncode})")
    return base_branch, base_sha, clone


def task_assertions(receipt: dict, result: Any, state: str,
                    settings: Settings) -> list[dict]:
    review = receipt.get("entries", {}).get("review", {})
    tests = receipt.get("entries", {}).get("tests", {})
    approval = receipt.get("entries", {}).get("approval", {})
    return [
        assertion("task_state", "PR_OPEN", state, ok=state == "PR_OPEN"),
        assertion("task_result_status", "PR_OPEN", result.status,
                  ok=result.status == "PR_OPEN"),
        assertion("tests_passed", True, tests.get("passed"),
                  ok=tests.get("passed") is True),
        assertion("review_verdict", "APPROVE", review.get("verdict"),
                  ok=review.get("verdict") == "APPROVE"),
        assertion("reviewer", f"opencode:{settings.review_model}",
                  review.get("reviewer"),
                  ok=review.get("reviewer") == f"opencode:{settings.review_model}"),
        assertion("review_diff_sha256_present", True,
                  bool(SHA256_RE.fullmatch(str(review.get("diff_sha256", "")))),
                  ok=bool(SHA256_RE.fullmatch(str(review.get("diff_sha256", ""))))),
        assertion("review_prompt_sha256_present", True,
                  bool(SHA256_RE.fullmatch(str(review.get("prompt_sha256", "")))),
                  ok=bool(SHA256_RE.fullmatch(str(review.get("prompt_sha256", ""))))),
        assertion("approval_verdict", "approve", approval.get("verdict"),
                  ok=approval.get("verdict") == "approve"),
        assertion("approval_by", settings.approver, approval.get("by"),
                  ok=approval.get("by") == settings.approver),
        assertion("receipt_digest_present", True,
                  bool(SHA256_RE.fullmatch(str(receipt.get("digest", "")))),
                  ok=bool(SHA256_RE.fullmatch(str(receipt.get("digest", ""))))),
    ]


async def wait_task_state(ctx: Context, handle: Any, predicate: Callable[[str], bool],
                          timeout: float) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = str(await handle.query(TaskWorkflow.state))
        if predicate(last):
            return last
        if last in TERMINAL_TASK_STATES:
            return last
        await asyncio.sleep(2)
    raise AcceptanceFailed(f"task did not reach the expected state; last={last!r}")


async def read_receipt(ctx: Context, workflow_id: str) -> dict:
    path = posixpath.join(ctx.settings.remote_state_dir, "receipts",
                          f"{workflow_id}.json")
    text = await ctx.read_remote_text(path)
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AcceptanceFailed(f"receipt is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise AcceptanceFailed("receipt is not a JSON object")
    return document


async def receipt_file_count(ctx: Context, workflow_id: str) -> int:
    directory = posixpath.join(ctx.settings.remote_state_dir, "receipts")
    result = await ctx.ssh(
        f"find {shlex.quote(directory)} -maxdepth 1 "
        f"-name {shlex.quote(workflow_id + '.json')} | wc -l", timeout=30)
    return _optional_int(result.stdout) or 0


async def read_prs(ctx: Context) -> dict:
    path = posixpath.join(ctx.settings.remote_state_dir, "prs.json")
    if not await ctx.remote_exists(path):
        return {}
    text = await ctx.read_remote_text(path)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AcceptanceFailed(f"PR registry is not valid JSON: {exc}") from exc
    return value if isinstance(value, dict) else {}


def branch_digest(origin: str, task_id: str, base_sha: str, head_sha: str,
                  temp_dir: Path) -> tuple[str, list[str], int]:
    cache = gitops.ensure_cache(temp_dir / "cache", origin)
    diff = gitops.diff_text(cache, base_sha, head_sha)
    names = gitops.git(["diff", "--name-only", base_sha, head_sha], cwd=cache)
    log = gitops.git(["log", "--format=%B", f"refs/remotes/origin/{gitops.branch_name(task_id)}"],
                     cwd=cache)
    trailers = sum(1 for line in log.splitlines()
                   if line.startswith(f"Factory-Step: {task_id}/"))
    return hashlib.sha256(diff.encode()).hexdigest(), names.splitlines(), trailers


async def gate_task(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    if not s.allow_paid:
        raise AcceptanceBlocked("paid review requires FACTORY_ACCEPTANCE_ALLOW_PAID=1",
                                missing=("FACTORY_ACCEPTANCE_ALLOW_PAID",))
    base_branch, base_sha, _clone = seed_origin(s, ctx.temp_dir, s.run_id, "task")
    task_id = f"acc-code-{s.run_id}"
    steps = [
        [s.opencode_bin, "run", "--auto", "-m", s.review_model, PROMPT_FIX_ADD],
        [s.opencode_bin, "run", "--auto", "-m", s.review_model, PROMPT_ADD_MUL],
    ]
    spec = TaskSpec(
        task_id=task_id, repo=s.origin, agent_steps=steps,
        test_command=[s.test_python, "-m", "unittest", "discover", "-s", "tests", "-q"],
        owned_paths=["app"], task_queue=s.task_queue, base_ref=base_branch,
        reviewer="opencode", review_model=s.review_model, require_approval=True,
        max_step_seconds=300, max_attempts=2, heartbeat_timeout_seconds=15,
        test_timeout_seconds=180, approval_timeout_seconds=3600, pr_backend="local")
    client = await ctx.ensure_client()
    services_before = {}
    with contextlib.suppress(Exception):
        services_before, _ = await service_snapshot(ctx)
    started = time.monotonic()
    handle = await start_task(client, spec)
    described = await handle.describe()
    run_id = described.run_id
    state = await wait_task_state(
        ctx, handle, lambda value: value == "AWAITING_APPROVAL", 600)
    if state != "AWAITING_APPROVAL":
        receipt = await read_receipt(ctx, f"task-{task_id}")
        raise AcceptanceFailed(f"task stopped at {state!r}: {receipt.get('entries', {}).get('failure')}")
    review_receipt = await read_receipt(ctx, f"task-{task_id}")
    awaiting_assertions = task_assertions(
        review_receipt, type("Result", (), {"status": "AWAITING_APPROVAL"})(),
        state, s)
    if not all(assertion_result(item) for item in awaiting_assertions[2:7]):
        raise AcceptanceFailed("review did not meet the acceptance contract before approval")
    approval = await decide(client, task_id, "approve", s.approver,
                            f"remote acceptance {s.run_id}")
    try:
        result = await asyncio.wait_for(handle.result(), timeout=s.timeout_seconds)
    except WorkflowFailureError as exc:
        receipt = await read_receipt(ctx, f"task-{task_id}")
        raise AcceptanceFailed(
            f"task workflow failed: {type(exc).__name__}; "
            f"receipt={receipt.get('status')!r}") from exc
    elapsed = time.monotonic() - started
    receipt = await read_receipt(ctx, f"task-{task_id}")
    problems = receipts.validate(receipt)
    if problems:
        raise AcceptanceFailed(f"receipt validation failed: {problems}")
    state = str(await handle.query(TaskWorkflow.state))
    assertions = task_assertions(receipt, result, state, s)
    assertions.append(assertion("approval_update_returned", True, bool(approval),
                                ok=bool(approval)))
    assertions.append(assertion("workflow_run_id_recorded", True, bool(run_id),
                                ok=bool(run_id)))
    diff_sha, changed, trailers = branch_digest(
        s.origin, task_id, base_sha, result.head_sha, ctx.temp_dir)
    assertions.append(assertion("changed_files", ["app/calc.py"], changed,
                                ok=changed == ["app/calc.py"]))
    assertions.append(assertion("review_diff_sha256_matches_git", True,
                                diff_sha == receipt["entries"]["review"].get("diff_sha256"),
                                ok=diff_sha == receipt["entries"]["review"].get("diff_sha256")))
    assertions.append(assertion("factory_step_trailers", 2, trailers, ok=trailers == 2))
    assertions.append(assertion("receipt_digest_matches_result", True,
                                receipt.get("digest") == result.receipt_digest,
                                ok=receipt.get("digest") == result.receipt_digest))
    prs = await read_prs(ctx)
    branch = gitops.branch_name(task_id)
    matches = [record for record in prs.values()
               if isinstance(record, dict) and record.get("head") == branch]
    assertions.append(assertion("one_pr_record", 1, len(matches), ok=len(matches) == 1))
    if matches:
        assertions.append(assertion("pr_head_sha", result.head_sha,
                                    matches[0].get("head_sha"),
                                    ok=matches[0].get("head_sha") == result.head_sha))
    services_after = {}
    with contextlib.suppress(Exception):
        services_after, _ = await service_snapshot(ctx)
    evidence = {
        "task_id": task_id,
        "workflow_id": f"task-{task_id}",
        "run_id": run_id,
        "base_branch": base_branch,
        "base_sha": base_sha,
        "head_sha": result.head_sha,
        "review": {key: receipt.get("entries", {}).get("review", {}).get(key)
                   for key in ("verdict", "reviewer", "diff_sha256", "prompt_sha256")},
        "approval_by": s.approver,
        "receipt_digest": receipt.get("digest", ""),
        "receipt_entries": sorted(receipt.get("entries", {})),
        "metrics": receipt.get("metrics", {}),
        "pr_count": len(matches),
        "elapsed_seconds": round(elapsed, 2),
        "resource_samples": _resource_samples(services_before, services_after),
    }
    ctx.documents["task"] = evidence
    return assertions, evidence


def _resource_samples(before: dict, after: dict) -> dict:
    names = sorted(set(before) | set(after))
    return {
        name: {
            "rss_mb_before": None if before.get(name, {}).get("rss_kb") is None else round(
                before[name]["rss_kb"] / 1024, 1),
            "rss_mb_after": None if after.get(name, {}).get("rss_kb") is None else round(
                after[name]["rss_kb"] / 1024, 1),
            "cpu_percent_after": after.get(name, {}).get("cpu_percent"),
        }
        for name in names
    }


# ---------------------------------------------------------------------------
# Gate 5: fresh-client readback and provenance
# ---------------------------------------------------------------------------


def find_telemetry(document: dict) -> dict:
    def walk(value: Any) -> dict | None:
        if isinstance(value, dict):
            if "cost_usd" in value or "total_tokens" in value or value.get("schema") == \
                    "agent-factory.opencode-telemetry/1":
                return value
            for item in value.values():
                found = walk(item)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found:
                    return found
        return None
    return walk(document) or {}


async def gate_readback(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    task = ctx.documents.get("task")
    if not task:
        if not s.task_id:
            raise AcceptanceBlocked(
                "run the task gate first, or set FACTORY_ACCEPTANCE_TASK_ID",
                missing=("FACTORY_ACCEPTANCE_TASK_ID",))
        receipt = await read_receipt(ctx, f"task-{s.task_id}")
        pinned = receipt.get("entries", {}).get("pinned", {})
        steps = [value for key, value in receipt.get("entries", {}).items()
                 if key.startswith("step-") and isinstance(value, dict)]
        task = {
            "task_id": s.task_id,
            "workflow_id": f"task-{s.task_id}",
            "base_sha": pinned.get("base_sha", ""),
            "head_sha": steps[-1].get("sha", "") if steps else "",
            "receipt_digest": receipt.get("digest", ""),
            "run_id": "",
        }
    await asyncio.sleep(2)
    client = await ctx.reset_client()
    workflow = client.get_workflow_handle_for(TaskWorkflow.run, task["workflow_id"])
    described = await workflow.describe()
    receipt_one = await read_receipt(ctx, task["workflow_id"])
    first_bytes = json.dumps(receipt_one, sort_keys=True).encode()
    await asyncio.sleep(1)
    receipt_two = await read_receipt(ctx, task["workflow_id"])
    second_bytes = json.dumps(receipt_two, sort_keys=True).encode()
    result = await workflow.result()
    state = str(await workflow.query(TaskWorkflow.state))
    problems = receipts.validate(receipt_two)
    review = receipt_two.get("entries", {}).get("review", {})
    approval = receipt_two.get("entries", {}).get("approval", {})
    expected_entries = {"pinned", "context", "step-0", "step-1", "tests", "evidence",
                        "review", "approval", "pr", "xplan_dry_run"}
    entry_keys = set(receipt_two.get("entries", {}))
    diff_sha = ""
    changed: list[str] = []
    trailers = 0
    if task.get("base_sha") and task.get("head_sha"):
        diff_sha, changed, trailers = branch_digest(
            s.origin, task["task_id"], task["base_sha"], task["head_sha"], ctx.temp_dir)
    prs = await read_prs(ctx)
    branch = gitops.branch_name(task["task_id"])
    matches = [record for record in prs.values()
               if isinstance(record, dict) and record.get("head") == branch]
    receipt_count = await receipt_file_count(ctx, task["workflow_id"])
    telemetry = find_telemetry(receipt_two)
    telemetry_ok = True
    if s.require_telemetry:
        telemetry_ok = bool(telemetry) and telemetry.get("schema") == \
            "agent-factory.opencode-telemetry/1"
    assertions = [
        assertion("temporal_status", "COMPLETED", described.status.name,
                  ok=described.status.name == "COMPLETED"),
        assertion("task_state", "PR_OPEN", state, ok=state == "PR_OPEN"),
        assertion("run_id_unchanged", task.get("run_id", ""), described.run_id,
                  ok=not task.get("run_id") or described.run_id == task["run_id"]),
        assertion("result_status", "PR_OPEN", result.status, ok=result.status == "PR_OPEN"),
        assertion("receipt_validation", [], problems, ok=problems == []),
        assertion("receipt_stable", True, first_bytes == second_bytes,
                  ok=first_bytes == second_bytes),
        assertion("receipt_digest_matches_result", True,
                  receipt_two.get("digest") == result.receipt_digest,
                  ok=receipt_two.get("digest") == result.receipt_digest),
        assertion("receipt_single_file", 1, receipt_count, ok=receipt_count == 1),
        assertion("required_entries", sorted(expected_entries), sorted(entry_keys),
                  ok=expected_entries <= entry_keys),
        assertion("no_failure_entry", False, "failure" in entry_keys,
                  ok="failure" not in entry_keys),
        assertion("review_verdict", "APPROVE", review.get("verdict"),
                  ok=review.get("verdict") == "APPROVE"),
        assertion("approval_by", s.approver, approval.get("by"),
                  ok=approval.get("by") == s.approver),
        assertion("changed_files", ["app/calc.py"], changed,
                  ok=changed == ["app/calc.py"]),
        assertion("review_diff_sha256_matches_git", True,
                  diff_sha == review.get("diff_sha256"),
                  ok=diff_sha == review.get("diff_sha256")),
        assertion("factory_step_trailers", 2, trailers, ok=trailers == 2),
        assertion("one_pr_record", 1, len(matches), ok=len(matches) == 1),
    ]
    if s.require_telemetry:
        assertions.append(assertion(
            "telemetry_present", True, bool(telemetry), ok=telemetry_ok))
    raw = json.dumps([receipt_two, prs], sort_keys=True)
    leaks = [value for value in private_values(s, ctx.env) if value and value in raw]
    assertions.append(assertion("no_private_value_in_receipt", 0, len(leaks),
                                ok=len(leaks) == 0))
    evidence = {
        "task_id": task["task_id"],
        "workflow_id": task["workflow_id"],
        "run_id": described.run_id,
        "temporal_status": described.status.name,
        "state": state,
        "receipt_digest": receipt_two.get("digest", ""),
        "receipt_sha256": hashlib.sha256(second_bytes).hexdigest(),
        "receipt_bytes": len(second_bytes),
        "entry_keys": sorted(entry_keys),
        "pr_count": len(matches),
        "diff_sha256": diff_sha,
        "trailers": trailers,
        "telemetry": {
            "present": bool(telemetry),
            "schema": telemetry.get("schema", ""),
            "fields": sorted(telemetry) if telemetry else [],
        },
        "redacted_private_values": len(leaks),
    }
    ctx.documents["readback"] = evidence
    return assertions, evidence


# ---------------------------------------------------------------------------
# Gate 6: Mac client detachment / remote independence
# ---------------------------------------------------------------------------


async def gate_independence(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    before = await poller_snapshot(ctx, [s.task_queue])
    pre_assertions = poller_assertions(before, s)
    if not all(assertion_result(item) for item in pre_assertions):
        raise AcceptanceFailed("target queue has no independent remote poller")
    base_branch, base_sha, _clone = seed_origin(
        s, ctx.temp_dir, s.run_id, "independence")
    task_id = f"acc-ind-{s.run_id}"
    step0 = ["/bin/sh", "-c",
             "mkdir -p src/a; printf 'independence\\n' > src/a/one.txt"]
    step1 = ["/bin/sh", "-c",
             f"sleep {s.independence_sleep:g}; "
             "printf 'remote\\n' > src/a/two.txt"]
    test = ["/bin/sh", "-c",
            "test \"$(cat src/a/one.txt)\" = independence && "
            "test \"$(cat src/a/two.txt)\" = remote"]
    spec = TaskSpec(
        task_id=task_id, repo=s.origin, agent_steps=[step0, step1], test_command=test,
        owned_paths=["src/a"], task_queue=s.task_queue, base_ref=base_branch,
        reviewer="stub", require_approval=False, max_step_seconds=180,
        max_attempts=2, heartbeat_timeout_seconds=15, test_timeout_seconds=120,
        pr_backend="local")
    client = await ctx.ensure_client()
    handle = await start_task(client, spec)
    described = await handle.describe()
    run_id = described.run_id
    workflow_id = handle.id
    await wait_task_state(ctx, handle,
                          lambda value: value in {"AGENT_STEP_0", "AGENT_STEP_1"}, 120)
    detached_at = datetime.now(timezone.utc)
    del handle
    ctx.drop_client()
    del client
    await asyncio.sleep(s.detach_seconds)
    client = await ctx.ensure_client()
    reconnected = client.get_workflow_handle_for(TaskWorkflow.run, workflow_id)
    reconnect_state = str(await reconnected.query(TaskWorkflow.state))
    result = await asyncio.wait_for(reconnected.result(), timeout=s.timeout_seconds)
    history = await reconnected.fetch_history()
    events_after = 0
    activity_starts_after = 0
    for event in history.events:
        seconds = event.event_time.ToSeconds() if event.HasField("event_time") else 0
        when = datetime.fromtimestamp(seconds, tz=timezone.utc)
        if when > detached_at:
            events_after += 1
            if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED:
                activity_starts_after += 1
    receipt = await read_receipt(ctx, workflow_id)
    after = await poller_snapshot(ctx, [s.task_queue])
    assertions = pre_assertions + [
        assertion("reconnect_state_progressed", True,
                  reconnect_state not in {"PENDING", "UNKNOWN", ""},
                  ok=reconnect_state not in {"PENDING", "UNKNOWN", ""}),
        assertion("result_status", "PR_OPEN", result.status, ok=result.status == "PR_OPEN"),
        assertion("events_after_detach", ">0", events_after, ok=events_after > 0),
        assertion("activity_started_after_detach", ">0", activity_starts_after,
                  ok=activity_starts_after > 0),
        assertion("receipt_status", "PR_OPEN", receipt.get("status"),
                  ok=receipt.get("status") == "PR_OPEN"),
        assertion("receipt_digest", True, bool(receipt.get("digest")),
                  ok=bool(receipt.get("digest"))),
    ] + poller_assertions(after, s)
    evidence = {
        "task_id": task_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "base_sha": base_sha,
        "detached_seconds": s.detach_seconds,
        "reconnect_state": reconnect_state,
        "events_after_detach": events_after,
        "activity_starts_after_detach": activity_starts_after,
        "receipt_digest": receipt.get("digest", ""),
        "local_markers": len(s.local_markers),
        "pollers_before": safe_poller_evidence(before),
        "pollers_after": safe_poller_evidence(after),
    }
    ctx.documents["independence"] = evidence
    return assertions, evidence


# ---------------------------------------------------------------------------
# Gate 7: isolated batch-worker restart + checkpoint reuse
# ---------------------------------------------------------------------------


def _batch_imports() -> tuple[Any, Any]:
    try:
        from agent_factory.batch.models import workflow_id  # noqa: PLC0415
        from agent_factory.batch.workflow import BatchWorkflow  # noqa: PLC0415
    except ImportError as exc:
        raise AcceptanceBlocked(
            "A2 batch module is not present in this checkout") from exc
    return BatchWorkflow, workflow_id


def batch_script(sleep_seconds: float = 45.0) -> str:
    return BATCH_RESTART_SCRIPT.replace("sleep 45", f"sleep {sleep_seconds:g}")


def batch_manifest(workspace: str, job_id: str, task_queue: str,
                   sleep_seconds: float = 45.0) -> dict:
    script = batch_script(sleep_seconds)
    dq = BATCH_RESTART_DQ
    data = {
        "job_id": job_id,
        "runner_id": "bash",
        "workspace": workspace,
        "task_queue": task_queue,
        "script": "unit.sh",
        "script_sha": sha256_text(script),
        "units": [
            {"unit_id": "u0", "outputs": ["out0.txt"],
             "resource_limits": {"timeout_seconds": 60, "cpu_seconds": 60,
                                 "memory_mb": 512, "output_bytes": 100000}},
            {"unit_id": "u1", "outputs": ["out1.txt"],
             "resource_limits": {"timeout_seconds": 180, "cpu_seconds": 180,
                                 "memory_mb": 512, "output_bytes": 100000}},
        ],
        "dq_contract": {
            "script": "dq.sh",
            "script_sha": sha256_text(dq),
            "report_path": "dq.json",
            "expected_json": {"status": "PASS"},
            "timeout_seconds": 60,
            "memory_mb": 256,
        },
    }
    body = {key: value for key, value in data.items() if key != "manifest_hash"}
    data["manifest_hash"] = sha256_text(canonical_json(body))
    return data


async def prepare_batch_fixture(ctx: Context, marker: str, job_id: str) -> tuple[str, str]:
    s = ctx.settings
    root = posixpath.join(s.remote_work_dir, "acceptance", s.run_id, marker)
    workspace = posixpath.join(root, "workspace")
    manifest_path = posixpath.join(root, "manifest.json")
    await ctx.ssh(f"mkdir -p {shlex.quote(workspace)}", timeout=30)
    await ctx.write_remote_text(
        posixpath.join(workspace, "unit.sh"), batch_script(s.restart_sleep))
    await ctx.write_remote_text(posixpath.join(workspace, "dq.sh"), BATCH_RESTART_DQ)
    manifest = batch_manifest(workspace, job_id, s.batch_queue, s.restart_sleep)
    await ctx.write_remote_text(manifest_path, json.dumps(manifest, indent=2))
    remote_script = await ctx.remote_sha256(posixpath.join(workspace, "unit.sh"))
    if remote_script != manifest["script_sha"]:
        raise AcceptanceFailed("remote batch script hash does not match the manifest")
    return manifest_path, workspace


async def submit_batch_remote(ctx: Context, manifest_path: str) -> dict:
    script = (
        f"set -a; . {shlex.quote(ctx.settings.remote_env_file)}; set +a; "
        f"exec {shlex.quote(ctx.settings.remote_python)} -m agent_factory.batch "
        f"submit {shlex.quote(manifest_path)}")
    result = await ctx.ssh(script, timeout=180)
    if result.returncode != 0:
        raise AcceptanceFailed(
            f"batch submit failed ({result.returncode}): "
            f"{redact(result.stderr[-800:], ctx.settings, ctx.env)}")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise AcceptanceFailed("batch submit returned no JSON")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AcceptanceFailed(f"batch submit returned non-JSON: {exc}") from exc
    if not isinstance(payload, dict) or not payload.get("workflow_id"):
        raise AcceptanceFailed(f"batch submit payload is incomplete: {payload}")
    return payload


async def wait_batch_state(ctx: Context, handle: Any, predicate: Callable[[str], bool],
                           timeout: float) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = str(await handle.query("state"))
        if predicate(last):
            return last
        await asyncio.sleep(1)
    raise AcceptanceFailed(f"batch did not reach the expected state; last={last!r}")


def batch_receipt_assertions(receipt: dict, result: Any, state: str,
                             expected_units: int | None = None) -> list[dict]:
    entries = receipt.get("entries", {})
    units = {key: value for key, value in entries.items()
             if key.startswith("unit-") and isinstance(value, dict)}
    if expected_units is None:
        unit_assert = assertion("batch_unit_count", ">=1", len(units), ok=len(units) >= 1)
    else:
        unit_assert = assertion("batch_unit_count", expected_units, len(units),
                                ok=len(units) == expected_units)
    return [
        assertion("batch_state", "BATCH_SUCCESS", state, ok=state == "BATCH_SUCCESS"),
        assertion("batch_result_status", "BATCH_SUCCESS", result.status,
                  ok=result.status == "BATCH_SUCCESS"),
        assertion("batch_receipt_status", "BATCH_SUCCESS", receipt.get("status"),
                  ok=receipt.get("status") == "BATCH_SUCCESS"),
        unit_assert,
        assertion("batch_dq_status", "PASS", entries.get("dq", {}).get("status"),
                  ok=entries.get("dq", {}).get("status") == "PASS"),
        assertion("batch_digest", True, bool(receipt.get("digest")),
                  ok=bool(receipt.get("digest"))),
    ]


async def gate_restart(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    BatchWorkflow, workflow_id = _batch_imports()
    if not s.restart_cmd:
        raise AcceptanceBlocked("restart command is not configured",
                                missing=("FACTORY_ACCEPTANCE_RESTART_CMD",))
    before = await poller_snapshot(ctx, [s.batch_queue])
    if before[s.batch_queue]["workflow"]["count"] < s.min_pollers:
        raise AcceptanceFailed(
            f"{s.batch_queue} has no worker poller before the restart")
    job_id = f"acc-restart-{s.run_id}"
    manifest_path, workspace = await prepare_batch_fixture(ctx, "restart", job_id)
    payload = await submit_batch_remote(ctx, manifest_path)
    client = await ctx.ensure_client()
    handle = client.get_workflow_handle_for(
        BatchWorkflow.run, str(workflow_id(job_id)))
    described = await handle.describe()
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        effects = ""
        with contextlib.suppress(Exception):
            effects = await ctx.read_remote_text(posixpath.join(workspace, "effects.log"))
        slow = await ctx.remote_exists(posixpath.join(workspace, "slow.pid"))
        if effects.splitlines()[:1] == ["u0"] and slow:
            break
        await asyncio.sleep(1)
    else:
        raise AcceptanceFailed("unit u0 did not finish before the restart window")
    restart_result = await ctx.ssh(s.restart_cmd, timeout=120)
    if restart_result.returncode != 0:
        raise AcceptanceFailed(
            f"restart command failed ({restart_result.returncode}): "
            f"{redact(restart_result.stderr[-500:], s, ctx.env)}")
    deadline = time.monotonic() + 180
    after = {}
    while time.monotonic() < deadline:
        with contextlib.suppress(Exception):
            after = await poller_snapshot(ctx, [s.batch_queue])
        before_ids = set(before[s.batch_queue]["workflow"]["identities"])
        after_ids = set(after.get(s.batch_queue, {}).get("workflow", {}).get("identities", []))
        if after and after_ids and after_ids != before_ids:
            break
        await asyncio.sleep(2)
    state = await wait_batch_state(
        ctx, handle, lambda value: value in {"BATCH_SUCCESS", "BATCH_FAILED", "BATCH_CANCELED"},
        s.timeout_seconds)
    result = await asyncio.wait_for(handle.result(), timeout=s.timeout_seconds)
    after_describe = await handle.describe()
    receipt = await read_receipt(ctx, str(workflow_id(job_id)))
    problems = receipts.validate(receipt)
    if problems:
        raise AcceptanceFailed(f"batch receipt validation failed: {problems}")
    entries = receipt.get("entries", {})
    effects = await ctx.read_remote_text(posixpath.join(workspace, "effects.log"))
    receipt_count = await receipt_file_count(ctx, str(workflow_id(job_id)))
    assertions = batch_receipt_assertions(receipt, result, state, expected_units=2)
    assertions.extend(poller_assertions(after, s))
    assertions.extend([
        assertion("unit_u0_preserved", "COMPLETED_OR_REUSED",
                  entries.get("unit-u0", {}).get("status"),
                  ok=entries.get("unit-u0", {}).get("status") in {"COMPLETED", "REUSED"}),
        assertion("unit_u0_checkpoint", True,
                  bool(entries.get("unit-u0", {}).get("checkpoint")),
                  ok=bool(entries.get("unit-u0", {}).get("checkpoint"))),
        assertion("unit_u1_completed", "COMPLETED", entries.get("unit-u1", {}).get("status"),
                  ok=entries.get("unit-u1", {}).get("status") == "COMPLETED"),
        assertion("effects_no_duplicate", ["u0", "u1"], effects.splitlines(),
                  ok=effects.splitlines() == ["u0", "u1"]),
        assertion("restart_changed_poller_identity", True,
                  bool(after) and set(after.get(s.batch_queue, {}).get(
                      "workflow", {}).get("identities", [])) !=
                  set(before[s.batch_queue]["workflow"]["identities"]),
                  ok=bool(after) and set(after.get(s.batch_queue, {}).get(
                      "workflow", {}).get("identities", [])) !=
                  set(before[s.batch_queue]["workflow"]["identities"])),
        assertion("workflow_run_id_recorded", True, bool(described.run_id),
                  ok=bool(described.run_id)),
        assertion("workflow_run_id_unchanged", described.run_id, after_describe.run_id,
                  ok=described.run_id == after_describe.run_id),
        assertion("receipt_single_file", 1, receipt_count,
                  ok=receipt_count == 1),
    ])
    evidence = {
        "job_id": job_id,
        "workflow_id": str(workflow_id(job_id)),
        "run_id": described.run_id,
        "restart_command_sha256": fingerprint(s.restart_cmd),
        "pollers_before": safe_poller_evidence(before),
        "pollers_after": safe_poller_evidence(after),
        "effects": effects.splitlines(),
        "units": {key: value.get("status") for key, value in entries.items()
                  if key.startswith("unit-")},
        "metrics": receipt.get("metrics", {}),
        "dq_status": entries.get("dq", {}).get("status", ""),
        "receipt_digest": receipt.get("digest", ""),
        "receipt_sha256": sha256_text(json.dumps(receipt, sort_keys=True)),
    }
    ctx.documents["restart"] = evidence
    return assertions, evidence


# ---------------------------------------------------------------------------
# Gate 8: real read-only BSC batch through A2
# ---------------------------------------------------------------------------


def bsc_readonly_evidence(report: Mapping[str, Any],
                          expected: Mapping[str, Any]) -> tuple[bool, list[str]]:
    missing = []
    for key, value in expected.items():
        if report.get(key) != value:
            missing.append(key)
    return not missing, missing


async def gate_bsc(ctx: Context) -> tuple[list[dict], dict]:
    s = ctx.settings
    if not s.allow_bsc:
        raise AcceptanceBlocked("BSC batch requires FACTORY_ACCEPTANCE_ALLOW_BSC=1",
                                missing=("FACTORY_ACCEPTANCE_ALLOW_BSC",))
    BatchWorkflow, workflow_id = _batch_imports()
    if not s.bsc_manifest:
        raise AcceptanceBlocked("BSC manifest is not configured",
                                missing=("FACTORY_ACCEPTANCE_BSC_MANIFEST",))
    source_text = await ctx.read_remote_text(s.bsc_manifest)
    try:
        source = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise AcceptanceFailed(f"BSC manifest is not valid JSON: {exc}") from exc
    if not isinstance(source, dict):
        raise AcceptanceFailed("BSC manifest must be a JSON object")
    job_id = str(source.get("job_id") or "")
    if not s.bsc_reuse_job:
        job_id = f"bsc-acc-{s.run_id}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", job_id):
        raise AcceptanceFailed("BSC job id is not path-safe")
    if source.get("task_queue", s.batch_queue) != s.batch_queue:
        raise AcceptanceFailed(
            f"BSC manifest targets {source.get('task_queue')!r}, expected {s.batch_queue!r}")
    source_hash = str(source.get("manifest_hash", ""))
    source_body = {key: value for key, value in source.items() if key != "manifest_hash"}
    if source_hash != sha256_text(canonical_json(source_body)):
        raise AcceptanceFailed("BSC source manifest hash does not match its bytes")
    body = dict(source_body)
    body["job_id"] = job_id
    body["manifest_hash"] = sha256_text(canonical_json(body))
    manifest_dir = posixpath.dirname(s.bsc_manifest) or "."
    temp_manifest = posixpath.join(manifest_dir, f".acceptance-{s.run_id}.json")
    await ctx.write_remote_text(temp_manifest, json.dumps(body, indent=2))
    try:
        payload = await submit_batch_remote(ctx, temp_manifest)
        if payload.get("job_id") != job_id:
            raise AcceptanceFailed("A2 submitted a different job id than requested")
        client = await ctx.ensure_client()
        handle = client.get_workflow_handle_for(
            BatchWorkflow.run, str(workflow_id(job_id)))
        described = await handle.describe()
        state = await wait_batch_state(
            ctx, handle,
            lambda value: value in {"BATCH_SUCCESS", "BATCH_FAILED", "BATCH_CANCELED"},
            s.timeout_seconds)
        result = await asyncio.wait_for(handle.result(), timeout=s.timeout_seconds)
    finally:
        with contextlib.suppress(Exception):
            await ctx.ssh(f"rm -f -- {shlex.quote(temp_manifest)}", timeout=30)
    receipt = await read_receipt(ctx, str(workflow_id(job_id)))
    problems = receipts.validate(receipt)
    if problems:
        raise AcceptanceFailed(f"BSC receipt validation failed: {problems}")
    entries = receipt.get("entries", {})
    units = {key: value for key, value in entries.items()
             if key.startswith("unit-") and isinstance(value, dict)}
    dq = entries.get("dq", {})
    report = dq.get("report") if isinstance(dq.get("report"), dict) else {}
    readonly, missing = bsc_readonly_evidence(report, s.bsc_dq_expected)
    workspace = str(body.get("workspace") or "")
    if not posixpath.isabs(workspace):
        workspace = posixpath.normpath(posixpath.join(manifest_dir, workspace))
    readback = {}
    for unit_key, unit in units.items():
        outputs = unit.get("outputs") if isinstance(unit.get("outputs"), dict) else {}
        readback[unit_key] = {
            path: (await ctx.remote_sha256(posixpath.join(workspace, path))) == digest
            for path, digest in outputs.items()
        }
    dq_report_sha = ""
    if dq.get("report_path"):
        dq_report_sha = await ctx.remote_sha256(
            posixpath.join(workspace, str(dq["report_path"])))
    receipt_count = await receipt_file_count(ctx, str(workflow_id(job_id)))
    assertions = batch_receipt_assertions(receipt, result, state) + [
        assertion("bsc_source_manifest_hash", "sha256", source_hash,
                  ok=bool(SHA256_RE.fullmatch(str(source_hash)))),
        assertion("bsc_job_manifest_hash", body["manifest_hash"], receipt.get(
            "entries", {}).get("manifest", {}).get("manifest_hash"),
                  ok=body["manifest_hash"] == receipt.get("entries", {}).get(
                      "manifest", {}).get("manifest_hash")),
        assertion("bsc_units_present", ">=1", len(units), ok=len(units) >= 1),
        assertion("bsc_units_valid", True,
                  all(value.get("status") in {"COMPLETED", "REUSED"}
                      for value in units.values()),
                  ok=all(value.get("status") in {"COMPLETED", "REUSED"}
                         for value in units.values())),
        assertion("bsc_dq_readonly", True, readonly, ok=readonly),
        assertion("bsc_dq_expected_keys", [], missing, ok=not missing),
        assertion("bsc_dq_report_hash", True,
                  bool(dq_report_sha) and dq_report_sha == dq.get("report_sha256"),
                  ok=bool(dq_report_sha) and dq_report_sha == dq.get("report_sha256")),
        assertion("bsc_outputs_readback", True,
                  all(all(values.values()) for values in readback.values()) and bool(readback),
                  ok=all(all(values.values()) for values in readback.values()) and bool(readback)),
        assertion("bsc_workflow_run_id", True, bool(described.run_id),
                  ok=bool(described.run_id)),
        assertion("bsc_receipt_single_file", 1, receipt_count, ok=receipt_count == 1),
    ]
    evidence = {
        "job_id": job_id,
        "workflow_id": str(workflow_id(job_id)),
        "run_id": described.run_id,
        "source_manifest_sha256": fingerprint(str(source_hash)),
        "job_manifest_hash": body["manifest_hash"],
        "script_sha256": str(receipt.get("entries", {}).get("manifest", {}).get(
            "script_sha", "")),
        "unit_count": len(units),
        "units": {key: value.get("status") for key, value in units.items()},
        "dq": {
            "status": dq.get("status", ""),
            "report_sha256": dq.get("report_sha256", ""),
            "readonly_evidence": readonly,
            "missing_expected_keys": missing,
            "report_fields": {key: report.get(key) for key in s.bsc_dq_expected},
        },
        "outputs_readback": readback,
        "receipt_digest": receipt.get("digest", ""),
        "metrics": receipt.get("metrics", {}),
    }
    ctx.documents["bsc"] = evidence
    return assertions, evidence


GATE_FUNCS: dict[str, Callable[[Context], Awaitable[tuple[list[dict], dict]]]] = {
    "preflight": gate_preflight,
    "services": gate_services,
    "resources": gate_resources,
    "task": gate_task,
    "readback": gate_readback,
    "independence": gate_independence,
    "restart": gate_restart,
    "bsc": gate_bsc,
}


# ---------------------------------------------------------------------------
# Report and CLI
# ---------------------------------------------------------------------------


def check_report_path(path: Path, settings: Settings) -> Path:
    target = path.expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[2]
    if repo_root in target.parents and not settings.allow_repo_report:
        raise AcceptanceFailed(
            "refusing to write acceptance evidence inside the repository; "
            "set FACTORY_ACCEPTANCE_REPORT outside it or "
            "FACTORY_ACCEPTANCE_ALLOW_REPO_REPORT=1")
    return target


def write_report(report: dict, path: Path, settings: Settings) -> Path:
    target = check_report_path(path, settings)
    target.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(target.parent, 0o700)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, target)
    return target


def print_summary(report: dict) -> None:
    for gate in report["gates"]:
        print(f"{gate['gate']:<14} {gate['status']:<8} {gate['duration_seconds']:>7.2f}s"
              + (f"  {gate['error']}" if gate.get("error") else ""))
        for item in gate.get("assertions", []):
            if not item["pass"]:
                print(f"  FAILED {item['name']}: expected={item['expected']!r} "
                      f"actual={item['actual']!r}")
    summary = report["summary"]
    print(f"RESULT {summary['result']}  pass={summary['counts']['PASS']} "
          f"fail={summary['counts']['FAIL']} blocked={summary['counts']['BLOCKED']} "
          f"skip={summary['counts']['SKIP']}")


def plan(names: Iterable[str], env: Mapping[str, str] | None = None) -> dict:
    current = _env(env)
    rows = []
    for name in names:
        spec = GATES[name]
        rows.append({
            "gate": name,
            "summary": spec.summary,
            "destructive": spec.destructive,
            "missing_env": [item for item in spec.required_env if not _value(current, item)],
            "missing_flags": [item for item in spec.required_flags
                              if not _flag(current, item)],
        })
    return {"schema": SCHEMA + "/plan", "gates": rows}


def _selected_gates(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(DEFAULT_GATES) + ["restart"]
    selected = []
    for value in args.gate:
        selected.extend(part.strip() for part in value.split(",") if part.strip())
    return list(dict.fromkeys(selected)) or list(DEFAULT_GATES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="remote-acceptance")
    parser.add_argument("--gate", action="append", default=[],
                        help="gate name or comma list; repeatable")
    parser.add_argument("--all", action="store_true",
                        help="include every gate, including the destructive restart gate")
    parser.add_argument("--list-gates", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the gate plan; no network calls")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--report", default="", help="evidence path override")
    args = parser.parse_args(argv)
    if args.list_gates:
        for name, spec in GATES.items():
            flags = f" flags={','.join(spec.required_flags)}" if spec.required_flags else ""
            print(f"{name:<14} {'destructive ' if spec.destructive else ''}"
                  f"{spec.summary}{flags}")
        return 0
    try:
        settings = settings_from_env(repo_root=Path(__file__).resolve().parents[2])
    except ValueError as exc:
        print(f"invalid acceptance environment: {exc}", file=sys.stderr)
        return 2
    selected = _selected_gates(args)
    unknown = [name for name in selected if name not in GATES]
    if unknown:
        print(f"unknown gates: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if args.report:
        settings = _replace_report(settings, Path(args.report))
    if args.dry_run:
        print(json.dumps(plan(selected), indent=2, sort_keys=True))
        return 0
    if os.environ.get(GLOBAL_FLAG) != "1":
        print(f"{GLOBAL_FLAG}=1 is required for a remote acceptance run", file=sys.stderr)
        return 2
    try:
        check_report_path(settings.report_path, settings)
    except AcceptanceFailed as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = asyncio.run(run_gates(settings, selected))
    try:
        path = write_report(report, settings.report_path, settings)
        report["report_path_sha256"] = fingerprint(str(path))
    except AcceptanceFailed as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_summary(report)
        print(f"evidence {path}")
    return 0 if report["result"] == "PASS" else (1 if report["result"] == "FAIL" else 2)


def _replace_report(settings: Settings, path: Path) -> Settings:
    from dataclasses import replace
    return replace(settings, report_path=path)


if __name__ == "__main__":
    sys.exit(main())
