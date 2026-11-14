"""Temporal activities. Each is bounded, heartbeating where it blocks, and repeat-safe.

Temporal may run an activity more than once. Side effects therefore use keys
that survive a retry: the checkpoint trailer, the PR head branch and the
receipt entry. Secrets are read from the worker environment, never from
activity arguments (those are stored in workflow history).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

from temporalio import activity
from temporalio.exceptions import ApplicationError

from . import faults, gitops, receipts, reviewer
from .config import Config
from .models import (ContextResult, PRRequest, ReviewRequest, ReviewResult,
                     StepResult, TaskSpec, TestResult)
from .prs import adapter_for

BASE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "USER", "SHELL")


def _env(spec: TaskSpec, cfg: Config, step: int | str, context_file: Path | None = None) -> dict:
    keep = [*BASE_ENV, *spec.env_passthrough]
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update(FACTORY_TASK_ID=spec.task_id, FACTORY_STEP=str(step))
    if context_file is not None:
        env["FACTORY_CONTEXT_FILE"] = str(context_file)
    return env


def _kill_group(proc: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


async def run_command(argv: list[str], cwd: Path, env: dict, log_path: Path,
                      on_beat, interval: float = 1.0) -> int:
    """Run a native CLI to completion, heartbeating; kill its process group on cancel."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=cwd, env=env, stdout=log, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True)
        try:
            on_beat(proc)
            while True:
                try:
                    return await asyncio.wait_for(asyncio.shield(proc.wait()), timeout=interval)
                except asyncio.TimeoutError:
                    on_beat(proc)
        except BaseException:  # cancellation, timeout, worker shutdown
            _kill_group(proc)
            await proc.wait()
            raise


