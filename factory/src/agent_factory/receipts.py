"""Persistent execution receipts.

One JSON file per workflow in the durable state dir. Entries are keyed by step
and written idempotently: the same data is `unchanged`. The digest covers only
deterministic content (no timestamps or durations), so reruns of the same task
over the same base reproduce it.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "agent-factory.receipt/1"
TERMINAL = {
    "PR_OPEN", "FAILED", "FAILED_TESTS", "CHANGES_REQUESTED", "BLOCKED_REVIEW",
    "REJECTED", "APPROVAL_TIMEOUT", "CANCELED",
}


def receipt_path(state_dir: Path, workflow_id: str) -> Path:
    return Path(state_dir) / "receipts" / f"{workflow_id}.json"


@contextmanager
def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _store(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(state_dir: Path, workflow_id: str, task_id: str, key: str, data: dict,
           metrics: dict | None = None) -> str:
    """Write one entry. Returns created | unchanged | updated."""
    path = receipt_path(state_dir, workflow_id)
    with _locked(path):
        doc = _load(path) or {
            "schema": SCHEMA, "workflow_id": workflow_id, "task_id": task_id,
            "status": "RUNNING", "entries": {}, "metrics": {}, "recorded_at": _now(),
        }
        if doc["status"] in TERMINAL:
            return "unchanged"  # terminal receipts are frozen
        old = doc["entries"].get(key)
        if old == data:
            outcome = "unchanged"
        else:
            outcome = "created" if old is None else "updated"
            doc["entries"][key] = data
        if metrics is not None:
            doc["metrics"][key] = metrics
        _store(path, doc)
        return outcome


def digest(doc: dict) -> str:
    body = {k: doc[k] for k in ("schema", "workflow_id", "task_id", "status", "entries")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def finalize(state_dir: Path, workflow_id: str, task_id: str, status: str) -> dict:
    """Freeze the receipt with its terminal status. Repeat calls are no-ops."""
    path = receipt_path(state_dir, workflow_id)
    with _locked(path):
        doc = _load(path) or {
            "schema": SCHEMA, "workflow_id": workflow_id, "task_id": task_id,
            "status": "RUNNING", "entries": {}, "metrics": {}, "recorded_at": _now(),
        }
        if doc["status"] not in TERMINAL:
            doc["status"] = status
            doc["finalized_at"] = _now()
            doc["digest"] = digest(doc)
            _store(path, doc)
        return doc


def validate(doc: dict) -> list[str]:
    problems = []
    for key in ("schema", "workflow_id", "task_id", "status", "entries"):
        if key not in doc:
            problems.append(f"missing {key}")
    if doc.get("schema") != SCHEMA:
        problems.append("unknown schema")
    if doc.get("status") in TERMINAL and doc.get("digest") != digest(doc):
        problems.append("digest mismatch")
    return problems
