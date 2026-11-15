import asyncio
import json
import os
import time

import pytest
from temporalio.client import WorkflowFailureError, WorkflowUpdateFailedError
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Replayer

from agent_factory import receipts
from agent_factory.client import decide, start_batch, start_task
from agent_factory.workflows import TaskWorkflow
from conftest import PLUGIN_ROOT, agent, file_exists, make_spec, remote_log, sh, worker

pytestmark = pytest.mark.asyncio(loop_scope="module")

XPLAN = {
    "binding": {"issue": {"id": 47, "identifier": "H2REC-3", "updatedAt": "r1", "columnId": 13},
                "run_id": "factory-test", "columns": {"IN_PROGRESS": 13, "DONE": 14},
                "required_delivery_level": 3, "worker": "factory"},
    "observed": {"id": 47, "identifier": "H2REC-3", "updatedAt": "r1", "columnId": 13},
}


def receipt(state, task_id):
    return json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())


def prs(state):
    path = state / "prs.json"
    return json.loads(path.read_text()) if path.exists() else {}


def step_commits(origin, branch, task_id, index):
    return remote_log(origin, branch).count(f"Factory-Step: {task_id}/{index}")


async def test_success_task_to_pr(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "ok", "src/a",
                     [agent("write", "src/a/one.txt", "1"), agent("write", "src/a/two.txt", "2")],
                     xplan=XPLAN, plugin_root=PLUGIN_ROOT)
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "PR_OPEN"
    assert result.review["verdict"] == "APPROVE" and result.review["reviewer"] == "stub-rule-based"
    doc = receipt(state, "ok")
    assert receipts.validate(doc) == [] and doc["digest"] == result.receipt_digest
    assert {"pinned", "context", "step-0", "step-1", "tests", "evidence", "review", "pr",
            "xplan_dry_run"} <= set(doc["entries"])
    assert {s["path"] for s in doc["entries"]["context"]["sources"]} == {
        "AGENTS.md", "wiki/graph/context_brief.md"}
    assert doc["entries"]["evidence"]["status"] == "MISSING"
    assert doc["entries"]["xplan_dry_run"]["mode"] == "dry_run"
    assert doc["entries"]["xplan_dry_run"]["decision"] == "NO_CHANGE"  # delivery gate not met
    assert step_commits(origin, "factory/ok", "ok", 0) == 1 and step_commits(origin, "factory/ok", "ok", 1) == 1
    assert len(prs(state)) == 1
    assert not (dirs[0] / "ok" / "wt").exists()  # worktree cleaned; work lives on the pushed branch


async def test_external_evidence_receipts_are_read_and_recorded(env, origin, dirs, queue, tmp_path):
    _, state = dirs
    h2, ofk = tmp_path / "h2.json", tmp_path / "ofk.json"
    h2.write_text(json.dumps({"profile": "alpha-wiki", "executor": "deterministic",
                              "result": "PASS", "cases": {"train": {"candidate_pass": True}}}))
    ofk.write_text(json.dumps({"kind": "repo-observed", "result": "PASS",
                               "source": {"sha": "a" * 40}, "model_sha256": "b" * 64,
                               "tool": "openflowkit 0.3.0"}))
    spec = make_spec(origin, queue, "ev", "src/a", [agent("write", "src/a/one.txt", "1")],
                     harness2_evaluation=str(h2), openflowkit_report=str(ofk))
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "PR_OPEN"
    entry = receipt(state, "ev")["entries"]["evidence"]
    assert entry["status"] == "PASS" and len(entry["sources"]) == 2
    assert {s["kind"] for s in entry["sources"]} == {"harness2", "openflowkit"}
    assert all(len(s["sha256"]) == 64 for s in entry["sources"])


async def test_approval_pauses_without_worker_and_resumes(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "appr", "src/a", [agent("write", "src/a/one.txt", "1")],
                     require_approval=True)
    handle = None
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        for _ in range(100):
            if await handle.query(TaskWorkflow.state) == "AWAITING_APPROVAL":
                break
            await asyncio.sleep(0.2)
        assert await handle.query(TaskWorkflow.state) == "AWAITING_APPROVAL"
        with pytest.raises(WorkflowUpdateFailedError):
            await decide(env.client, "appr", "maybe", "owner")
        with pytest.raises(WorkflowUpdateFailedError):
            await decide(env.client, "appr", "approve", "")
    assert prs(state) == {}  # nothing external happens before approval
    # the worker is gone: the workflow keeps waiting with no process and no activity running
    await asyncio.sleep(1)
    described = await handle.describe()
    assert described.status.name == "RUNNING"
    assert len(described.raw_description.pending_activities) == 0  # no CLI process, no activity held
    async with worker(env, queue):  # a different worker picks the workflow up
        await decide(env.client, "appr", "approve", "owner", "ship it")
        result = await handle.result()
    assert result.status == "PR_OPEN" and len(prs(state)) == 1
    assert receipt(state, "appr")["entries"]["approval"] == {"verdict": "approve", "by": "owner", "note": "ship it"}