def _tail(path: Path, size: int = 2000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[-size:].decode(errors="replace")


@activity.defn
async def pin_snapshot(spec: TaskSpec) -> str:
    return await asyncio.to_thread(gitops.resolve_base, spec.repo, spec.base_ref)


@activity.defn
async def build_context(spec: TaskSpec, base_sha: str) -> ContextResult:
    """Alpha-Wiki context at the pinned SHA: contract + brief + requested files."""
    cfg = Config.from_env()
    cache = await asyncio.to_thread(gitops.ensure_cache, cfg.work_root, spec.repo)
    sources, parts = [], []
    for path in ["AGENTS.md", "wiki/graph/context_brief.md", *spec.context_files]:
        text = await asyncio.to_thread(gitops.show_file, cache, base_sha, path)
        if text is None:
            continue
        parts.append(f"## {path}\n{text[:6000]}")
        sources.append({"path": path, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    body = f"# Task {spec.task_id}\nOwned paths: {', '.join(spec.owned_paths)}\n\n" + "\n\n".join(parts)
    out = cfg.work_root / spec.task_id / "context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    return ContextResult(text=body, sources=sources)


@activity.defn
async def agent_step(spec: TaskSpec, index: int, checkpoint: str) -> StepResult:
    """Run one agent CLI step and end it as one pushed checkpoint commit."""
    cfg = Config.from_env()
    started = time.monotonic()
    cache = await asyncio.to_thread(gitops.ensure_cache, cfg.work_root, spec.repo)
    confirmed = await asyncio.to_thread(gitops.find_confirmed_step, cache, spec.task_id, index, checkpoint)
    if confirmed:  # an earlier attempt already pushed this step: do not run the agent again
        return StepResult(index, confirmed, True, True, 0, "", time.monotonic() - started)

    wt = await asyncio.to_thread(gitops.ensure_worktree, cfg.work_root, spec.repo, spec.task_id, checkpoint)
    activity.heartbeat({"step": index, "phase": "ready"})
    context_file = cfg.work_root / spec.task_id / "context.md"
    beats = {"n": 0}

    def on_beat(proc):
        beats["n"] += 1
        activity.heartbeat({"step": index, "pid": proc.pid, "beat": beats["n"]})
        if beats["n"] == 1 and faults.hit(cfg.state_dir, "mid_step", index) == "crash":
            _kill_group(proc)
            os._exit(137)  # simulate a worker killed mid-step

    log = cfg.work_root / spec.task_id / "logs" / f"step-{index}.log"
    code = await run_command(spec.agent_steps[index], wt, _env(spec, cfg, index, context_file), log, on_beat)
    if code != 0:
        raise ApplicationError(f"agent step {index} exited {code}: {_tail(log)}", type="AgentFailed")
    try:
        sha, changed = await asyncio.to_thread(
            gitops.commit_and_push, wt, spec.task_id, index, checkpoint, spec.owned_paths)
    except gitops.OwnershipViolation as exc:
        raise ApplicationError(str(exc), type="OwnershipViolation", non_retryable=True)
    if faults.hit(cfg.state_dir, "after_push", index) == "error":
        raise RuntimeError("injected failure after push")  # retry must not duplicate the commit
    return StepResult(index, sha, changed, False, code, _tail(log), time.monotonic() - started)


@activity.defn
async def run_tests(spec: TaskSpec, sha: str) -> TestResult:
    cfg = Config.from_env()
    started = time.monotonic()
    wt = await asyncio.to_thread(gitops.ensure_worktree, cfg.work_root, spec.repo, spec.task_id, sha)
    log = cfg.work_root / spec.task_id / "logs" / "tests.log"
    log.unlink(missing_ok=True)
    code = await asyncio.wait_for(
        run_command(spec.test_command, wt, _env(spec, cfg, "tests"), log,
                    lambda proc: activity.heartbeat({"phase": "tests", "pid": proc.pid})),
        timeout=spec.test_timeout_seconds)
    return TestResult(code == 0, code, _tail(log), time.monotonic() - started)


@activity.defn
async def review(spec: TaskSpec, req: ReviewRequest) -> ReviewResult:
    cfg = Config.from_env()
    cache = await asyncio.to_thread(gitops.ensure_cache, cfg.work_root, spec.repo)
    diff = await asyncio.to_thread(gitops.diff_text, cache, req.base_sha, req.head_sha)
    if spec.reviewer == "opencode":
        result = await asyncio.to_thread(
            reviewer.opencode_review, spec.review_model, req.context_text,
            f"passed={req.tests_passed}\n{req.tests_tail}", diff, req.head_sha)
    elif spec.reviewer == "stub":
        result = reviewer.stub_review(spec.owned_paths, diff, req.tests_passed, req.head_sha)
    else:
        raise ApplicationError(f"unknown reviewer {spec.reviewer!r}", non_retryable=True)
    return ReviewResult(**result)


@activity.defn
async def open_pr(spec: TaskSpec, req: PRRequest) -> dict:
    cfg = Config.from_env()
    adapter = adapter_for(spec.pr_backend, cfg.state_dir, spec.pr_repo)
    title = spec.pr_title or f"factory: {spec.task_id}"
    record = await asyncio.to_thread(
        adapter.ensure_pr, spec.repo, gitops.branch_name(spec.task_id), spec.base_ref,
        title, req.review_summary, req.head_sha)
    if faults.hit(cfg.state_dir, "after_pr") == "error":
        raise RuntimeError("injected failure after PR creation")  # retry must reuse the PR
    return record


@activity.defn
async def reconcile_dry_run(spec: TaskSpec, kind: str, git_sha: str, evidence: list[str],
                            findings: str) -> dict:
    """Propose an xPlan transition. Pure and read-only: nothing is written to xPlan."""
    if not spec.xplan:
        return {"decision": "SKIPPED", "reason": "no xPlan binding supplied", "mode": "dry_run"}
    root = spec.plugin_root or os.environ.get("FACTORY_PLUGIN_ROOT")
    if not root:
        return {"decision": "SKIPPED", "reason": "plugin_root not set", "mode": "dry_run"}
    event = {"kind": kind, "git_sha": git_sha, "evidence_refs": evidence}
    if kind == "rework":
        event["review"] = {"git_sha": git_sha, "findings": findings}
    payload = json.dumps({"binding": spec.xplan["binding"], "observed": spec.xplan["observed"],
                          "event": event})
    # Run the project's own tool through its launcher: the plugin keeps its dependencies
    # in .alpha-wiki/runtime, outside this package's environment.
    cfg = Config.from_env()
    inp = cfg.work_root / spec.task_id / "xplan-input.json"
    inp.parent.mkdir(parents=True, exist_ok=True)
    inp.write_text(payload)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(Path(root) / ".alpha-wiki" / "run.py"), "-m", "tools.xplan_dry_run", str(inp),
        cwd=root, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
    if proc.returncode != 0:
        return {"decision": "INVALID", "reason": err.decode(errors="replace").strip()[-300:],
                "mode": "dry_run"}
    return json.loads(out)


@activity.defn
async def record_step(key: str, data_json: str, metrics_json: str) -> str:
    """Write one receipt entry; repeating it with the same data is a no-op."""
    cfg = Config.from_env()
    info = activity.info()
    task_id = info.workflow_id.removeprefix("task-")
    return await asyncio.to_thread(
        receipts.record, cfg.state_dir, info.workflow_id, task_id, key, json.loads(data_json),
        json.loads(metrics_json) if metrics_json else None)


@activity.defn
async def finalize_receipt(status: str) -> dict:
    cfg = Config.from_env()
    info = activity.info()
    task_id = info.workflow_id.removeprefix("task-")
    doc = await asyncio.to_thread(receipts.finalize, cfg.state_dir, info.workflow_id, task_id, status)
    return {"path": str(receipts.receipt_path(cfg.state_dir, info.workflow_id)),
            "digest": doc["digest"], "status": doc["status"]}


@activity.defn
async def cleanup_worktree(spec: TaskSpec) -> bool:
    cfg = Config.from_env()
    return await asyncio.to_thread(gitops.remove_worktree, cfg.work_root, spec.repo, spec.task_id)


ALL = [pin_snapshot, build_context, agent_step, run_tests, review, open_pr,
       reconcile_dry_run, record_step, finalize_receipt, cleanup_worktree]
