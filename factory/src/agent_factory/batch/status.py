"""Read-only projection of batch workflow state plus its durable receipt."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from temporalio.client import Client

from .. import receipts
from ..config import Config
from .models import workflow_id
from .workflow import BatchWorkflow

_TERMINAL = {"BATCH_SUCCESS", "BATCH_FAILED", "BATCH_CANCELED"}


def receipt_doc(state_dir: Path | str, job_id: str) -> dict | None:
    path = receipts.receipt_path(state_dir, workflow_id(job_id))
    try:
        document = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def _units(entries: dict) -> list[dict[str, Any]]:
    units = []
    for key, value in entries.items():
        if not key.startswith("unit-") or not isinstance(value, dict):
            continue
        units.append({
            "unit_id": str(value.get("unit_id", key.removeprefix("unit-"))),
            "status": str(value.get("status", "")),
            "outputs": {str(k): str(v) for k, v in (value.get("outputs") or {}).items()},
            "checkpoint": str(value.get("checkpoint", "")),
            "checkpoint_reason": str(value.get("checkpoint_reason", "")),
        })
    return units


def project_receipt(doc: dict | None) -> dict[str, Any]:
    if doc is None:
        return {"receipt_status": "", "receipt_digest": "", "entries": [], "metrics": {},
                "units": [], "dq_status": "", "manifest_hash": "", "script_sha": ""}
    entries = doc.get("entries") or {}
    manifest = entries.get("manifest") or {}
    dq = entries.get("dq") or {}
    return {
        "receipt_status": str(doc.get("status", "")),
        "receipt_digest": str(doc.get("digest", "")),
        "entries": list(entries),
        "metrics": {key: value for key, value in (doc.get("metrics") or {}).items()
                    if isinstance(value, dict)},
        "units": _units(entries),
        "dq_status": str(dq.get("status", "")) if isinstance(dq, dict) else "",
        "manifest_hash": str(manifest.get("manifest_hash", "")) if isinstance(manifest, dict) else "",
        "script_sha": str(manifest.get("script_sha", "")) if isinstance(manifest, dict) else "",
    }


def _error(exc: BaseException) -> str:
    cause = getattr(exc, "cause", None)
    text = f"{type(exc).__name__}"
    if cause is not None:
        text += f": {type(cause).__name__}: {cause}"
    elif str(exc).strip():
        text += f": {exc}"
    return text[:500]


async def batch_status(client: Client, job_id: str) -> dict[str, Any]:
    """Query the live workflow and merge the durable receipt; never invents state."""
    document = receipt_doc(Config.from_env().state_dir, job_id)
    status: dict[str, Any] = {
        "job_id": job_id,
        "workflow_id": workflow_id(job_id),
        "state": "",
        "temporal_status": "",
        "error": "",
        **project_receipt(document),
    }
    handle = client.get_workflow_handle(workflow_id(job_id))
    try:
        described = await asyncio.wait_for(handle.describe(), timeout=5)
        status["temporal_status"] = described.status.name
    except Exception as exc:  # unknown workflow or server gone
        if not status["receipt_status"]:
            status["state"] = "NOT_FOUND"
            status["error"] = _error(exc)
            return status
        status["error"] = f"describe failed: {_error(exc)}"
    try:
        status["state"] = await asyncio.wait_for(handle.query(BatchWorkflow.state), timeout=5)
    except Exception as exc:
        if status["receipt_status"] in _TERMINAL:
            status["state"] = status["receipt_status"]
        else:
            status["error"] = status["error"] or f"state query failed: {_error(exc)}"
    if not status["state"]:
        status["state"] = "UNKNOWN"
    return status


__all__ = ["batch_status", "project_receipt", "receipt_doc"]
