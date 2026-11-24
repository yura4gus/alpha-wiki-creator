"""Allowlisted batch process execution.

Only three runner ids exist: `python`, `bash` and `rust`.

- python -> `sys.executable <script>`
- bash   -> `/bin/bash <script>`
- rust   -> `<script>` directly (executable file, no shell, no interpreter)

Every command is an argv list. `shell=True` is never used. The process is its
own session, so cancellation and wall-timeout kill the whole process group.

Resource limits are installed by a tiny exec wrapper (`limit_exec.py`): it sets
RLIMIT_CPU, RLIMIT_AS and RLIMIT_FSIZE, then `execv`s the target. This avoids
`preexec_fn` in a threaded worker, which can deadlock. The wrapper disappears at
exec, so the process group id, PID and signal reporting stay the real child's.

The existing `agent_factory.activities.run_command` drives the child and sends
heartbeats; this module adds only the allowlist, limits and failure mapping.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ..activities import run_command
from .models import ResourceLimits

LIMIT_EXEC = Path(__file__).with_name("limit_exec.py")


@dataclass
class RunOutcome:
    exit_code: int
    seconds: float
    log_tail: str


class BatchRunError(RuntimeError):
    """A bounded execution failed. `kind` is stable for receipts and tests."""

    def __init__(self, kind: str, message: str, exit_code: int = -1,
                 log_tail: str = "", seconds: float = 0.0) -> None:
        super().__init__(message)
        self.kind = kind
        self.exit_code = exit_code
        self.log_tail = log_tail
        self.seconds = seconds


def _tail(path: Path, size: int = 2000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[-size:].decode(errors="replace")


def runner_argv(runner_id: str, script: Path, args: list[str]) -> list[str]:
    if runner_id == "python":
        return [sys.executable, str(script), *args]
    if runner_id == "bash":
        bash = "/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash")
        if not bash:
            raise BatchRunError("config", "bash runner is not available on this host")
        return [bash, str(script), *args]
    if runner_id == "rust":
        return [str(script), *args]
    raise BatchRunError("config", f"unknown batch runner {runner_id!r}")


def _with_limits(argv: list[str], limits: ResourceLimits) -> list[str]:
    return [
        sys.executable,
        str(LIMIT_EXEC),
        str(limits.cpu_seconds),
        str(limits.memory_mb * 1024 * 1024),
        str(limits.output_bytes),
        *argv,
    ]


def _signal_name(number: int) -> str:
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"


async def run_limited(argv: list[str], cwd: Path, env: dict[str, str], log_path: Path,
                      limits: ResourceLimits, on_beat) -> RunOutcome:
    """Run one argv under process-group, wall, CPU, memory and output limits."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.unlink(missing_ok=True)
    started = time.monotonic()
    command = _with_limits(argv, limits)
    try:
        code = await asyncio.wait_for(
            run_command(command, cwd, env, log_path, on_beat),
            timeout=limits.timeout_seconds)
    except asyncio.TimeoutError as exc:
        elapsed = time.monotonic() - started
        tail = _tail(log_path)
        raise BatchRunError(
            "timeout", f"unit exceeded {limits.timeout_seconds}s wall limit",
            -1, tail, elapsed) from exc
    except (OSError, ValueError) as exc:
        elapsed = time.monotonic() - started
        raise BatchRunError("launch", f"could not start the unit: {exc}", -1, "",
                            elapsed) from exc

    elapsed = time.monotonic() - started
    tail = _tail(log_path)
    size = log_path.stat().st_size if log_path.exists() else 0
    if code < 0:
        signum = -code
        if signum == signal.SIGXFSZ or (size >= limits.output_bytes and code != 0):
            raise BatchRunError(
                "output", f"output cap {limits.output_bytes} bytes exceeded",
                code, tail, elapsed)
        if signum == signal.SIGXCPU:
            raise BatchRunError(
                "cpu", f"CPU limit {limits.cpu_seconds}s exceeded", code, tail, elapsed)
        raise BatchRunError(
            "signal", f"unit killed by {_signal_name(signum)}", code, tail, elapsed)
    if size > limits.output_bytes:
        raise BatchRunError(
            "output", f"output cap {limits.output_bytes} bytes exceeded", code, tail, elapsed)
    if size >= limits.output_bytes and code != 0:
        raise BatchRunError(
            "output", f"output cap {limits.output_bytes} bytes reached", code, tail, elapsed)
    return RunOutcome(exit_code=code, seconds=elapsed, log_tail=tail)


def ensure_executable(path: Path, where: str) -> None:
    if not path.is_file():
        raise BatchRunError("config", f"{where}: not a file: {path}")
    if not os.access(path, os.X_OK):
        raise BatchRunError("config", f"{where}: file is not executable: {path}")


__all__ = ["BatchRunError", "RunOutcome", "ensure_executable", "run_limited", "runner_argv"]
