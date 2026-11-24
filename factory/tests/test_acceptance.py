"""Acceptance gate tests: missing evidence blocks, contradictions fail."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import pytest

from agent_factory import acceptance

NOW = datetime(2026, 11, 24, 21, 0, tzinfo=timezone.utc)
TS = "2026-11-24T20:50:00Z"
A40 = "a" * 40
C40 = "c" * 40
B64 = "b" * 64
D64 = "d" * 64
E64 = "e" * 64


def envelope(checks: dict | None = None) -> dict:
    return {
        "schema": acceptance.SCHEMA,
        "generated_at": TS,
        "commit": A40,
        "environment": "remote",
        "checks": checks or {},
    }


def queue(count: int = 1) -> dict:
    return {
        "workflow": {"poller_count": count, "identities": [f"worker-{count}"]},
        "activity": {"poller_count": count, "identities": [f"worker-{count}"]},
    }


def full_bundle() -> dict:
    """A complete, internally consistent evidence bundle."""
    checks = {
        "RAILWAY_FACTORY_DEPLOYED": {
            "project_id": "project",
            "environment_id": "environment",
            "services": {"factory": "service-1", "harness": "service-2"},
            "deployment": {"id": "deployment-1", "sha": A40, "status": "SUCCESS"},
            "health": {"status": "PASS", "checked_at": TS},
            "git_sha": A40,
            "public_exposure": False,
            "access": "railway-private",
        },
        "RAILWAY_OPENCODE_READY": {
            "instances": [{"id": "opencode-1", "placement": "railway", "status": "ready"}],
            "auth": {"provider": "opencode-go", "model": "opencode-go/paid-model",
                     "authenticated": True},
            "access": {"public_domain": False, "method": "railway-private"},
            "health": {"status": "PASS", "checked_at": TS},
        },
        "TEMPORAL_POLLERS_ACTIVE": {
            "target": "alpha-dev",
            "namespace": "alpha-dev",
            "observed_at": TS,
            "queues": {
                "factory-code": queue(),
                "factory-coordinator": queue(),
                "bsc-batch": queue(),
            },
            "placement": {
                "factory-code": "railway",
                "factory-coordinator": "railway",
                "bsc-batch": "external-compute",
            },
        },
        "ITSPLAN_TASK_BINDING_PASS": {
            "issue": {"id": 47, "identifier": "BSC-29", "updatedAt": "revision-1",
                      "columnId": 13, "source_revision": "revision-1",
                      "observed_revision": "revision-1"},
            "binding": {
                "issue": {"id": 47, "identifier": "BSC-29"},
                "run_id": "pilot-1",
                "worker": "external-compute",
                "columns": {"IN_PROGRESS": 13, "DONE": 14, "CANCELED": 15},
                "required_delivery_level": 3,
            },
            "planner": {"decision": "NO_CHANGE", "mode": "dry_run",
                        "proposed_column_id": None},
            "write_audit": {"writes_attempted": 0, "writes_applied": 0,
                            "methods": ["GET"], "paths": []},
            "replay": {"identical": True, "decision": "NO_CHANGE"},
        },
        "REMOTE_CODING_E2E_PASS": {
            "task_id": "fix-calc",
            "workflow_id": "task-fix-calc",
            "workflow_status": "PR_OPEN",
            "execution": {"placement": "railway", "local_process": False},
            "agent": {"runner": "opencode", "model": "opencode-go/paid-model",
                      "steps": 2, "session_id": "ses-impl"},
            "tests": {"passed": True, "command": ["python3", "-m", "unittest"]},
            "review": {"verdict": "APPROVE", "independent": True,
                       "session_id": "ses-review", "model": "opencode-go/paid-model",
                       "diff_sha256": B64, "prompt_sha256": B64},
            "checkpoints": [{"index": 0, "sha": A40}, {"index": 1, "sha": C40}],
            "pr": {"number": 12, "head_sha": C40, "branch": "factory/fix-calc"},
            "receipt": {"path": "receipts/task-fix-calc.json", "sha256": D64},
            "duplicates": {"commits": 0, "prs": 0},
        },
        "EXTERNAL_BATCH_WORKER_PASS": {
            "job_id": "bsc-job",
            "workflow_id": "batch-bsc-job",
            "task_queue": "bsc-batch",
            "status": "BATCH_SUCCESS",
            "worker": {"placement": "external-compute", "identity": "external-1",
                       "railway_service_id": None, "host_class": "external"},
            "units": [{"unit_id": "unit-1", "status": "COMPLETED", "exit_code": 0,
                       "outputs": {"out.json": E64}}],
            "data_plane": {"bulk_data_on_railway": False, "railway_bytes": 0,
                           "durable_state_placement": "external"},
            "receipt": {"path": "receipts/batch-bsc-job.json", "sha256": D64},
        },
        "RESTART_RECOVERY_PASS": {
            "railway_restart": {"service_id": "service-1", "restart_count": 1,
                                "observed_at": TS},
            "external_restart": {"worker_identity": "external-1", "restart_count": 1,
                                 "observed_at": TS},
            "recovery": {"resumed": True, "replay": "PASS",
                         "terminal_state": "PR_OPEN", "checkpoints_reused": 1},
            "duplicates": {"commits": 0, "prs": 0, "batch_units": 0, "side_effects": 0},
            "continuity": {"before_sha": A40, "after_sha": A40},
        },
        "MAC_INDEPENDENCE_PASS": {
            "local": {
                "stopped_at": TS,
                "processes": [{"name": "temporal", "running_after": False},
                              {"name": "opencode", "running_after": False}],
                "ports": [{"port": 7233, "listening_after": False},
                          {"port": 8000, "listening_after": False}],
                "remote_tunnels_required": False,
            },
            "remote": {"continued": True, "observed_after_local_stop": True,
                       "workflow_id": "task-fix-calc", "terminal_state": "PR_OPEN"},
        },
        "REMOTE_FACTORY_READY": {
            "release_sha": A40,
            "services": {
                "factory_worker": {"status": "online", "queue": "factory-code"},
                "coordinator": {"status": "online", "queue": "factory-coordinator"},
                "console": {"status": "online", "private": True},
            },
            "state": {"durable": True, "receipts_readable": True},
        },
        "REMOTE_OPENCODE_PASS": {
            "instance": {"id": "opencode-1", "placement": "railway"},
            "auth": {"authenticated": True, "model": "opencode-go/paid-model"},
            "real_call": {"exit_code": 0, "session_id": "ses-remote",
                          "text_sha256": B64},
            "access": {"public_domain": False},
        },
        "DETERMINISTIC_BATCH_PASS": {
            "job_id": "bsc-job",
            "manifest_hash": B64,
            "script_sha": B64,
            "runs": [
                {"checkpoint_digest": D64, "outputs": {"out.json": E64}},
                {"checkpoint_digest": D64, "outputs": {"out.json": E64}},
            ],
            "checkpoint_fields": ["schema", "job_id", "unit_id", "outputs", "status"],
            "deterministic": True,
        },
        "BSC_0029_CANARY_PASS": {
            "job_id": "bsc-0029",
            "status": "BATCH_SUCCESS",
            "worker": {"placement": "external-compute"},
            "dq": {"status": "PASS"},
            "outputs": {"canary.json": E64},
            "receipt": {"sha256": D64},
            "canary": True,
        },
        "CHECKPOINT_RESUME_PASS": {
            "job_id": "bsc-job",
            "unit_id": "unit-1",
            "killed": True,
            "worker_restart": {"observed": True},
            "resume": {"checkpoint_reused": True, "unit_rerun": False,
                       "outputs_match": True},
            "counts": {"unit_executions": 1, "checkpoint_writes": 1},
            "receipt": {"sha256": D64},
        },
        "DQ_READBACK_PASS": {
            "job_id": "bsc-job",
            "dq": {"status": "PASS", "exit_code": 0, "expected_exit": 0,
                   "report_sha256": B64, "expected_json": {"rows": 3},
                   "reported_json": {"rows": 3}},
            "readback": {"independent": True, "matches_expected": True,
                         "report_hash_matches": True},
        },
        "ZERO_DUPLICATE_EFFECTS": {
            "counts": {"commits": 0, "prs": 0, "branches": 0, "batch_units": 0,
                       "dq_reports": 0, "receipts": 0, "notifications": 0},
            "scope": ["coding", "batch", "restart"],
            "evidence": {"coding": "receipts/task-fix-calc.json",
                         "batch": "receipts/batch-bsc-job.json",
                         "restart": "receipts/restart.json"},
            "independent": True,
        },
        "TELEMETRY_VERIFIED": {
            "schema": "agent-factory.opencode-telemetry/1",
            "source": "opencode-run-json",
            "runs": [
                {"stage": "agent", "model": "opencode-go/paid-model",
                 "session_id": "ses-impl", "steps": 2, "cost": 0.01,
                 "input_tokens": 100, "output_tokens": 20,
                 "duration_seconds": 1.25, "exit_code": 0, "text_sha256": B64},
                {"stage": "review", "model": "opencode-go/paid-model",
                 "session_id": "ses-review", "steps": 1, "cost": 0.02,
                 "input_tokens": 50, "output_tokens": 10,
                 "duration_seconds": 0.75, "exit_code": 0, "text_sha256": B64},
            ],
            "receipt": {"contains_telemetry": True, "metrics_sha256": D64},
        },
    }
    return envelope(checks)


def test_complete_bundle_passes():
    report = acceptance.evaluate(full_bundle(), now=NOW, verify_artifacts=False)
    assert report["overall"] == acceptance.PASS
    assert report["passed"] == report["total"] == 16


def test_empty_bundle_blocks_every_gate():
    report = acceptance.evaluate(envelope(), now=NOW, verify_artifacts=False)
    assert report["overall"] == acceptance.BLOCKED
    assert report["passed"] == 0
    assert all(gate["status"] == acceptance.BLOCKED
               for gate in report["gates"].values())


def test_deployment_sha_must_match_tested_commit():
    bundle = full_bundle()
    bundle["checks"]["RAILWAY_FACTORY_DEPLOYED"]["deployment"]["sha"] = C40
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["RAILWAY_FACTORY_DEPLOYED"]["status"] == acceptance.FAIL
    assert "git_sha" in report["gates"]["RAILWAY_FACTORY_DEPLOYED"]["reasons"][0]


def test_dependency_blocks_even_when_own_evidence_looks_complete():
    bundle = full_bundle()
    del bundle["checks"]["RAILWAY_FACTORY_DEPLOYED"]
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["RAILWAY_OPENCODE_READY"]["status"] == acceptance.BLOCKED
    assert "prerequisite" in report["gates"]["RAILWAY_OPENCODE_READY"]["reasons"][0]


def test_all_zero_pollers_is_blocked_and_partial_is_failed():
    bundle = full_bundle()
    bundle["checks"]["TEMPORAL_POLLERS_ACTIVE"]["queues"] = {
        "factory-code": queue(0),
        "factory-coordinator": queue(0),
        "bsc-batch": queue(0),
    }
    blocked = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert blocked["gates"]["TEMPORAL_POLLERS_ACTIVE"]["status"] == acceptance.BLOCKED

    bundle["checks"]["TEMPORAL_POLLERS_ACTIVE"]["queues"]["factory-code"] = queue(1)
    failed = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = failed["gates"]["TEMPORAL_POLLERS_ACTIVE"]
    assert gate["status"] == acceptance.FAIL
    assert "without pollers" in gate["reasons"][0]


def test_stale_observation_is_blocked():
    bundle = full_bundle()
    bundle["checks"]["TEMPORAL_POLLERS_ACTIVE"]["observed_at"] = "2026-11-20T00:00:00Z"
    report = acceptance.evaluate(bundle, now=NOW, max_age_hours=1,
                                 verify_artifacts=False)
    assert report["gates"]["TEMPORAL_POLLERS_ACTIVE"]["status"] == acceptance.BLOCKED
    assert "older than" in report["gates"]["TEMPORAL_POLLERS_ACTIVE"]["reasons"][0]


def test_xplan_write_or_non_read_method_fails_the_binding():
    bundle = full_bundle()
    bundle["checks"]["ITSPLAN_TASK_BINDING_PASS"]["write_audit"]["writes_attempted"] = 1
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = report["gates"]["ITSPLAN_TASK_BINDING_PASS"]
    assert gate["status"] == acceptance.FAIL
    assert "mutation" in gate["reasons"][0]

    bundle = full_bundle()
    bundle["checks"]["ITSPLAN_TASK_BINDING_PASS"]["write_audit"]["methods"] = ["PATCH"]
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["ITSPLAN_TASK_BINDING_PASS"]["status"] == acceptance.FAIL


def test_review_must_be_independent():
    bundle = full_bundle()
    review = bundle["checks"]["REMOTE_CODING_E2E_PASS"]["review"]
    review["session_id"] = "ses-impl"
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = report["gates"]["REMOTE_CODING_E2E_PASS"]
    assert gate["status"] == acceptance.FAIL
    assert "implementation session" in gate["reasons"][0]


def test_batch_worker_must_not_be_on_railway():
    bundle = full_bundle()
    worker = bundle["checks"]["EXTERNAL_BATCH_WORKER_PASS"]["worker"]
    worker["placement"] = "railway"
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["EXTERNAL_BATCH_WORKER_PASS"]["status"] == acceptance.FAIL

    worker["placement"] = "external-compute"
    worker["railway_service_id"] = "service-1"
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["EXTERNAL_BATCH_WORKER_PASS"]["status"] == acceptance.FAIL


def test_bulk_batch_data_on_railway_fails():
    bundle = full_bundle()
    bundle["checks"]["EXTERNAL_BATCH_WORKER_PASS"]["data_plane"]["railway_bytes"] = 2_000_000
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = report["gates"]["EXTERNAL_BATCH_WORKER_PASS"]
    assert gate["status"] == acceptance.FAIL
    assert "1 MiB" in gate["reasons"][0]


def test_restart_duplicates_fail_and_mac_process_must_stop():
    bundle = full_bundle()
    bundle["checks"]["RESTART_RECOVERY_PASS"]["duplicates"]["commits"] = 1
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["RESTART_RECOVERY_PASS"]["status"] == acceptance.FAIL

    bundle = full_bundle()
    bundle["checks"]["MAC_INDEPENDENCE_PASS"]["local"]["processes"][0][
        "running_after"] = True
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["MAC_INDEPENDENCE_PASS"]["status"] == acceptance.FAIL


def test_bsc_canary_must_be_the_named_job():
    bundle = full_bundle()
    bundle["checks"]["BSC_0029_CANARY_PASS"]["job_id"] = "bsc-0030"
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = report["gates"]["BSC_0029_CANARY_PASS"]
    assert gate["status"] == acceptance.FAIL
    assert "BSC-0029" in gate["reasons"][0]


def test_telemetry_requires_both_agent_and_review_stages():
    bundle = full_bundle()
    bundle["checks"]["TELEMETRY_VERIFIED"]["runs"] = [
        run for run in bundle["checks"]["TELEMETRY_VERIFIED"]["runs"]
        if run["stage"] == "review"
    ]
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    gate = report["gates"]["TELEMETRY_VERIFIED"]
    assert gate["status"] == acceptance.FAIL
    assert "agent-step" in gate["reasons"][0]


def test_telemetry_unavailable_is_not_zero():
    bundle = full_bundle()
    bundle["checks"]["TELEMETRY_VERIFIED"]["runs"][0]["cost"] = "UNAVAILABLE"
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["TELEMETRY_VERIFIED"]["status"] == acceptance.FAIL


def test_dq_readback_must_match_expected_and_hash():
    bundle = full_bundle()
    bundle["checks"]["DQ_READBACK_PASS"]["dq"]["reported_json"] = {"rows": 4}
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["DQ_READBACK_PASS"]["status"] == acceptance.FAIL

    bundle = full_bundle()
    bundle["checks"]["DQ_READBACK_PASS"]["readback"]["independent"] = False
    report = acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)
    assert report["gates"]["DQ_READBACK_PASS"]["status"] == acceptance.FAIL


def test_artifact_hash_mismatch_blocks_the_gate(tmp_path):
    artifact = tmp_path / "railway.json"
    artifact.write_text('{"deployment": "ok"}\n')
    bundle = full_bundle()
    bundle["artifacts"] = [{"id": "railway", "path": "railway.json", "sha256": B64}]
    bundle["checks"]["RAILWAY_FACTORY_DEPLOYED"]["artifacts"] = ["railway"]
    report = acceptance.evaluate(bundle, now=NOW, bundle_dir=tmp_path)
    assert report["gates"]["RAILWAY_FACTORY_DEPLOYED"]["status"] == acceptance.BLOCKED
    assert "sha256 mismatch" in report["gates"]["RAILWAY_FACTORY_DEPLOYED"][
        "reasons"][0]


def test_artifact_absence_blocks_and_correct_hash_verifies(tmp_path):
    artifact = tmp_path / "railway.json"
    artifact.write_text('{"deployment": "ok"}\n')
    import hashlib
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    bundle = full_bundle()
    bundle["artifacts"] = [{"id": "railway", "path": "railway.json", "sha256": digest}]
    bundle["checks"]["RAILWAY_FACTORY_DEPLOYED"]["artifacts"] = ["railway"]
    report = acceptance.evaluate(bundle, now=NOW, bundle_dir=tmp_path)
    assert report["gates"]["RAILWAY_FACTORY_DEPLOYED"]["status"] == acceptance.PASS

    bundle["checks"]["RAILWAY_FACTORY_DEPLOYED"]["artifacts"] = ["absent"]
    report = acceptance.evaluate(bundle, now=NOW, bundle_dir=tmp_path)
    assert report["gates"]["RAILWAY_FACTORY_DEPLOYED"]["status"] == acceptance.BLOCKED


def test_secret_shaped_evidence_is_rejected():
    bundle = full_bundle()
    bundle["checks"]["RAILWAY_OPENCODE_READY"]["auth"]["api_key"] = "sk-live-1234567890"
    with pytest.raises(ValueError, match="secret-shaped"):
        acceptance.evaluate(bundle, now=NOW, verify_artifacts=False)


def test_invalid_envelope_is_rejected():
    with pytest.raises(ValueError, match="schema"):
        acceptance.evaluate({"schema": "wrong", "generated_at": TS,
                             "checks": {}}, now=NOW)
    with pytest.raises(ValueError, match="generated_at"):
        acceptance.evaluate({"schema": acceptance.SCHEMA, "generated_at": "not-time",
                             "checks": {}}, now=NOW)


def test_report_markdown_lists_all_gates():
    report = acceptance.evaluate(full_bundle(), now=NOW, verify_artifacts=False)
    text = acceptance.report_markdown(report)
    for gate in acceptance.GATES:
        assert f"`{gate.id}`" in text


def test_cli_returns_zero_for_pass_and_two_for_blocked(tmp_path, capsys):
    pass_path = tmp_path / "pass.json"
    pass_path.write_text(json.dumps(full_bundle()))
    assert acceptance.main(["--bundle", str(pass_path), "--format", "json",
                            "--no-artifacts"]) == 0

    blocked = envelope()
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text(json.dumps(blocked))
    assert acceptance.main(["--bundle", str(blocked_path)]) == 2
    assert "BLOCKED" in capsys.readouterr().out


def test_gate_order_is_stable_and_unique():
    ids = [gate.id for gate in acceptance.GATES]
    assert len(ids) == len(set(ids)) == 16
    assert ids[0] == "RAILWAY_FACTORY_DEPLOYED"
    assert ids[-1] == "TELEMETRY_VERIFIED"