async def test_rejection_opens_no_pr(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "rej", "src/a", [agent("write", "src/a/one.txt", "1")])
    spec.require_approval = True
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        for _ in range(100):
            if await handle.query(TaskWorkflow.state) == "AWAITING_APPROVAL":
                break
            await asyncio.sleep(0.2)
        await decide(env.client, "rej", "reject", "owner", "not now")
        result = await handle.result()
    assert result.status == "REJECTED" and prs(state) == {}


async def test_replay_has_no_duplicate_side_effects(env, origin, dirs, queue, monkeypatch):
    _, state = dirs
    monkeypatch.setenv("FACTORY_FAULTS", "after_push@0=error,after_pr=error")
    spec = make_spec(origin, queue, "rp", "src/a",
                     [agent("write", "src/a/one.txt", "1"), agent("write", "src/a/two.txt", "2")])
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        result = await handle.result()
        with pytest.raises(WorkflowAlreadyStartedError):  # same task id cannot start twice
            await start_task(env.client, spec)
    assert (state / "faults" / "after_push-0").exists() and (state / "faults" / "after_pr-None").exists()
    assert result.status == "PR_OPEN"
    assert step_commits(origin, "factory/rp", "rp", 0) == 1  # retried step reused its pushed commit
    assert step_commits(origin, "factory/rp", "rp", 1) == 1
    assert len(prs(state)) == 1 and list(prs(state).values())[0]["number"] == 1
    assert receipt(state, "rp")["metrics"]["step-0"]["reused"] is True
    # deterministic replay of the recorded history
    await Replayer(workflows=[TaskWorkflow]).replay_workflow(await handle.fetch_history())


async def test_crash_recovers_from_pushed_checkpoint(env, origin, dirs, queue, tmp_path, monkeypatch):
    work, state = dirs
    import subprocess, sys
    src = os.path.join(PLUGIN_ROOT, "factory", "src")
    address = env.client.service_client.config.target_host

    def spawn(work_root, faults=""):
        e = {**os.environ, "PYTHONPATH": src, "FACTORY_TEMPORAL_ADDRESS": address,
             "FACTORY_TASK_QUEUE": queue, "FACTORY_WORK_ROOT": str(work_root),
             "FACTORY_STATE_DIR": str(state), "FACTORY_FAULTS": faults}
        return subprocess.Popen([sys.executable, "-m", "agent_factory.worker"], env=e)

    spec = make_spec(origin, queue, "crash", "src/a",
                     [agent("write", "src/a/one.txt", "1"), agent("write", "src/a/two.txt", "2")],
                     max_attempts=3, heartbeat_timeout_seconds=3)
    w1 = spawn(tmp_path / "work1", "mid_step@1=crash")
    handle = await start_task(env.client, spec)
    deadline = time.time() + 60
    while w1.poll() is None and time.time() < deadline:
        await asyncio.sleep(0.2)
    assert w1.returncode == 137, "worker should have been killed mid step 1"
    step0 = sh("git", "rev-parse", "factory/crash", cwd=origin)  # confirmed progress survives
    import shutil
    shutil.rmtree(tmp_path / "work1")  # the worker's filesystem is gone
    w2 = spawn(tmp_path / "work2")
    try:
        result = await asyncio.wait_for(handle.result(), 90)
    finally:
        w2.kill()
        w2.wait()
    assert result.status == "PR_OPEN"
    log = remote_log(origin, "factory/crash")
    assert step0 in log, "step 0 commit was preserved, not redone"
    assert step_commits(origin, "factory/crash", "crash", 0) == 1
    assert step_commits(origin, "factory/crash", "crash", 1) == 1
    assert len(prs(state)) == 1
    assert receipt(state, "crash")["entries"]["step-0"]["sha"] == step0
    await Replayer(workflows=[TaskWorkflow]).replay_workflow(await handle.fetch_history())


async def test_three_concurrent_tasks_with_disjoint_ownership(env, origin, dirs, queue):
    _, state = dirs
    specs = [make_spec(origin, queue, f"par-{x}", f"src/{x}",
                       [agent("slow-write", f"src/{x}/one.txt", x, "1.5"),
                        agent("slow-write", f"src/{x}/two.txt", x, "1.5")]) for x in "abc"]
    async with worker(env, queue):
        began = time.monotonic()
        handles = await start_batch(env.client, specs)
        results = [await h.result() for h in handles]
        elapsed = time.monotonic() - began
    assert [r.status for r in results] == ["PR_OPEN"] * 3
    assert elapsed < 3 * 2 * 1.5, "tasks ran concurrently, not one after another"
    for x in "abc":
        changed = sh("git", "diff", "--name-only", "main", f"factory/par-{x}", cwd=origin).split()
        assert changed == [f"src/{x}/one.txt", f"src/{x}/two.txt"]
    assert len(prs(state)) == 3
    bad = [make_spec(origin, queue, "x1", "src/a", [agent("noop")]),
           make_spec(origin, queue, "x2", "src/a", [agent("noop")])]
    with pytest.raises(ValueError, match="overlap"):
        await start_batch(env.client, bad)


