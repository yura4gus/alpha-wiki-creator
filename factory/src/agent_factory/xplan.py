"""Read-only ITSPlan (xPlan) binding for factory tasks.

The adapter is deliberately small and write-free:

- a snapshot (JSON written by an authorised read-only exporter) supplies the
  project, issue requirements, dependencies, revision and column map;
- `bind_issue` maps the issue identifier to the factory workflow id
  ``task-<task_id>`` and builds the exact binding/observed payload the existing
  ``tools.xplan_dry_run.plan_transition`` already understands;
- `task_spec` produces a TaskSpec for the coordinator's ``submit_task`` tool
  (or the factory client); it refuses an unapproved issue;
- `propose_transition` calls the project's own planner and returns its
  ``dry_run`` receipt. There is no PATCH/PUT/POST path and no second backlog.

The xPlan HTTP API is not called here. ``plan-api.value8.dev`` requires
authentication; the public JSON snapshot is the single read boundary. See
``factory/RAILWAY.md`` for the current access blocker.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

SNAPSHOT_SCHEMA = "agent-factory.xplan-snapshot/1"
REQUIRED_COLUMNS = ("TODO", "IN_PROGRESS", "DONE", "REWORK")
TERMINAL_OR_CLOSED = {"DONE", "CANCELED"}
_SAFE_TASK_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")


class XPlanError(ValueError):
    """The snapshot, binding or planner input is invalid."""


class XPlanConflict(XPlanError):
    """The issue cannot be bound yet (for example an open dependency)."""


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise XPlanError(f"{field} must be a non-empty string")
    return value.strip()


def _integer(value: Any, field: str, *, low: int = 0) -> int:
    if type(value) is not int or value < low:
        raise XPlanError(f"{field} must be an integer >= {low}")
    return value


def _dependencies(raw: Any) -> list[dict[str, str | None]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise XPlanError("issue.dependencies must be a list")
    result: list[dict[str, str | None]] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            identifier, status = item.strip(), None
        elif isinstance(item, Mapping):
            identifier = item.get("identifier")
            status = item.get("status")
        else:
            raise XPlanError(f"issue.dependencies[{index}] must be a string or object")
        if not isinstance(identifier, str) or not identifier.strip():
            raise XPlanError(f"issue.dependencies[{index}].identifier is required")
        if status is not None and (not isinstance(status, str) or not status.strip()):
            raise XPlanError(f"issue.dependencies[{index}].status must be a string")
        result.append({"identifier": identifier.strip(),
                       "status": status.strip().upper() if status else None})
    return result


def validate_snapshot(doc: Any) -> dict:
    """Validate a read-only xPlan snapshot and return a normalised copy."""
    if not isinstance(doc, Mapping):
        raise XPlanError("snapshot must be a JSON object")
    if doc.get("schema") not in (None, SNAPSHOT_SCHEMA):
        raise XPlanError(f"unsupported snapshot schema {doc.get('schema')!r}")

    project = doc.get("project") or {}
    if not isinstance(project, Mapping):
        raise XPlanError("project must be an object")
    project_id = project.get("id")
    if project_id is not None and type(project_id) is not int:
        raise XPlanError("project.id must be an integer when present")

    issue = doc.get("issue")
    if not isinstance(issue, Mapping):
        raise XPlanError("snapshot.issue is required")
    identifier = _text(issue.get("identifier"), "issue.identifier")
    updated_at = _text(issue.get("updatedAt"), "issue.updatedAt")
    title = _text(issue.get("title"), "issue.title")
    description = _text(issue.get("description"), "issue.description", allow_empty=True)
    columns = doc.get("columns")
    if not isinstance(columns, Mapping):
        raise XPlanError("snapshot.columns is required")
    normalised_columns: dict[str, int] = {}
    for name, value in columns.items():
        if not isinstance(name, str) or not name.strip():
            raise XPlanError("columns keys must be non-empty strings")
        normalised_columns[name.strip().upper()] = _integer(
            value, f"columns.{name}", low=1)
    missing = [name for name in REQUIRED_COLUMNS if name not in normalised_columns]
    if missing:
        raise XPlanError(f"columns is missing {missing}")

    required_level = issue.get("required_delivery_level")
    if required_level is None:
        required_level = doc.get("required_delivery_level")
    required_level = _integer(required_level, "issue.required_delivery_level", low=1)
    if required_level > 6:
        raise XPlanError("issue.required_delivery_level must be 1 through 6")
    worker = issue.get("worker") or doc.get("worker") or "opencode"
    worker = _text(worker, "issue.worker")

    return {
        "schema": SNAPSHOT_SCHEMA,
        "project": {
            "id": project_id,
            "name": _text(project.get("name", "xPlan"), "project.name"),
            "revision": _text(project.get("revision", ""), "project.revision",
                              allow_empty=True) or None,
        },
        "issue": {
            "id": _integer(issue.get("id"), "issue.id", low=1),
            "identifier": identifier,
            "title": title,
            "description": description,
            "columnId": _integer(issue.get("columnId"), "issue.columnId", low=1),
            "updatedAt": updated_at,
            "dependencies": _dependencies(issue.get("dependencies")),
            "required_delivery_level": required_level,
            "worker": worker,
        },
        "columns": normalised_columns,
        "run_id": _text(doc.get("run_id"), "run_id"),
        "approved_by": (doc.get("approved_by") or "").strip() or None,
    }


def load_snapshot(path: str | Path) -> dict:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise XPlanError(f"cannot read snapshot {path}: {type(exc).__name__}: {exc}") from exc
    return validate_snapshot(raw)


def task_id_for(identifier: str) -> str:
    """Deterministic, branch-safe task id bound to the issue identifier."""
    candidate = re.sub(r"[^a-z0-9._-]+", "-", identifier.strip().lower()).strip("-._")
    if not candidate or not _SAFE_TASK_ID.fullmatch(candidate) or candidate in {".", ".."}:
        raise XPlanError(f"cannot derive a safe task id from {identifier!r}")
    return candidate


def open_dependencies(binding: Mapping[str, Any]) -> list[dict[str, str | None]]:
    return [dep for dep in binding["issue"]["dependencies"]
            if dep.get("status") and dep["status"] not in TERMINAL_OR_CLOSED]


def bind_issue(snapshot: Mapping[str, Any], *, task_id: str | None = None,
               require_dependencies_done: bool = False) -> dict:
    """Bind one issue to ``task-<id>`` and the planner's binding/observed shape."""
    doc = validate_snapshot(snapshot)
    identifier = doc["issue"]["identifier"]
    resolved = task_id or task_id_for(identifier)
    if not _SAFE_TASK_ID.fullmatch(resolved) or resolved in {".", ".."}:
        raise XPlanError(f"task_id {resolved!r} is not branch-safe")
    if require_dependencies_done:
        blocked = open_dependencies(doc)
        if blocked:
            names = ", ".join(str(dep["identifier"]) for dep in blocked)
            raise XPlanConflict(f"issue {identifier} has open dependencies: {names}")

    pinned = {
        "id": doc["issue"]["id"],
        "identifier": identifier,
        "updatedAt": doc["issue"]["updatedAt"],
        "columnId": doc["issue"]["columnId"],
    }
    binding = {
        "issue": pinned,
        "columns": doc["columns"],
        "run_id": doc["run_id"],
        "required_delivery_level": doc["issue"]["required_delivery_level"],
        "worker": doc["issue"]["worker"],
    }
    return {
        "schema": SNAPSHOT_SCHEMA,
        "project": doc["project"],
        "issue_id": identifier,
        "task_id": resolved,
        "workflow_id": f"task-{resolved}",
        "requirements": {
            "title": doc["issue"]["title"],
            "description": doc["issue"]["description"],
            "dependencies": doc["issue"]["dependencies"],
            "revision": doc["issue"]["updatedAt"],
        },
        "binding": binding,
        "observed": dict(pinned),
        "approved_by": doc["approved_by"],
    }


