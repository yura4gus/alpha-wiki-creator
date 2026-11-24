"""End-to-end evidence for the real OpenCode CLI worker through Temporal.

These tests are opt-in: they spend real model calls and need `opencode` on PATH.

    FACTORY_LIVE_CLI=1 .venv/bin/python -m pytest tests/test_live_cli.py -q

The four lifecycle tests build their own throwaway git repositories under
`tmp_path`; the concurrent-isolation test uses the shared `origin` fixture with
unique task ids. The product code is not stubbed: `opencode run --auto` edits a
worktree, the existing activity commits and pushes one checkpoint per step, and
the existing workflow runs tests, review, PR and receipt.

Only the success test uses a live reviewer. The recovery, cancellation, reuse
and isolation tests use the rule-based stub reviewer so their evidence is about
the CLI lifecycle, not about another model.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.worker import Replayer

from agent_factory import gitops, receipts
from agent_factory.client import start_task
from agent_factory.models import TaskSpec
from agent_factory.workflows import TaskWorkflow
from conftest import make_spec, remote_log, sh, worker

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(not os.environ.get("FACTORY_LIVE_CLI"),
                       reason="live OpenCode CLI calls; set FACTORY_LIVE_CLI=1"),
]

MODEL = os.environ.get("FACTORY_CLI_MODEL", "opencode-go/deepseek-v4.1-flash")
OPENCODE = os.environ.get("FACTORY_OPENCODE_BIN", shutil.which("opencode") or "opencode")
SRC = str(Path(__file__).resolve().parents[1] / "src")
TEST_COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"]

CALC_BUG = """def add(a, b):
    return a - b
"""

TEST_ADD = """import unittest

from app.calc import add


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
"""

TEST_FULL = """import unittest

from app.calc import add, mul


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_mul(self):
        self.assertEqual(mul(2, 3), 6)


if __name__ == "__main__":
    unittest.main()
