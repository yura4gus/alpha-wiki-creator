from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from agent_factory.activities import ALL
from agent_factory.models import TaskSpec
from agent_factory.workflows import TaskWorkflow

TEMPORAL = (os.environ.get("FACTORY_TEMPORAL_BIN") or shutil.which("temporal")
            or "/opt/homebrew/bin/temporal")
FAKE = str(Path(__file__).parent / "fake_agent.py")
PLUGIN_ROOT = str(Path(__file__).resolve().parents[2])


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def agent(*args: str) -> list[str]:
    return [sys.executable, FAKE, *args]


def file_exists(path: str) -> list[str]:
    return [sys.executable, "-c", f"import pathlib,sys; sys.exit(0 if pathlib.Path({path!r}).exists() else 1)"]


@pytest.fixture
def origin(tmp_path) -> str:
    """Bare origin with a main branch holding the Alpha-Wiki contract files."""
    seed = tmp_path / "seed"
    seed.mkdir()
    sh("git", "init", "-q", "-b", "main", cwd=seed)
    sh("git", "config", "user.email", "t@t", cwd=seed)
    sh("git", "config", "user.name", "t", cwd=seed)
    for rel, text in {"AGENTS.md": "# contract\n", "wiki/graph/context_brief.md": "# brief\n",
                      "src/a/.keep": "", "src/b/.keep": "", "src/c/.keep": ""}.items():
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text(text)
    sh("git", "add", "-A", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    bare = tmp_path / "origin.git"
    sh("git", "clone", "-q", "--bare", str(seed), str(bare))
    return str(bare)


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    work, state = tmp_path / "work", tmp_path / "state"
    monkeypatch.setenv("FACTORY_WORK_ROOT", str(work))
    monkeypatch.setenv("FACTORY_STATE_DIR", str(state))
    monkeypatch.delenv("FACTORY_FAULTS", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return work, state


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def env():
    async with await WorkflowEnvironment.start_local(dev_server_existing_path=TEMPORAL) as e:
        yield e


@pytest.fixture
def queue() -> str:
    return f"q-{uuid.uuid4().hex[:8]}"


def worker(env, queue: str) -> Worker:
    return Worker(env.client, task_queue=queue, workflows=[TaskWorkflow], activities=ALL,
                  max_concurrent_activities=8)


def make_spec(origin: str, queue: str, task_id: str, owned: str, steps: list[list[str]],
              **kw) -> TaskSpec:
    base = dict(
        task_id=task_id, repo=origin, agent_steps=steps, owned_paths=[owned],
        test_command=file_exists(f"{owned}/one.txt"), task_queue=queue,
        require_approval=False, max_step_seconds=30, max_attempts=2,
        heartbeat_timeout_seconds=10)
    base.update(kw)
    return TaskSpec(**base)


def remote_log(origin: str, branch: str) -> str:
    return sh("git", "log", "--format=%H%n%B", branch, cwd=origin)