def task_spec(binding: Mapping[str, Any], *, repo: str, agent_steps: list[list[str]],
              test_command: list[str], owned_paths: list[str],
              plugin_root: str | None = None, **overrides: Any) -> dict:
    """Build the TaskSpec payload for the coordinator's ``submit_task`` tool."""
    if not binding.get("approved_by"):
        raise XPlanConflict("the snapshot has no approved_by; an unapproved issue cannot start")
    if "xplan" in overrides:
        raise XPlanError("xplan binding is owned by the adapter")
    spec = {
        "task_id": binding["task_id"],
        "repo": repo,
        "agent_steps": agent_steps,
        "test_command": test_command,
        "owned_paths": owned_paths,
        "xplan": {"binding": binding["binding"], "observed": binding["observed"]},
        **overrides,
    }
    if plugin_root:
        spec["plugin_root"] = plugin_root
    from .client import validate_batch
    from .models import TaskSpec

    validate_batch([TaskSpec(**spec)])
    return spec


async def submit_task(client: Any, binding: Mapping[str, Any], spec: Mapping[str, Any]) -> str:
    """Start ``task-<id>`` through the existing client; return the workflow id."""
    if not binding.get("approved_by"):
        raise XPlanConflict("the snapshot has no approved_by; refusing to submit")
    if spec.get("task_id") != binding.get("task_id"):
        raise XPlanError("task spec id does not match the bound issue")
    from .client import start_task
    from .models import TaskSpec

    handle = await start_task(client, TaskSpec(**spec))
    return handle.id


def _head_sha(entries: Mapping[str, Any]) -> str:
    best, sha = -1, ""
    for key, value in entries.items():
        if not key.startswith("step-") or not isinstance(value, Mapping):
            continue
        try:
            index = int(key.split("-", 1)[1])
        except ValueError:
            continue
        if index >= best:
            best, sha = index, str(value.get("sha", ""))
    if sha:
        return sha
    pinned = entries.get("pinned")
    return str(pinned.get("base_sha", "")) if isinstance(pinned, Mapping) else ""


