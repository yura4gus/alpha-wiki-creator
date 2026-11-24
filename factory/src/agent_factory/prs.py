"""Idempotent pull request creation: look up by head branch, create only if absent."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .gitops import file_lock


class LocalPRAdapter:
    """File-backed registry in the durable state dir. For tests and dry runs."""

    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / "prs.json"

    def ensure_pr(self, repo: str, head: str, base: str, title: str, body: str,
                  head_sha: str) -> dict:
        with file_lock(self.path.with_suffix(".lock")):
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            key = f"{repo}::{head}"
            record = data.get(key)
            created = record is None or record["state"] != "open"
            if created:
                record = {"number": len(data) + 1, "repo": repo, "head": head, "base": base,
                          "title": title, "state": "open"}
            record.update(head_sha=head_sha, body=body)
            data[key] = record
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
            os.replace(tmp, self.path)
            return {**record, "created": created}


class GhPRAdapter:
    """GitHub via the gh CLI. Opens drafts only. Not exercised by the test suite."""

    def __init__(self, gh_repo: str):
        self.gh_repo = gh_repo

    def _gh(self, *args: str) -> str:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
        return proc.stdout.strip()

    def ensure_pr(self, repo: str, head: str, base: str, title: str, body: str,
                  head_sha: str) -> dict:
        found = json.loads(self._gh("pr", "list", "--repo", self.gh_repo, "--head", head,
                                    "--state", "open", "--json", "number,url,headRefOid"))
        if found:
            return {**found[0], "head": head, "head_sha": head_sha, "created": False}
        url = self._gh("pr", "create", "--repo", self.gh_repo, "--head", head, "--base", base,
                       "--title", title, "--body", body, "--draft")
        return {"url": url, "head": head, "base": base, "head_sha": head_sha, "created": True}


def adapter_for(backend: str, state_dir: Path, pr_repo: str | None):
    if backend == "local":
        return LocalPRAdapter(state_dir)
    if backend == "gh":
        if not pr_repo:
            raise ValueError("pr_backend=gh requires pr_repo")
        return GhPRAdapter(pr_repo)
    raise ValueError(f"unknown pr_backend {backend!r}")
