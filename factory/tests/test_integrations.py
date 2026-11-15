import hashlib
import json

from agent_factory import integrations
from agent_factory.models import TaskSpec


def spec(root=None, **kw):
    base = dict(task_id="t", repo="r", agent_steps=[["true"]], test_command=["true"],
                owned_paths=["app"], plugin_root=str(root) if root else None)
    base.update(kw)
    return TaskSpec(**base)


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


def harness(result="PASS", **kw):
    return {"profile": "alpha-wiki", "executor": "deterministic", "result": result,
            "engine_receipt": "runs/x/summary.json",
            "cases": {"train": {"candidate_pass": result == "PASS"}}, **kw}


def openflow(result="PASS", **kw):
    return {"kind": "repo-observed", "result": result, "tool": "openflowkit 0.3.0",
            "source": {"sha": "a" * 40}, "model_sha256": "b" * 64, **kw}


def test_no_evidence_is_missing_not_a_failure(tmp_path):
    got = integrations.read_evidence(spec(tmp_path))
    assert got.status == "MISSING" and got.refs == [] and "not a failure" not in got.note


def test_passing_receipts_are_bound_by_hash(tmp_path):
    h = write(tmp_path / "h2.json", harness())
    o = write(tmp_path / "ofk.json", openflow())
    got = integrations.read_evidence(spec(tmp_path, harness2_evaluation="h2.json",
                                         openflowkit_report="ofk.json"))
    assert got.status == "PASS" and len(got.sources) == 2
    assert got.sources[0]["sha256"] == hashlib.sha256(h.read_bytes()).hexdigest()
    assert got.sources[1]["sha"] == "a" * 40
    assert got.sources[1]["model_sha256"] == "b" * 64
    assert all(ref.endswith(got.sources[i]["sha256"][:16]) for i, ref in enumerate(got.refs))


def test_drift_and_unknown_are_reported_without_blocking_the_factory(tmp_path):
    write(tmp_path / "h2.json", harness("DRIFT"))
    write(tmp_path / "ofk.json", openflow("UNKNOWN"))
    got = integrations.read_evidence(spec(tmp_path, harness2_evaluation="h2.json",
                                         openflowkit_report="ofk.json"))
    assert got.status == "DRIFT" and "openflowkit: UNKNOWN" in got.note and len(got.refs) == 2


def test_bad_receipts_are_invalid_not_trusted(tmp_path):
    write(tmp_path / "h2.json", {"result": "PASS"})
    write(tmp_path / "ofk.json", openflow(source={}))
    got = integrations.read_evidence(spec(tmp_path, harness2_evaluation="h2.json",
                                         openflowkit_report="ofk.json"))
    assert got.status == "INVALID" and len(got.sources) == 2
    assert all(s["reason"] for s in got.sources)


def test_missing_optional_path_is_reported(tmp_path):
    got = integrations.read_evidence(spec(tmp_path, harness2_evaluation="absent.json"))
    assert got.status == "MISSING" and "missing absent.json" in got.note


def test_boundaries_name_each_authority():
    assert set(integrations.BOUNDARIES) == {
        "execution", "models", "context", "task_state", "quality", "architecture", "delivery"}
    assert "read-only" in integrations.BOUNDARIES["task_state"]
