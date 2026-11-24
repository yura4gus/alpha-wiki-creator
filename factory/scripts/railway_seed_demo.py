#!/usr/bin/env python3
"""Create a disposable origin repository and task spec inside the worker volume.

This is an operator script for the Railway pilot, not part of the factory runtime.
It writes only under `--root` (default `/data/seed`) and `/tmp`; it never calls
Temporal or a model. Submit the emitted spec with:

    python -m agent_factory.client start /data/seed/task.json

The origin is a bare repo on the durable volume, so the worker's checkpoint
pushes survive container restarts without a GitHub credential. Re-running keeps
the existing origin and writes a fresh task id/spec.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

APP = '''"""Tiny arithmetic module used by the Railway pilot."""


def add(left, right):
    """Return the sum of two numbers."""
    return left - right
'''

TEST = '''import unittest

from app.calc import add


class AddTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 2), 4)


if __name__ == "__main__":
    unittest.main()
'''

AGENTS = """# Pilot repository

`app/` is the only owned path. Tests run with
`python3 -m unittest discover -s tests -q`.
"""

GITIGNORE = """__pycache__/
*.pyc
"""

PROMPT = (
    "The repository has a failing unit test. Fix app/calc.py so that "
    "`python3 -m unittest discover -s tests -q` passes. Only edit files under "
    "app/. Do not run git commands."
)


def git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def seed_origin(origin: Path) -> None:
    if origin.exists():
        return
    work = Path(tempfile.mkdtemp(prefix="factory-seed-", dir="/tmp"))
    try:
        (work / "app").mkdir()
        (work / "tests").mkdir()
        (work / "app" / "__init__.py").write_text("")
        (work / "app" / "calc.py").write_text(APP)
        (work / "tests" / "test_calc.py").write_text(TEST)
        (work / "AGENTS.md").write_text(AGENTS)
        (work / ".gitignore").write_text(GITIGNORE)
        git("init", "--quiet", "--initial-branch=main", cwd=work)
        git("add", "-A", cwd=work)
        git("-c", "user.name=Alpha-Wiki Pilot", "-c", "user.email=pilot@localhost",
            "commit", "--quiet", "-m", "pilot: failing add test", cwd=work)
        origin.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--bare", "--quiet", str(work), str(origin))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def task_spec(origin: Path, task_id: str) -> dict:
    model = os.environ.get("FACTORY_REVIEW_MODEL", "opencode-go/deepseek-v4.1-flash")
    return {
        "task_id": task_id,
        "repo": str(origin),
        "base_ref": "main",
        "agent_steps": [["opencode", "run", "--auto", "-m", model, PROMPT]],
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
        "owned_paths": ["app"],
        "reviewer": "opencode",
        "review_model": model,
        "task_queue": os.environ.get("FACTORY_TASK_QUEUE", "factory-code"),
        "require_approval": True,
        "max_step_seconds": 600,
        "max_attempts": 2,
        "test_timeout_seconds": 120,
        "pr_backend": "local",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/data/seed", help="volume directory for origin and spec")
    parser.add_argument("--task-id", default=None, help="explicit task id (default: timestamped)")
    args = parser.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    origin = root / "origin.git"
    seed_origin(origin)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_id = args.task_id or f"railway-smoke-{stamp}"
    spec_path = root / "task.json"
    spec_path.write_text(json.dumps(task_spec(origin, task_id), indent=2) + "\n")
    print(json.dumps({"origin": str(origin), "task_id": task_id, "spec": str(spec_path)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