"""

# The prompts are part of the contract under test: they constrain the real
# model to `app/`, forbid git/tests changes, and split the task into two steps
# so the checkpoint sequence is observable.
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

PROMPT_SLEEP = (
    "Use the bash tool to run exactly this command and wait for it to finish: "
    "sleep 120. Do not edit any files. Do not run any git commands. "
    "Reply only after the command exits."
)


def live_id(prefix: str) -> str:
    return f"live-{prefix}-{uuid.uuid4().hex[:8]}"


def make_origin(tmp_path: Path, *, full: bool) -> str:
    """A bare origin whose main branch has a tiny, genuinely failing Python project."""
    seed = tmp_path / "seed"
    seed.mkdir()
    sh("git", "init", "-q", "-b", "main", cwd=seed)
    sh("git", "config", "user.email", "t@t", cwd=seed)
    sh("git", "config", "user.name", "t", cwd=seed)
    files = {
        "AGENTS.md": "# contract\n\nOnly change files under app/.\n",
        "wiki/graph/context_brief.md": "# brief\n\nA tiny calculator package.\n",
        ".gitignore": "__pycache__/\n*.pyc\n.opencode/\n.DS_Store\n",
        "app/__init__.py": "",
        "app/calc.py": CALC_BUG,
        "tests/test_calc.py": TEST_FULL if full else TEST_ADD,
    }
    for rel, text in files.items():
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text(text)
    sh("git", "add", "-A", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed a failing calculator", cwd=seed)
    bare = tmp_path / "origin.git"
    sh("git", "clone", "-q", "--bare", str(seed), str(bare))
    return str(bare)


def cli_step(prompt: str, binary: str = OPENCODE) -> list[str]:
    # `--auto` is required: without it the CLI may wait for a permission prompt
    # no test can answer. The step argv is stored verbatim in the workflow spec.
    return [binary, "run", "--auto", "-m", MODEL, prompt]


def counting_opencode(tmp_path: Path) -> tuple[str, Path]:
    """Wrap the real CLI, count invocations, then exec it unchanged."""
    log = tmp_path / "opencode-calls.log"
    wrapper = tmp_path / "opencode-counting"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"printf 'call\\n' >> {shlex.quote(str(log))}\n"
        f"exec {shlex.quote(OPENCODE)} \"$@\"\n"
    )
    wrapper.chmod(0o755)
    return str(wrapper), log


def load_receipt(state: Path, task_id: str) -> dict:
    return json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())


def prs(state: Path) -> dict:
    path = state / "prs.json"
    return json.loads(path.read_text()) if path.exists() else {}


def step_commits(origin: str, task_id: str, index: int) -> int:
    return remote_log(origin, f"factory/{task_id}").count(f"Factory-Step: {task_id}/{index}")


def write_fixture_spec(repo: str, queue: str, task_id: str, steps: list[list[str]], **kw) -> TaskSpec:
    base = dict(
        task_id=task_id, repo=repo, agent_steps=steps, test_command=TEST_COMMAND,
        owned_paths=["app"], task_queue=queue, require_approval=False,
        max_step_seconds=240, max_attempts=2, heartbeat_timeout_seconds=10,
        test_timeout_seconds=120,
    )
    base.update(kw)
    return TaskSpec(**base)


async def test_live_cli_success_edits_tests_commits_review(env, dirs, queue, tmp_path):
    work, state = dirs
    origin = make_origin(tmp_path, full=True)
    task_id = live_id("ok")
    branch = f"factory/{task_id}"

    # Prove the seeded repository really fails before the factory touches it.
    base_check = tmp_path / "base-check"
    sh("git", "clone", "-q", origin, str(base_check))
    failed = subprocess.run(TEST_COMMAND, cwd=base_check, capture_output=True, text=True)
    assert failed.returncode != 0, "base project must fail before the agent edits it"

    spec = write_fixture_spec(
        origin, queue, task_id,
        [cli_step(PROMPT_FIX_ADD), cli_step(PROMPT_ADD_MUL)],
        reviewer="opencode", review_model=MODEL,
    )
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()

    assert result.review is not None, f"workflow {result.status}: {result.error}"
    verdict = result.review["verdict"]
    assert verdict in {"APPROVE", "CHANGES"}, result.review
    expected_status = {"APPROVE": "PR_OPEN", "CHANGES": "CHANGES_REQUESTED"}[verdict]
    assert result.status == expected_status, result

    # The pushed branch contains the fixes; the unchanged tests pass there.
    checkout = tmp_path / "verify"
    sh("git", "clone", "-q", origin, str(checkout))
    sh("git", "checkout", "-q", "-b", "verify", f"origin/{branch}", cwd=checkout)
    calc = (checkout / "app" / "calc.py").read_text()
    assert "def add(" in calc and "def mul(" in calc
    passed = subprocess.run(TEST_COMMAND, cwd=checkout, capture_output=True, text=True)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    changed = sh("git", "diff", "--name-only", "main", "verify", cwd=checkout).splitlines()
    assert changed == ["app/calc.py"], "agent stayed inside app/ and did not touch tests"

    # Two durable checkpoints, each exactly once.
    for index in (0, 1):
        assert step_commits(origin, task_id, index) == 1
    assert remote_log(origin, branch).count("Factory-Step:") == 2

    doc = load_receipt(state, task_id)
    assert doc["status"] == result.status
    assert receipts.validate(doc) == [], receipts.validate(doc)
    assert doc["digest"] == result.receipt_digest
    assert doc["entries"]["tests"]["passed"] is True
    review_entry = doc["entries"]["review"]
    assert review_entry["verdict"] == verdict
    assert review_entry["reviewer"] == f"opencode:{MODEL}"
    assert review_entry["head_sha"] == result.head_sha
    assert len(review_entry["diff_sha256"]) == 64
    assert len(review_entry["prompt_sha256"]) == 64
    assert review_entry["diff_sha256"] == result.review["diff_sha256"]
    assert review_entry["prompt_sha256"] == result.review["prompt_sha256"]
    # Provenance is real: recompute the reviewed diff from the pushed commits.
    cache = gitops.ensure_cache(work, origin)
    reviewed_diff = gitops.diff_text(cache, result.base_sha, result.head_sha)
    assert review_entry["diff_sha256"] == hashlib.sha256(reviewed_diff.encode()).hexdigest()

    if verdict == "APPROVE":
        assert result.status == "PR_OPEN"
        assert result.pr["head"] == branch
        assert result.pr["head_sha"] == result.head_sha
        assert len(prs(state)) == 1
        assert list(prs(state).values())[0]["head_sha"] == result.head_sha
    else:
        assert prs(state) == {}
    assert not (work / task_id / "wt").exists()


async def test_live_cli_crash_recovers_from_checkpoint(env, dirs, queue, tmp_path):
    _, state = dirs
    origin = make_origin(tmp_path, full=True)
    task_id = live_id("crash")
    branch = f"factory/{task_id}"
    work1, work2 = tmp_path / "work1", tmp_path / "work2"
    address = env.client.service_client.config.target_host

    def spawn(work_root: Path, faults: str = "") -> subprocess.Popen:
        child_env = {
            **os.environ,
            "PYTHONPATH": SRC,
            "FACTORY_TEMPORAL_ADDRESS": address,
            "FACTORY_TASK_QUEUE": queue,
            "FACTORY_WORK_ROOT": str(work_root),
            "FACTORY_STATE_DIR": str(state),
            "FACTORY_FAULTS": faults,
        }
        return subprocess.Popen([sys.executable, "-m", "agent_factory.worker"], env=child_env)

    spec = write_fixture_spec(
        origin, queue, task_id,
        [cli_step(PROMPT_FIX_ADD), cli_step(PROMPT_ADD_MUL)],
        max_attempts=3,
    )
    w1 = spawn(work1, "mid_step@1=crash")
    handle = await start_task(env.client, spec)
    deadline = time.monotonic() + 180
    while w1.poll() is None and time.monotonic() < deadline:
        await asyncio.sleep(0.2)
    if w1.poll() is None:
        w1.kill()
        w1.wait()
    assert w1.returncode == 137, "worker was killed during agent step 1"
    # Step 0 is the remote tip: the mid-step crash could not have committed step 1.
    step0 = sh("git", "rev-parse", f"refs/heads/{branch}", cwd=origin)
    assert f"Factory-Step: {task_id}/0" in remote_log(origin, branch)

    shutil.rmtree(work1)  # the crashed worker's filesystem is gone
    w2 = spawn(work2)
    try:
        result = await asyncio.wait_for(handle.result(), 300)
    finally:
        w2.kill()
        w2.wait()

    assert result.status == "PR_OPEN", result
    assert result.review["verdict"] == "APPROVE"
    log = remote_log(origin, branch)
    assert step0 in log, "step 0 commit survived on origin"
    assert step_commits(origin, task_id, 0) == 1, "step 0 was not redone"
    assert step_commits(origin, task_id, 1) == 1
    assert log.count("Factory-Step:") == 2
    assert len(prs(state)) == 1
    doc = load_receipt(state, task_id)
    assert doc["status"] == "PR_OPEN"
    assert receipts.validate(doc) == []
    assert doc["entries"]["step-0"]["sha"] == step0
    await Replayer(workflows=[TaskWorkflow]).replay_workflow(await handle.fetch_history())


async def test_live_cli_cancel_kills_process(env, dirs, queue, tmp_path):
    work, state = dirs
    origin = make_origin(tmp_path, full=False)
    task_id = live_id("cancel")
    spec = write_fixture_spec(
        origin, queue, task_id, [cli_step(PROMPT_SLEEP)],
        max_attempts=1,
    )
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        log = work / task_id / "logs" / "step-0.log"
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if await handle.query(TaskWorkflow.state) == "AGENT_STEP_0" and log.exists():
                break
            await asyncio.sleep(0.2)
        assert await handle.query(TaskWorkflow.state) == "AGENT_STEP_0"
        assert log.exists(), "the real CLI step started"
        await asyncio.sleep(2)  # let opencode launch its bash sleep before cancellation
        await handle.cancel()
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), 60)

    assert (await handle.describe()).status.name == "CANCELED"
    doc = load_receipt(state, task_id)
    assert doc["status"] == "CANCELED"
    assert receipts.validate(doc) == []
    assert prs(state) == {}
    assert not (work / task_id / "wt").exists()


async def test_live_cli_three_concurrent_tasks_stay_isolated(env, origin, dirs, queue):
    """Three real CLI tasks share one origin but no worktree, file, commit or PR."""
    _, state = dirs
    from agent_factory.client import start_batch

    prompts = [f"Create a file named src/{x}/one.txt containing exactly: {x}. "
               f"Only modify files under src/{x}/. Do not run git commands." for x in "abc"]
    specs = [make_spec(origin, queue, live_id(f"par-{x}"), f"src/{x}",
                       [cli_step(prompt)], max_step_seconds=240) for x, prompt in zip("abc", prompts)]
    began = time.monotonic()
    async with worker(env, queue):
        results = [await handle.result() for handle in await start_batch(env.client, specs)]
    elapsed = time.monotonic() - began

    assert [r.status for r in results] == ["PR_OPEN"] * 3, results
    assert elapsed < 90, f"three tasks ran concurrently, not serially: {elapsed:.1f}s"
    for spec in specs:
        branch = f"factory/{spec.task_id}"
        changed = sh("git", "diff", "--name-only", "main", branch, cwd=origin).splitlines()
        assert changed == [f"{spec.owned_paths[0]}/one.txt"], (spec.task_id, changed)
        assert step_commits(origin, spec.task_id, 0) == 1
    assert len(prs(state)) == 3
    assert len({p["number"] for p in prs(state).values()}) == 3
    assert len({p["head"] for p in prs(state).values()}) == 3
    assert all(receipts.validate(load_receipt(state, s.task_id)) == [] for s in specs)


async def test_live_cli_step_reuses_pushed_commit(env, dirs, queue, tmp_path, monkeypatch):
    _, state = dirs
    origin = make_origin(tmp_path, full=False)
    task_id = live_id("reuse")
    wrapper, calls = counting_opencode(tmp_path)
    spec = write_fixture_spec(
        origin, queue, task_id, [cli_step(PROMPT_FIX_ADD, binary=wrapper)],
        max_attempts=2,
    )
    # `after_push` is deterministic: it fires only after commit_and_push returned,
    # so the retry must discover the pushed Factory-Step instead of calling the
    # model again. No sleep/race is involved; the call counter proves it.
    monkeypatch.setenv("FACTORY_FAULTS", "after_push@0=error")
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()

    assert result.status == "PR_OPEN", result
    assert result.review["verdict"] == "APPROVE"
    assert step_commits(origin, task_id, 0) == 1, "one Factory-Step trailer"
    assert len(calls.read_text().splitlines()) == 1, "the model ran exactly once"
    doc = load_receipt(state, task_id)
    assert receipts.validate(doc) == []
    assert doc["metrics"]["step-0"]["reused"] is True
    assert doc["entries"]["step-0"]["changed"] is True
    assert len(prs(state)) == 1
    assert list(prs(state).values())[0]["head_sha"] == result.head_sha
