"""Create a reproducible repository snapshot ID for Codex subagent work."""
from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click


SNAPSHOT_FORMAT = b"alpha-wiki-worktree-v1\0"


@dataclass(frozen=True)
class WorktreeSnapshot:
    repository: str
    branch: str
    base_sha: str
    dirty: bool
    worktree_digest: str
    snapshot_id: str


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        message = result.stderr.decode(errors="replace").strip() or "git command failed"
        raise RuntimeError(message)
    return result


def _hash_field(hasher: object, name: bytes, value: bytes) -> None:
    hasher.update(name + b"\0")  # type: ignore[attr-defined]
    hasher.update(len(value).to_bytes(8, "big"))  # type: ignore[attr-defined]
    hasher.update(value)  # type: ignore[attr-defined]


def _hash_untracked_file(hasher: object, root: Path, raw_path: bytes) -> None:
    path = root / os.fsdecode(raw_path)
    _hash_field(hasher, b"path", raw_path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        _hash_field(hasher, b"type", b"missing")
        return

    if stat.S_ISLNK(mode):
        _hash_field(hasher, b"type", b"symlink")
        _hash_field(hasher, b"target", os.fsencode(os.readlink(path)))
        return
    if stat.S_ISREG(mode):
        executable = b"executable" if mode & 0o111 else b"regular"
        _hash_field(hasher, b"type", executable)
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                _hash_field(hasher, b"content", chunk)
        return
    _hash_field(hasher, b"type", b"other")


def build_snapshot(root: Path) -> WorktreeSnapshot:
    requested_root = root.resolve()
    repository = Path(
        os.fsdecode(_git(requested_root, "rev-parse", "--show-toplevel").stdout).strip()
    ).resolve()
    base_sha = os.fsdecode(_git(repository, "rev-parse", "HEAD").stdout).strip()
    branch_result = _git(repository, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    branch = os.fsdecode(branch_result.stdout).strip() or "HEAD"
    status = _git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    tracked_diff = _git(
        repository,
        "diff",
        "--binary",
        "--no-ext-diff",
        "HEAD",
        "--",
    ).stdout
    untracked = _git(
        repository,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout.split(b"\0")

    hasher = hashlib.sha256()
    hasher.update(SNAPSHOT_FORMAT)
    _hash_field(hasher, b"base_sha", base_sha.encode())
    _hash_field(hasher, b"status", status)
    _hash_field(hasher, b"tracked_diff", tracked_diff)
    for raw_path in sorted(path for path in untracked if path):
        _hash_untracked_file(hasher, repository, raw_path)

    digest = hasher.hexdigest()
    dirty = bool(status)
    snapshot_id = f"{base_sha}+worktree:{digest}" if dirty else base_sha
    return WorktreeSnapshot(
        repository=str(repository),
        branch=branch,
        base_sha=base_sha,
        dirty=dirty,
        worktree_digest=digest,
        snapshot_id=snapshot_id,
    )


@click.command()
@click.option("--root", type=click.Path(path_type=Path), default=Path("."), show_default=True)
@click.option("--json-output", is_flag=True, help="Print the full snapshot record as JSON.")
def main(root: Path, json_output: bool) -> None:
    snapshot = build_snapshot(root)
    if json_output:
        import json

        click.echo(json.dumps(asdict(snapshot), indent=2))
    else:
        click.echo(snapshot.snapshot_id)


if __name__ == "__main__":
    main()
