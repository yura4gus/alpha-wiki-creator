"""Offline contract tests for the remote acceptance runner.

The live gates are opt-in with both ``FACTORY_REMOTE_ACCEPTANCE=1`` and
``FACTORY_ACCEPTANCE_LIVE_TEST=1``. The default suite only exercises pure
helpers, report safety and the gate plan; no network, host or model is used.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import re
from pathlib import Path

import pytest

import acceptance_remote as ar

HERE = Path(__file__).resolve().parent
MODULE = HERE / "acceptance_remote.py"


def settings(tmp_path: Path, **changes):
    base = ar.settings_from_env(env={})
    base = dataclasses.replace(base, report_path=tmp_path / "report.json", **changes)
    return base


def test_gate_catalog_has_all_remote_gates():
    assert set(ar.DEFAULT_GATES) == {
        "preflight", "services", "resources", "task", "readback", "independence", "bsc"}
    assert set(ar.GATES) == set(ar.DEFAULT_GATES) | {"restart"}
    assert ar.GATES["restart"].destructive
    assert not ar.GATES["task"].destructive


def test_default_dry_run_never_contains_private_values(tmp_path, monkeypatch, capfd):
    secret = "unit-test-api-key-never-print"
    ssh = "private-ssh-alias-never-print"
    origin = "git@private.example:team/repo.git"
    env = {
        "TEMPORAL_API_KEY": secret,
        "FACTORY_ACCEPTANCE_REMOTE_SSH": ssh,
        "FACTORY_ACCEPTANCE_ORIGIN": origin,
        "FACTORY_ACCEPTANCE_REPORT": str(tmp_path / "report.json"),
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    code = ar.main(["--dry-run", "--gate", "services"])
    assert code == 0
    output = capfd.readouterr().out
    assert secret not in output
    assert ssh not in output
    assert origin not in output


def test_global_flag_is_required_before_connecting(monkeypatch, capfd):
    monkeypatch.delenv(ar.GLOBAL_FLAG, raising=False)
    monkeypatch.setattr(ar, "connect", _must_not_connect)
    code = ar.main(["--gate", "preflight"])
    assert code == 2
    assert "FACTORY_REMOTE_ACCEPTANCE=1" in capfd.readouterr().err


async def _must_not_connect(*_args, **_kwargs):
    raise AssertionError("connect must not be called")


def test_source_contains_no_private_host_literals():
    text = MODULE.read_text()
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)
    assert not re.search(r"tmprl\.cloud", text)


def test_redaction_covers_secrets_and_private_targets(tmp_path):
    secret = "unit-test-api-key-never-print"
    ssh = "private-ssh-alias-never-print"
    origin = "git@private.example:team/repo.git"
    env = {"TEMPORAL_API_KEY": secret, "FACTORY_ACCEPTANCE_REMOTE_SSH": ssh,
           "FACTORY_ACCEPTANCE_ORIGIN": origin,
           "TEMPORAL_ADDRESS": "private.example:7233",
           "TEMPORAL_NAMESPACE": "private-namespace"}
    cfg = ar.settings_from_env(env=env)
    text = f"{secret} {ssh} {origin} private.example:7233 private-namespace"
    redacted = ar.redact(text, cfg, env)
    for value in (secret, ssh, origin, "private.example:7233", "private-namespace"):
        assert value not in redacted
    assert redacted.count("<redacted>") == 5


def test_public_target_is_hashed_by_default():
    cfg = ar.settings_from_env(env={})
    assert ar.public_target("host.example:7233", cfg) == \
        "sha256:" + ar.fingerprint("host.example:7233")
    shown = dataclasses.replace(cfg, show_targets=True)
    assert ar.public_target("host.example:7233", shown) == "host.example:7233"


def test_service_table_parser():
    table = (
        "alpha-wiki-batch-worker.service\tactive\tenabled\t123\t204800\t1.5\t3600\n"
        "HOST\t1.25\t101000\t537000\n"
    )
    services, host = ar.parse_service_table(table, ["alpha-wiki-batch-worker.service"])
    item = services["alpha-wiki-batch-worker.service"]
    assert item == {"state": "active", "enabled": "enabled", "pid": 123,
                    "rss_kb": 204800, "cpu_percent": 1.5, "elapsed_seconds": 3600}
    assert host == {"load1": 1.25, "mem_available_mb": 101000, "disk_free_mb": 537000}


def test_service_table_parser_marks_missing_service():
    services, _ = ar.parse_service_table("", ["missing.service"])
    assert services["missing.service"]["state"] == "unknown"
    assert services["missing.service"]["pid"] is None


def test_health_json_parser():
    payload = json.dumps({
        "services": {
            "worker.service": {"state": "running", "pid": 42, "rss_kb": 1024,
                               "cpu_percent": 3, "elapsed_seconds": 10},
        },
        "host": {"load1": 0.5, "mem_available_mb": 2048, "disk_free_mb": 4096},
    })
    services, host = ar.parse_health_json(payload, ["worker.service"])
    assert services["worker.service"]["state"] == "running"
    assert services["worker.service"]["pid"] == 42
    assert host["mem_available_mb"] == 2048


def test_poller_assertions_require_minimum_and_reject_local_identity():
    snapshot = {
        "factory-code": {
            "workflow": {"count": 1, "identities": ["abc"], "raw_identities": ["42@mac.local"]},
            "activity": {"count": 1, "identities": ["def"], "raw_identities": ["42@mac.local"]},
        }
    }
    cfg = dataclasses.replace(ar.settings_from_env(env={}),
                              min_pollers=2, local_markers=("mac.local",))
    results = ar.poller_assertions(snapshot, cfg)
    by_name = {item["name"]: item for item in results}
    assert not by_name["queue_factory_code_workflow_pollers"]["pass"]
    assert not by_name["no_local_poller_identity"]["pass"]


def test_poller_identity_requirement_is_not_in_evidence():
    cfg = dataclasses.replace(ar.settings_from_env(env={}),
                              poller_requirements={"bsc-batch": "private-host-marker"})
    snapshot = {
        "bsc-batch": {
            "workflow": {"count": 1, "identities": ["abc"],
                         "raw_identities": ["9@private-host-marker"]},
            "activity": {"count": 0, "identities": [], "raw_identities": []},
        }
    }
    results = ar.poller_assertions(snapshot, cfg)
    assert all(item["pass"] for item in results)
    evidence = json.dumps(ar.safe_poller_evidence(snapshot))
    assert "private-host-marker" not in evidence


def test_bsc_read_only_evidence_is_explicit():
    ok, missing = ar.bsc_readonly_evidence(
        {"mode": "read_only", "writes": 0, "status": "PASS"},
        {"mode": "read_only", "writes": 0})
    assert ok and not missing
    ok, missing = ar.bsc_readonly_evidence(
        {"status": "PASS"}, {"mode": "read_only", "writes": 0})
    assert not ok
    assert missing == ["mode", "writes"]


def test_summarize_never_calls_blocked_a_pass():
    passed = {"gate": "a", "status": "PASS"}
    blocked = {"gate": "b", "status": "BLOCKED"}
    failed = {"gate": "c", "status": "FAIL"}
    assert ar.summarize([passed])["result"] == "PASS"
    assert ar.summarize([passed, blocked])["result"] == "BLOCKED"
    assert ar.summarize([passed, blocked, failed])["result"] == "FAIL"


def test_batch_manifest_hash_is_canonical_and_queue_scoped(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "unit.sh").write_text(ar.batch_script(5))
    (workspace / "dq.sh").write_text(ar.BATCH_RESTART_DQ)
    manifest = ar.batch_manifest(str(workspace), "job-1", "bsc-batch", 5)
    body = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    assert manifest["manifest_hash"] == ar.sha256_text(ar.canonical_json(body))
    assert manifest["script_sha"] == ar.sha256_text((workspace / "unit.sh").read_text())
    assert manifest["task_queue"] == "bsc-batch"
    assert manifest["dq_contract"]["expected_json"] == {"status": "PASS"}


def test_batch_manifest_is_a2_valid(tmp_path):
    pytest.importorskip("agent_factory.batch.manifest")
    from agent_factory.batch.manifest import compute_manifest_hash, parse_manifest
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "unit.sh").write_text(ar.batch_script(5))
    (workspace / "dq.sh").write_text(ar.BATCH_RESTART_DQ)
    manifest = ar.batch_manifest(str(workspace), "job-1", "bsc-batch", 5)
    assert manifest["manifest_hash"] == compute_manifest_hash(manifest)
    spec = parse_manifest(manifest)
    assert [unit.unit_id for unit in spec.units] == ["u0", "u1"]
    assert spec.task_queue == "bsc-batch"
    assert spec.dq_contract is not None


def test_report_writer_refuses_repository_path(tmp_path):
    cfg = settings(tmp_path)
    repo_report = Path(ar.__file__).resolve().parents[1] / "acceptance-report.json"
    with pytest.raises(ar.AcceptanceFailed):
        ar.write_report({"ok": False}, repo_report, cfg)
    assert not repo_report.exists()


def test_report_writer_is_private(tmp_path):
    cfg = settings(tmp_path)
    path = ar.write_report({"ok": True}, tmp_path / "evidence" / "report.json", cfg)
    assert path.exists()
    assert oct(path.stat().st_mode & 0o777) == "0o600"


@pytest.mark.skipif(
    os.environ.get(ar.GLOBAL_FLAG) != "1" or
    os.environ.get("FACTORY_ACCEPTANCE_LIVE_TEST") != "1",
    reason="remote acceptance is opt-in; set FACTORY_REMOTE_ACCEPTANCE=1 and "
           "FACTORY_ACCEPTANCE_LIVE_TEST=1")
def test_live_remote_acceptance(tmp_path):
    selected = ar._selected_gates(type("Args", (), {
        "all": os.environ.get("FACTORY_ACCEPTANCE_ALL") == "1",
        "gate": [os.environ.get("FACTORY_ACCEPTANCE_GATES", "")],
    })())
    cfg = ar.settings_from_env(
        repo_root=Path(__file__).resolve().parents[2])
    cfg = dataclasses.replace(cfg, report_path=tmp_path / "remote-acceptance.json")
    report = asyncio.run(ar.run_gates(cfg, selected))
    ar.write_report(report, cfg.report_path, cfg)
    ar.print_summary(report)
    assert report["result"] == "PASS", json.dumps(report["summary"], sort_keys=True)
    text = cfg.report_path.read_text()
    for name, value in os.environ.items():
        if value and len(value) >= 8 and ar.SENSITIVE_NAME.search(name):
            assert value not in text
