import subprocess
from pathlib import Path

from tools.worktree_snapshot import build_snapshot


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "alpha-wiki@example.test")
    _git(tmp_path, "config", "user.name", "Alpha-Wiki Test")
    (tmp_path / "tracked.md").write_text("stable\n")
    _git(tmp_path, "add", "tracked.md")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_clean_snapshot_uses_exact_head(tmp_path: Path):
    repo = _repo(tmp_path)

    snapshot = build_snapshot(repo)

    assert not snapshot.dirty
    assert snapshot.snapshot_id == snapshot.base_sha
    assert len(snapshot.worktree_digest) == 64


def test_dirty_snapshot_is_stable_and_tracks_tracked_content(tmp_path: Path):
    repo = _repo(tmp_path)
    (repo / "tracked.md").write_text("changed\n")

    first = build_snapshot(repo)
    second = build_snapshot(repo)
    (repo / "tracked.md").write_text("changed again\n")
    third = build_snapshot(repo)

    assert first.dirty
    assert first.snapshot_id == second.snapshot_id
    assert first.snapshot_id != third.snapshot_id
    assert first.snapshot_id.startswith(first.base_sha + "+worktree:")


def test_dirty_snapshot_tracks_untracked_content(tmp_path: Path):
    repo = _repo(tmp_path)
    untracked = repo / "new source.md"
    untracked.write_text("first\n")

    first = build_snapshot(repo)
    untracked.write_text("second\n")
    second = build_snapshot(repo)

    assert first.dirty and second.dirty
    assert first.worktree_digest != second.worktree_digest
