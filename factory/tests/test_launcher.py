import json

import pytest

from agent_factory import launcher, receipts


def task(**kw):
    base = dict(task_id="up", repo="/repo", agent_steps=[["true"]], test_command=["true"],
                owned_paths=["app"])
    base.update(kw)
    return base


def write_specs(tmp_path, *docs):
    paths = []
    for i, doc in enumerate(docs):
        path = tmp_path / f"task-{i}.json"
        path.write_text(json.dumps(doc))
        paths.append(str(path))
    return paths


def test_load_specs_accepts_one_or_many(tmp_path):
    specs = launcher.load_specs(write_specs(tmp_path, task(), [task(task_id="up2", owned_paths=["lib"])]))
    assert [s.task_id for s in specs] == ["up", "up2"]


def test_load_specs_rejects_duplicate_ids_and_overlap(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        launcher.load_specs(write_specs(tmp_path, task(), task()))
    with pytest.raises(ValueError, match="overlap"):
        launcher.load_specs(write_specs(tmp_path, task(owned_paths=["app"]),
                                        task(task_id="b", owned_paths=["app/api"])))


def test_receipt_summary_measures_step_time_and_review(tmp_path):
    receipts.record(tmp_path, "task-up", "up", "step-0", {"sha": "a" * 40}, {"seconds": 2.5})
    receipts.record(tmp_path, "task-up", "up", "tests", {"passed": True}, {"seconds": 1.5})
    receipts.record(tmp_path, "task-up", "up", "review", {"verdict": "APPROVE",
                                                          "reviewer": "opencode:m"})
    receipts.finalize(tmp_path, "task-up", "up", "PR_OPEN")
    summary = launcher._receipt_summary(receipts.receipt_path(tmp_path, "task-up"))
    assert summary["status"] == "PR_OPEN" and summary["measured_step_seconds"] == 4.0
    assert summary["review"] == "APPROVE" and summary["reviewer"] == "opencode:m"
    assert len(summary["digest"]) == 16


def test_receipt_command_reports_invalid_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FACTORY_STATE_DIR", str(tmp_path))
    receipts.record(tmp_path, "task-up", "up", "k", {"a": 1})
    receipts.finalize(tmp_path, "task-up", "up", "PR_OPEN")
    assert launcher._print_receipt(tmp_path, "up") == 0
    doc = json.loads(receipts.receipt_path(tmp_path, "task-up").read_text())
    doc["entries"]["k"] = {"a": 2}
    receipts.receipt_path(tmp_path, "task-up").write_text(json.dumps(doc))
    assert launcher._print_receipt(tmp_path, "up") == 1
    assert "digest mismatch" in capsys.readouterr().out
