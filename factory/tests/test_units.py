import json

import pytest

from agent_factory import gitops, receipts
from agent_factory.client import validate_batch
from agent_factory.models import TaskSpec
from conftest import agent, sh


def spec(task_id, owned, repo="r"):
    return TaskSpec(task_id=task_id, repo=repo, agent_steps=[agent("noop")], test_command=["true"],
                    owned_paths=owned)


def test_receipt_record_is_idempotent_and_freezes(tmp_path):
    assert receipts.record(tmp_path, "task-x", "x", "k", {"a": 1}) == "created"
    assert receipts.record(tmp_path, "task-x", "x", "k", {"a": 1}) == "unchanged"
    assert receipts.record(tmp_path, "task-x", "x", "k", {"a": 2}) == "updated"
    first = receipts.finalize(tmp_path, "task-x", "x", "PR_OPEN")
    again = receipts.finalize(tmp_path, "task-x", "x", "FAILED")
    assert again["status"] == "PR_OPEN" and again["digest"] == first["digest"]
    assert receipts.record(tmp_path, "task-x", "x", "k", {"a": 3}) == "unchanged"
    assert receipts.validate(json.loads(receipts.receipt_path(tmp_path, "task-x").read_text())) == []


def test_receipt_digest_ignores_metrics_and_time(tmp_path):
    for d, secs in (("one", 1), ("two", 99)):
        receipts.record(tmp_path / d, "task-x", "x", "k", {"a": 1}, {"seconds": secs})
    a = receipts.finalize(tmp_path / "one", "task-x", "x", "PR_OPEN")
    b = receipts.finalize(tmp_path / "two", "task-x", "x", "PR_OPEN")
    assert a["digest"] == b["digest"]


def test_overlapping_ownership_is_rejected():
    with pytest.raises(ValueError, match="overlap"):
        validate_batch([spec("a", ["src/a"]), spec("b", ["src/a/deep"])])
    validate_batch([spec("a", ["src/a"]), spec("b", ["src/ab"])])  # prefix of name is not overlap
    validate_batch([spec("a", ["src/a"], repo="r1"), spec("b", ["src/a"], repo="r2")])
    with pytest.raises(ValueError, match="duplicate"):
        validate_batch([spec("a", ["x"]), spec("a", ["y"])])
    with pytest.raises(ValueError, match="repo-relative"):
        validate_batch([spec("a", ["../x"])])


def test_checkpoint_commit_is_deterministic_across_worktrees(origin, tmp_path):
    base = gitops.resolve_base(origin, "main")
    shas = []
    for name in ("w1", "w2"):
        wt = gitops.ensure_worktree(tmp_path / name, origin, "t", base)
        (wt / "src/a").mkdir(parents=True, exist_ok=True)
        (wt / "src/a/one.txt").write_text("same\n")
        sha, changed = gitops.commit_and_push(wt, "t", 0, base, ["src/a"]) if name == "w1" else (
            None, None)
        if name == "w1":
            shas.append(sha)
    # second worktree: same edit, same parent, same message => same commit id (push is a no-op)
    wt2 = gitops.ensure_worktree(tmp_path / "w2", origin, "t2", base)
    (wt2 / "src/a").mkdir(parents=True, exist_ok=True)
    (wt2 / "src/a/one.txt").write_text("same\n")
    sha2, _ = gitops.commit_and_push(wt2, "t", 0, base, ["src/a"])
    assert sha2 == shas[0]


def test_ownership_violation_restores_checkpoint(origin, tmp_path):
    base = gitops.resolve_base(origin, "main")
    wt = gitops.ensure_worktree(tmp_path, origin, "t", base)
    (wt / "src/b").mkdir(parents=True, exist_ok=True)
    (wt / "src/b/x.txt").write_text("nope\n")
    with pytest.raises(gitops.OwnershipViolation):
        gitops.commit_and_push(wt, "t", 0, base, ["src/a"])
    assert not (wt / "src/b/x.txt").exists()
    assert sh("git", "branch", "--list", "factory/t", cwd=origin) == ""