async def test_cancel_kills_agent_and_finalizes(env, origin, dirs, queue, tmp_path):
    work, state = dirs
    pidfile = tmp_path / "agent.pid"
    spec = make_spec(origin, queue, "cx", "src/a", [agent("sleep", "120", str(pidfile))])
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        for _ in range(100):
            if pidfile.exists():
                break
            await asyncio.sleep(0.2)
        pid = int(pidfile.read_text())
        await handle.cancel()
        with pytest.raises(WorkflowFailureError):
            await handle.result()
    time.sleep(0.5)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    doc = receipt(state, "cx")
    assert doc["status"] == "CANCELED" and receipts.validate(doc) == []
    assert not (work / "cx" / "wt").exists() and prs(state) == {}


async def test_budget_bounds_a_runaway_agent(env, origin, dirs, queue, tmp_path):
    _, state = dirs
    pidfile = tmp_path / "slow.pid"
    spec = make_spec(origin, queue, "bud", "src/a", [agent("sleep", "120", str(pidfile))],
                     max_step_seconds=2, max_attempts=2)
    began = time.monotonic()
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "FAILED" and "TIMEOUT" in result.error.upper()
    assert time.monotonic() - began < 40
    time.sleep(1)
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)
    assert prs(state) == {}


async def test_ownership_violation_fails_without_retry_or_push(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "own", "src/a", [agent("write", "src/b/stolen.txt", "x")],
                     max_attempts=3)
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "FAILED" and "OwnershipViolation" in result.error
    assert sh("git", "branch", "--list", "factory/own", cwd=origin) == ""


async def test_failing_tests_stop_before_review(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "ft", "src/a", [agent("write", "src/a/other.txt", "1")])
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "FAILED_TESTS" and prs(state) == {}
    assert "review" not in receipt(state, "ft")["entries"]


def fake_opencode(tmp_path, body: str, code: int = 0) -> str:
    path = tmp_path / "fake-opencode"
    path.write_text(f"#!/bin/sh\ncat <<'EOF'\n{body}\nEOF\nexit {code}\n")
    path.chmod(0o755)
    return str(path)


async def test_opencode_review_approves_and_is_recorded(env, origin, dirs, queue, tmp_path, monkeypatch):
    _, state = dirs
    monkeypatch.setenv("FACTORY_OPENCODE_BIN", fake_opencode(
        tmp_path, '\x1b[1mreview\x1b[0m {"verdict": "APPROVE", "findings": "scoped and tested"}'))
    spec = make_spec(origin, queue, "ocr", "src/a", [agent("write", "src/a/one.txt", "1")],
                     reviewer="opencode", review_model="opencode-go/deepseek-v4.1-flash")
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "PR_OPEN"
    assert result.review["reviewer"] == "opencode:opencode-go/deepseek-v4.1-flash"
    assert receipt(state, "ocr")["entries"]["review"]["verdict"] == "APPROVE"


@pytest.mark.parametrize("body,code", [("not json at all", 0), ('{"verdict": "MAYBE"}', 0),
                                       ('{"verdict": "APPROVE"}', 0),
                                       ('{"verdict": "APPROVE"}', 1)])
async def test_opencode_review_failure_blocks_never_approves(env, origin, dirs, queue, tmp_path,
                                                             monkeypatch, body, code):
    _, state = dirs
    monkeypatch.setenv("FACTORY_OPENCODE_BIN", fake_opencode(tmp_path, body, code))
    spec = make_spec(origin, queue, f"blk{code}{len(body)}", "src/a",
                     [agent("write", "src/a/one.txt", "1")], reviewer="opencode")
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "BLOCKED_REVIEW" and prs(state) == {}


async def test_opencode_missing_binary_blocks(env, origin, dirs, queue, monkeypatch):
    _, state = dirs
    monkeypatch.setenv("FACTORY_OPENCODE_BIN", "/nonexistent/opencode")
    spec = make_spec(origin, queue, "nobin", "src/a", [agent("write", "src/a/one.txt", "1")],
                     reviewer="opencode")
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "BLOCKED_REVIEW" and prs(state) == {}


@pytest.mark.skipif(not os.environ.get("FACTORY_LIVE_OPENCODE"),
                    reason="live OpenCode call; set FACTORY_LIVE_OPENCODE=1")
async def test_live_opencode_deepseek_review(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "live", "src/a", [agent("write", "src/a/one.txt", "hello")],
                     reviewer="opencode", review_model=os.environ.get(
                         "FACTORY_REVIEW_MODEL", "opencode-go/deepseek-v4.1-flash"))
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.review["reviewer"].startswith("opencode:") and "deepseek" in result.review["reviewer"]
    assert result.review["verdict"] in {"APPROVE", "CHANGES"}, result.review
    assert result.status in {"PR_OPEN", "CHANGES_REQUESTED"}


async def test_empty_change_requests_changes(env, origin, dirs, queue):
    _, state = dirs
    spec = make_spec(origin, queue, "emp", "src/a", [agent("noop")], test_command=["true"])
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "CHANGES_REQUESTED" and prs(state) == {}
