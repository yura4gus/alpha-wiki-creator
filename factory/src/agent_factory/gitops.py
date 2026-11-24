"""Git primitives. Everything here is safe to repeat.

Checkpoints are the durable progress record: each agent step ends as one commit
pushed to `factory/<task_id>` on origin, carrying a `Factory-Step` trailer. A
lost worktree is rebuilt from origin, never assumed to survive a worker.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

SHA_RE = re.compile(r"[0-9a-f]{40}")
IDENTITY = {
    "GIT_AUTHOR_NAME": "Alpha-Wiki Agent Factory",
    "GIT_AUTHOR_EMAIL": "agent-factory@localhost",
    "GIT_COMMITTER_NAME": "Alpha-Wiki Agent Factory",
    "GIT_COMMITTER_EMAIL": "agent-factory@localhost",
}


class GitError(RuntimeError):
    pass


class OwnershipViolation(RuntimeError):
    pass


def git(args: list[str], cwd: Path | str | None = None, env: dict | None = None,
        check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})},
    )
    if check and proc.returncode:
        raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout.strip()


@contextmanager
def file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def branch_name(task_id: str) -> str:
    return f"factory/{task_id}"


def resolve_base(repo: str, ref: str) -> str:
    if SHA_RE.fullmatch(ref):
        return ref
    out = git(["ls-remote", repo, f"refs/heads/{ref}"])
    if not out:
        raise GitError(f"base ref {ref!r} not found in {repo}")
    return out.split()[0]


def cache_path(work_root: Path, repo: str) -> Path:
    return Path(work_root) / "_cache" / (hashlib.sha1(repo.encode()).hexdigest()[:12] + ".git")


def ensure_cache(work_root: Path, repo: str) -> Path:
    """Bare clone shared by all worktrees of one repo on this worker."""
    cache = cache_path(work_root, repo)
    with file_lock(cache.with_suffix(".lock")):
        if not (cache / "HEAD").exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            git(["clone", "--bare", "--quiet", repo, str(cache)])
            git(["config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"], cwd=cache)
        git(["fetch", "--quiet", "--prune", "origin"], cwd=cache)
    return cache


def remote_tip(cache: Path, task_id: str) -> str | None:
    out = git(["rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch_name(task_id)}"],
              cwd=cache, check=False)
    return out or None


def find_confirmed_step(cache: Path, task_id: str, index: int, checkpoint: str) -> str | None:
    """Return the pushed commit that already completed this step, if any."""
    tip = remote_tip(cache, task_id)
    if not tip or tip == checkpoint:
        return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", checkpoint, tip],
                      cwd=cache, capture_output=True).returncode:
        return None
    out = git(["log", "--format=%H", f"--grep=^Factory-Step: {task_id}/{index}$",
               f"{checkpoint}..{tip}"], cwd=cache)
    return out.splitlines()[0] if out else None


def ensure_worktree(work_root: Path, repo: str, task_id: str, checkpoint: str) -> Path:
    """Isolated worktree reset to a known checkpoint; rebuilt if it was lost."""
    cache = ensure_cache(work_root, repo)
    wt = Path(work_root) / task_id / "wt"
    with file_lock(cache.with_suffix(".lock")):
        git(["worktree", "prune"], cwd=cache)
        if wt.exists() and not (wt / ".git").exists():
            shutil.rmtree(wt)
        if not wt.exists():
            wt.parent.mkdir(parents=True, exist_ok=True)
            git(["worktree", "add", "--force", "-B", branch_name(task_id), str(wt), checkpoint],
                cwd=cache)
    git(["reset", "--hard", "--quiet", checkpoint], cwd=wt)
    git(["clean", "-fdxq"], cwd=wt)
    return wt


def remove_worktree(work_root: Path, repo: str, task_id: str) -> bool:
    cache = cache_path(work_root, repo)
    wt = Path(work_root) / task_id / "wt"
    removed = wt.exists()
    if removed:
        shutil.rmtree(wt, ignore_errors=True)
    if (cache / "HEAD").exists():
        with file_lock(cache.with_suffix(".lock")):
            git(["worktree", "prune"], cwd=cache, check=False)
    return removed


def _owned(path: str, owned_paths: list[str]) -> bool:
    return any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in owned_paths)


def commit_and_push(wt: Path, task_id: str, index: int, checkpoint: str,
                    owned_paths: list[str]) -> tuple[str, bool]:
    """Commit the step's changes deterministically and push; repeat-safe.

    Raises OwnershipViolation (after restoring the checkpoint) if the agent
    touched files outside `owned_paths`.
    """
    git(["add", "-A"], cwd=wt)
    names = [n for n in git(["diff", "--cached", "--name-only", "-z"], cwd=wt).split("\0") if n]
    if not names:
        return checkpoint, False
    outside = [n for n in names if not _owned(n, owned_paths)]
    if outside:
        git(["reset", "--hard", "--quiet", checkpoint], cwd=wt)
        git(["clean", "-fdxq"], cwd=wt)
        raise OwnershipViolation(f"changed files outside owned paths {owned_paths}: {outside}")
    when = git(["show", "-s", "--format=%cI", checkpoint], cwd=wt)  # deterministic commit time
    message = (f"factory({task_id}): step {index}\n\n"
               f"Factory-Task: {task_id}\nFactory-Step: {task_id}/{index}\n"
               f"Factory-Parent: {checkpoint}")
    git(["commit", "-q", "-m", message], cwd=wt,
        env={**IDENTITY, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
    sha = git(["rev-parse", "HEAD"], cwd=wt)
    git(["push", "--quiet", "origin", f"{sha}:refs/heads/{branch_name(task_id)}"], cwd=wt)
    return sha, True


def diff_text(cache: Path, base: str, head: str, limit: int = 60000) -> str:
    text = git(["diff", "--stat", base, head], cwd=cache) + "\n\n" + git(["diff", base, head], cwd=cache)
    return text[:limit]


def show_file(cache: Path, sha: str, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=cache, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None
