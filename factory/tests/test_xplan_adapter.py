"""Read-only ITSPlan adapter tests: binding, admission guard, planner reuse."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agent_factory import xplan

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40


def snapshot(**overrides) -> dict:
    doc = {
        "schema": xplan.SNAPSHOT_SCHEMA,
        "project": {"id": 7, "name": "RateX", "revision": "project-rev-1"},
        "issue": {
            "id": 42,
            "identifier": "RATEX-42",
            "title": "Fix the calculator",
            "description": "Make add() return a sum and keep ownership under app/.",
            "columnId": 1,
            "updatedAt": "2026-11-24T12:00:00Z",
            "dependencies": [{"identifier": "RATEX-40", "status": "DONE"}],
            "required_delivery_level": 3,
            "worker": "opencode",
        },
        "columns": {"TODO": 1, "IN_PROGRESS": 2, "DONE": 3, "REWORK": 4},
        "run_id": "pilot-1",
        "approved_by": "owner",
    }
    doc.update(overrides)
    return doc


def test_bind_maps_issue_to_workflow_id():
    bound = xplan.bind_issue(snapshot())
    assert bound["task_id"] == "ratex-42"
    assert bound["workflow_id"] == "task-ratex-42"
    assert bound["binding"]["issue"]["identifier"] == "RATEX-42"
    assert bound["binding"]["columns"]["DONE"] == 3
    assert bound["requirements"]["revision"] == "2026-11-24T12:00:00Z"


def test_bind_rejects_open_dependencies_and_missing_fields():
    doc = snapshot()
    doc["issue"]["dependencies"] = [{"identifier": "RATEX-40", "status": "IN_PROGRESS"}]
    with pytest.raises(xplan.XPlanConflict, match="RATEX-40"):
        xplan.bind_issue(doc, require_dependencies_done=True)

    doc = snapshot()
    del doc["issue"]["updatedAt"]
    with pytest.raises(xplan.XPlanError, match="updatedAt"):
        xplan.bind_issue(doc)


def test_task_spec_requires_approval_and_carries_binding():
    bound = xplan.bind_issue(snapshot())
    spec = xplan.task_spec(bound, repo="/data/seed/origin.git",
                           agent_steps=[["opencode", "run", "--auto", "fix"]],
                           test_command=["python3", "-m", "unittest"],
                           owned_paths=["app"], plugin_root="/app")
    assert spec["task_id"] == "ratex-42"
    assert spec["xplan"]["binding"]["run_id"] == "pilot-1"
    assert spec["plugin_root"] == "/app"

    unapproved = copy.deepcopy(bound)
    unapproved["approved_by"] = None
    with pytest.raises(xplan.XPlanConflict, match="approved_by"):
        xplan.task_spec(unapproved, repo="/data/seed/origin.git",
                        agent_steps=[["opencode", "run", "fix"]],
                        test_command=["python3", "-m", "unittest"],
                        owned_paths=["app"])


def test_planner_reuse_proposes_without_writing():
    bound = xplan.bind_issue(snapshot())
    started = xplan.propose_transition(
        bound, {"kind": "started", "git_sha": SHA, "evidence_refs": ["receipt:task-ratex-42"]},
        ROOT)
    assert started["decision"] == "PROPOSE"
    assert started["proposed_status"] == "IN_PROGRESS"
    assert started["proposed_column_id"] == 2
    assert started["mode"] == "dry_run"
    assert started["task_id"] == "ratex-42"

    accepted = xplan.propose_transition(
        bound,
        {"kind": "accepted", "git_sha": SHA, "evidence_refs": ["receipt:task-ratex-42"],
         "verified_delivery_level": 3,
         "review": {"git_sha": SHA, "verdict": "ACCEPT", "evidence_ref": "receipt:task-ratex-42"}},
        ROOT)
    assert accepted["decision"] == "PROPOSE"
    assert accepted["proposed_status"] == "DONE"

    pending = xplan.propose_transition(
        bound,
        {"kind": "accepted", "git_sha": SHA, "evidence_refs": [],
         "verified_delivery_level": 3,
         "review": {"git_sha": SHA, "verdict": "ACCEPT"}},
        ROOT)
    assert pending["decision"] == "GATE_PENDING"


def test_planner_reports_conflict_and_needs_owner():
    bound = xplan.bind_issue(snapshot())
    changed = copy.deepcopy(bound)
    changed["observed"]["updatedAt"] = "2026-11-24T13:00:00Z"
    conflict = xplan.propose_transition(changed, {"kind": "started", "git_sha": SHA,
                                                  "evidence_refs": ["r"]}, ROOT)
    assert conflict["decision"] == "SKIP_CONFLICT"

    owner = xplan.propose_transition(bound, {"kind": "needs_owner", "git_sha": SHA,
                                             "evidence_refs": ["r"],
                                             "question": "Which repo owns app/?"}, ROOT)
    assert owner["decision"] == "NEEDS_OWNER"
    assert owner["proposed_status"] == "NEEDS_OWNER"


def test_status_view_reads_only_durable_fields():
    receipt = {
        "workflow_id": "task-ratex-42",
        "task_id": "ratex-42",
        "status": "PR_OPEN",
        "digest": "digest",
        "entries": {
            "pinned": {"base_sha": "b" * 40},
            "step-0": {"sha": SHA},
            "review": {"verdict": "APPROVE", "reviewer": "opencode:model", "findings": "ok"},
            "evidence": {"status": "PASS", "sources": [{"path": "AGENTS.md"}], "note": ""},
            "xplan_dry_run": {"decision": "NO_CHANGE", "mode": "dry_run"},
            "approval": {"verdict": "approve", "by": "owner"},
        },
    }
    view = xplan.status_view(receipt)
    assert view["head_sha"] == SHA
    assert view["review"]["verdict"] == "APPROVE"
    assert view["evidence"]["status"] == "PASS"
    assert view["xplan_dry_run"]["mode"] == "dry_run"
    assert view["mode"] == "read_only"


def test_task_id_is_branch_safe():
    assert xplan.task_id_for("RATEX-42 / hotfix") == "ratex-42-hotfix"
    with pytest.raises(xplan.XPlanError):
        xplan.task_id_for("///")
