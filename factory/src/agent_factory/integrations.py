"""Read-only boundaries to the Alpha-Wiki project tools.

Each authority keeps its own implementation:

- Alpha-Wiki supplies the pinned context (`build_context`) and the xPlan dry-run
  tool (`tools.xplan_dry_run`); the factory only invokes them.
- Harness² and OpenFlowKit are offline tools that write receipts. The factory
  reads those receipts; it never runs an experiment or renders a diagram.
- xPlan remains the task-state authority. This package only asks the dry-run
  planner for a proposed transition and never writes.

Paths in a TaskSpec are resolved against `plugin_root` when relative.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import EvidenceResult, TaskSpec

BOUNDARIES = {
    "execution": "Temporal TaskWorkflow owns durable execution and retries",
    "models": "OpenCode CLI owns every model call; no direct provider HTTP client",
    "context": "Alpha-Wiki pinned sources; the factory never rewrites wiki or raw files",
    "task_state": "xPlan owns issue state; reconcile_dry_run is read-only",
    "quality": "Harness² owns offline baseline/candidate experiments; the factory reads receipts",
    "architecture": "OpenFlowKit owns discovery/render/drift; the factory reads receipts",
    "delivery": "Git and the PR adapter supply commits and PR evidence",
}


def _resolve(root: Path | None, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() or root is None else Path(root) / path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def read_harness2(path: Path) -> tuple[str, dict]:
    doc = _load(path)
    if doc.get("profile") != "alpha-wiki" or doc.get("executor") != "deterministic":
        return "INVALID", {"kind": "harness2", "reason": "not an Alpha-Wiki deterministic replay"}
    result = doc.get("result")
    if result not in {"PASS", "DRIFT", "UNKNOWN"}:
        return "INVALID", {"kind": "harness2", "reason": f"unknown result {result!r}"}
    cases = doc.get("cases") or {}
    failed = [name for name, case in cases.items() if not case.get("candidate_pass")]
    return result, {"kind": "harness2", "result": result, "cases": len(cases),
                    "failed_cases": failed, "engine_receipt": str(doc.get("engine_receipt", ""))}


def read_openflowkit(path: Path) -> tuple[str, dict]:
    doc = _load(path)
    if doc.get("kind") not in {"repo-observed", "repo-drift"}:
        return "INVALID", {"kind": "openflowkit", "reason": "not a repo-scoped report"}
    result = doc.get("result")
    if result not in {"PASS", "DRIFT", "UNKNOWN"}:
        return "INVALID", {"kind": "openflowkit", "reason": f"unknown result {result!r}"}
    source = doc.get("source") or {}
    if not source.get("sha") or not doc.get("model_sha256"):
        return "INVALID", {"kind": "openflowkit", "reason": "report has no pinned source SHA"}
    return result, {"kind": "openflowkit", "result": result, "kind_detail": doc["kind"],
                    "sha": source["sha"], "model_sha256": doc["model_sha256"],
                    "tool": doc.get("tool", "")}


def read_evidence(spec: TaskSpec) -> EvidenceResult:
    """Read the configured receipts. Missing optional evidence is not a failure."""
    root = Path(spec.plugin_root) if spec.plugin_root else None
    wanted = [("harness2", spec.harness2_evaluation, read_harness2),
              ("openflowkit", spec.openflowkit_report, read_openflowkit)]
    refs, sources, statuses, notes = [], [], [], []
    for name, value, reader in wanted:
        if not value:
            continue
        path = _resolve(root, value)
        if not path.is_file():
            statuses.append("MISSING")
            notes.append(f"{name}: missing {value}")
            continue
        try:
            status, detail = reader(path)
        except (OSError, ValueError, TypeError) as exc:
            status, detail = "INVALID", {"kind": name, "reason": f"{type(exc).__name__}: {exc}"[:300]}
        detail["path"] = str(path)
        detail["sha256"] = _digest(path)
        statuses.append(status)
        sources.append(detail)
        refs.append(f"{name}:{detail.get('result', status)}@{detail['sha256'][:16]}")
        if status not in {"PASS"}:
            notes.append(f"{name}: {status}")
    if not statuses:
        return EvidenceResult("MISSING", [], [], "no external evidence configured")
    for worst in ("INVALID", "DRIFT", "UNKNOWN", "MISSING"):
        if worst in statuses:
            return EvidenceResult(worst, refs, sources, "; ".join(notes))
    return EvidenceResult("PASS", refs, sources, "")
