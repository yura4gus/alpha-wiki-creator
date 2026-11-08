import pytest

from tools.xplan_dry_run import plan_transition


SHA = "a" * 40


@pytest.fixture
def pilot():
    issue = {"id": 47, "identifier": "H2REC-3", "updatedAt": "revision-1", "columnId": 13}
    binding = {
        "issue": issue,
        "run_id": "pilot",
        "columns": {"IN_PROGRESS": 13, "DONE": 14, "CANCELED": 15},
        "required_delivery_level": 3,
        "worker": "CI evidence worker",
    }
    event = {
        "kind": "accepted", "git_sha": SHA, "verified_delivery_level": 3,
        "review": {"verdict": "ACCEPT", "git_sha": SHA, "evidence_ref": "review.json"},
        "evidence_refs": ["tests.json"],
    }
    return binding, dict(issue), event


def test_no_change_on_repeat(pilot):
    binding, issue, event = pilot
    event["kind"] = "started"
    first = plan_transition(binding, issue, event)
    assert first["decision"] == "NO_CHANGE"
    assert first == plan_transition(binding, issue, event)
    assert first["proposed_column_id"] is None


@pytest.mark.parametrize("change", [{"updatedAt": "manual-edit"}, {"columnId": 16}])
def test_manual_override_wins(pilot, change):
    binding, issue, event = pilot
    result = plan_transition(binding, {**issue, **change}, event)
    assert result["decision"] == "SKIP_CONFLICT"
    assert result["proposed_column_id"] is None


def test_stale_review_cannot_close_new_code(pilot):
    binding, issue, event = pilot
    event["git_sha"] = "b" * 40
    result = plan_transition(binding, issue, event)
    assert result["decision"] == "STALE_SHA"
    assert result["proposed_column_id"] is None


def test_rework_routes_findings_to_bound_worker(pilot):
    binding, issue, event = pilot
    event["kind"] = "rework"
    event["review"]["findings"] = "Bind the exact protected job to the commit."
    result = plan_transition(binding, issue, event)
    assert result["decision"] == "REWORK"
    assert result["worker"] == binding["worker"]
    assert result["reason"] == event["review"]["findings"]
    assert result["proposed_column_id"] is None


def test_done_requires_same_sha_review_and_required_evidence(pilot):
    binding, issue, event = pilot
    assert plan_transition(binding, issue, {**event, "kind": "tests_passed"})["decision"] == "NO_CHANGE"
    for incomplete in ({"verified_delivery_level": 2}, {"evidence_refs": []},
                       {"review": {**event["review"], "evidence_ref": ""}}):
        assert plan_transition(binding, issue, {**event, **incomplete})["decision"] == "GATE_PENDING"
    result = plan_transition(binding, issue, event)
    assert (result["decision"], result["proposed_status"], result["proposed_column_id"], result["mode"]) == (
        "PROPOSE", "DONE", 14, "dry_run",
    )


def test_canceled_issue_requires_explicit_reopen(pilot):
    binding, issue, event = pilot
    binding["issue"] = issue = {**issue, "columnId": 15}
    assert plan_transition(binding, issue, event)["decision"] == "GATE_PENDING"