def status_view(receipt: Mapping[str, Any]) -> dict:
    """Read status, review, evidence and xPlan proposal from a frozen receipt."""
    entries = receipt.get("entries") or {}
    review = entries.get("review") or {}
    evidence = entries.get("evidence") or {}
    plan = entries.get("xplan_dry_run") or {}
    return {
        "workflow_id": receipt.get("workflow_id"),
        "task_id": receipt.get("task_id"),
        "status": receipt.get("status"),
        "digest": receipt.get("digest"),
        "head_sha": _head_sha(entries),
        "review": {
            "verdict": review.get("verdict"),
            "reviewer": review.get("reviewer"),
            "findings": review.get("findings"),
        },
        "evidence": {
            "status": evidence.get("status"),
            "sources": evidence.get("sources") or [],
            "note": evidence.get("note", ""),
        },
        "xplan_dry_run": plan,
        "approval": entries.get("approval") or {},
        "mode": "read_only",
    }


async def read_status(client: Any, task_id: str, state_dir: str | Path) -> dict:
    """Live workflow state plus the durable receipt, read-only."""
    import asyncio

    from .client import workflow_id
    from . import receipts
    from .workflows import TaskWorkflow

    view: dict[str, Any] = {"task_id": task_id, "workflow_id": workflow_id(task_id)}
    try:
        handle = client.get_workflow_handle(workflow_id(task_id))
        view["state"] = await asyncio.wait_for(handle.query(TaskWorkflow.state), timeout=5)
        view["temporal"] = (await asyncio.wait_for(handle.describe(), timeout=5)).status.name
    except Exception as exc:  # read-only projection; a missing workflow is reported
        view["state_error"] = f"{type(exc).__name__}: {exc}"[:300]
    path = receipts.receipt_path(Path(state_dir), workflow_id(task_id))
    try:
        receipt = json.loads(path.read_text())
    except (OSError, ValueError):
        receipt = None
    if receipt is not None:
        view.update(status_view(receipt))
    return view


def _planner(plugin_root: str | Path):
    path = Path(plugin_root) / "tools" / "xplan_dry_run.py"
    if not path.is_file():
        raise XPlanError(f"xPlan planner not found: {path}")
    spec = importlib.util.spec_from_file_location("alpha_wiki_xplan_dry_run", path)
    if spec is None or spec.loader is None:
        raise XPlanError(f"cannot load xPlan planner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan_transition


def propose_transition(binding: Mapping[str, Any], event: Mapping[str, Any],
                       plugin_root: str | Path = ".") -> dict:
    """Call the existing planner; the result is always a dry-run receipt."""
    plan = _planner(plugin_root)(dict(binding["binding"]), dict(binding["observed"]),
                                 dict(event))
    if plan.get("mode") != "dry_run":
        raise XPlanError("planner did not return a dry-run receipt")
    return {**plan, "task_id": binding["task_id"], "workflow_id": binding["workflow_id"]}


def _load(path: str | Path) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise XPlanError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent-factory-xplan",
                                     description="Read-only ITSPlan binding and dry-run planner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    bind = sub.add_parser("bind", help="bind a snapshot issue to task-<id>")
    bind.add_argument("snapshot")
    bind.add_argument("--task-id", default=None)
    bind.add_argument("--require-dependencies-done", action="store_true")

    build = sub.add_parser("build", help="merge a binding with a task template")
    build.add_argument("snapshot")
    build.add_argument("template", help="JSON with repo, agent_steps, test_command, owned_paths")
    build.add_argument("--task-id", default=None)
    build.add_argument("--plugin-root", default=None)
    build.add_argument("--out", default=None, help="write the TaskSpec JSON here")

    plan = sub.add_parser("plan", help="propose one transition with tools.xplan_dry_run")
    plan.add_argument("snapshot")
    plan.add_argument("event", help="JSON lifecycle event")
    plan.add_argument("--task-id", default=None)
    plan.add_argument("--plugin-root", default=".")

    view = sub.add_parser("receipt", help="read status/review/evidence from a frozen receipt")
    view.add_argument("receipt")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "bind":
            result = bind_issue(load_snapshot(args.snapshot), task_id=args.task_id,
                                require_dependencies_done=args.require_dependencies_done)
        elif args.cmd == "build":
            snapshot = load_snapshot(args.snapshot)
            binding = bind_issue(snapshot, task_id=args.task_id)
            template = _load(args.template)
            if not isinstance(template, dict):
                raise XPlanError("task template must be a JSON object")
            result = task_spec(binding, repo=template.pop("repo"),
                               agent_steps=template.pop("agent_steps"),
                               test_command=template.pop("test_command"),
                               owned_paths=template.pop("owned_paths"),
                               plugin_root=args.plugin_root or ".",
                               **template)
            if args.out:
                Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
                result = {"task_spec": args.out, "task_id": result["task_id"],
                          "workflow_id": binding["workflow_id"]}
        elif args.cmd == "plan":
            binding = bind_issue(load_snapshot(args.snapshot), task_id=args.task_id)
            result = propose_transition(binding, _load(args.event), args.plugin_root)
        else:
            result = status_view(_load(args.receipt))
        print(json.dumps(result, indent=2, sort_keys=True))
    except XPlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def main() -> None:
    sys.exit(_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
