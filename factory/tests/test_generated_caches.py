"""Regression: agent-run tests may write generated caches, never authored code.

A real task failed with `OwnershipViolation` because `git add -A` staged
`tests/__pycache__/*.pyc` created by the agent's own test run. Generated cache
paths are now excluded from staging and from the ownership check, while every
other untracked file remains subject to `owned_paths`.
"""

from __future__ import annotations

import json
import os

import pytest

from agent_factory import gitops, receipts
from agent_factory.activities import _env
from agent_factory.client import start_task
from agent_factory.config import Config

from conftest import agent, file_exists, make_spec, sh, worker

CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def assert_no_generated_cache(paths: list[str]) -> None:
    for path in paths:
        assert not gitops.is_generated_cache(path), path


@pytest.mark.asyncio(loop_scope="module")
async def test_agent_step_commits_owned_change_but_not_generated_caches(
        env, origin, dirs, queue):
    _work, _state = dirs
    spec = make_spec(origin, queue, "cachemix", "src/a",
                     [agent("write-with-cache", "src/a/one.txt", "1")])
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "PR_OPEN", result.error
    assert result.review["verdict"] == "APPROVE"
    changed = sh("git", "diff", "--name-only", "main", "factory/cachemix", cwd=origin).split()
    assert changed == ["src/a/one.txt"]  # only the authored, owned file
    tracked = sh("git", "ls-tree", "-r", "--name-only", "factory/cachemix", cwd=origin).split()
    assert_no_generated_cache(tracked)
    assert not any(part in CACHE_PARTS for path in tracked for part in path.split("/"))


@pytest.mark.asyncio(loop_scope="module")
async def test_cache_only_changes_do_not_fail_or_create_a_commit(
        env, origin, dirs, queue):
    _work, state = dirs
    spec = make_spec(origin, queue, "cacheonly", "src/a", [agent("cache-only")],
                     test_command=["true"])
    async with worker(env, queue):
        handle = await start_task(env.client, spec)
        result = await handle.result()
    # No authored change: the step returns the base checkpoint and review rejects the
    # empty diff. The point is that the generated caches never raise OwnershipViolation.
    assert result.status == "CHANGES_REQUESTED", result.error
    assert "OwnershipViolation" not in (result.error or "")
    assert sh("git", "branch", "--list", "factory/cacheonly", cwd=origin) == ""
    doc = json.loads(receipts.receipt_path(state, "task-cacheonly").read_text())
    assert doc["entries"]["step-0"]["changed"] is False


@pytest.mark.asyncio(loop_scope="module")
async def test_agent_step_pwd_is_the_worktree_not_the_worker_cwd(
        env, origin, dirs, queue):
    work, _state = dirs
    spec = make_spec(origin, queue, "pwdcheck", "src/a",
                     [agent("record-pwd", "src/a/pwd.txt")],
                     test_command=file_exists("src/a/pwd.txt"))
    worker_cwd = os.getcwd()
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()
    assert result.status == "PR_OPEN", result.error
    recorded = sh("git", "show", "factory/pwdcheck:src/a/pwd.txt", cwd=origin)
    assert recorded == str(work / "pwdcheck" / "wt")
    assert recorded != worker_cwd


@pytest.mark.parametrize("path,generated", [
    ("tests/__pycache__/test_calc.cpython-312.pyc", True),
    ("anything.pyc", True),
    (".pytest_cache/v/cache/nodeids", True),
    (".mypy_cache/3.12/cache.json", True),
    (".ruff_cache/content", True),
    ("src/app/__pycache__/module.pyc", True),
    ("src/app/cache_results.py", False),
    ("docs/__pycache__/design.md", True),  # inside a cache dir: still generated
    ("src/app/pycache.py", False),
    ("src/app/mypy_cache.py", False),
])
def test_generated_cache_classification(path, generated):
    assert gitops.is_generated_cache(path) is generated


def test_agent_environment_prevents_bytecode_and_redirects_cache(tmp_path):
    spec = make_spec("unused-origin", "q", "envcheck", "src/a", [agent("noop")])
    cfg = Config(work_root=tmp_path / "work", state_dir=tmp_path / "state")
    worktree = tmp_path / "work" / "envcheck" / "wt"
    environment = _env(spec, cfg, 0, workdir=worktree)
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert environment["PYTHONPYCACHEPREFIX"] == str(cfg.work_root / "pycache" / "envcheck")
    assert environment["PWD"] == str(worktree)
