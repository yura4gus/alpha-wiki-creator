"""Review telemetry: JSON mode is opt-in and never changes the fail-closed verdict."""

from __future__ import annotations

import json

from agent_factory import reviewer, telemetry


def fake(tmp_path, events: list[dict], exit_code: int = 0, name: str = "fake-opencode") -> str:
    path = tmp_path / name
    body = "#!/usr/bin/env python3\nimport json, sys\n"
    body += f"events = {events!r}\n"
    body += "for event in events:\n    print(json.dumps(event))\n"
    body += f"sys.exit({exit_code})\n"
    path.write_text(body)
    path.chmod(0o755)
    return str(path)


def approve_event(text: str = '{"verdict": "APPROVE", "findings": "scoped and tested"}') -> dict:
    return {"type": "text", "timestamp": 1000, "sessionID": "ses_fake",
            "part": {"type": "text", "text": text}}


def finish_event(cost=0.001, input_tokens=123, output_tokens=7) -> dict:
    return {"type": "step_finish", "timestamp": 2000, "sessionID": "ses_fake",
            "part": {"type": "step-finish", "reason": "stop", "cost": cost,
                     "tokens": {"input": input_tokens, "output": output_tokens,
                                "reasoning": 0, "cache": {"read": 0, "write": 0}}}}


def review(monkeypatch, binary: str, telemetry_out: dict | None) -> dict:
    monkeypatch.setenv("FACTORY_OPENCODE_BIN", binary)
    return reviewer.opencode_review("test/model", "ctx", "passed=True", "diff --git a/x b/x",
                                    "a" * 40, timeout=10, telemetry_out=telemetry_out)


def test_json_mode_populates_telemetry_and_parses_text_event(tmp_path, monkeypatch):
    binary = fake(tmp_path, [approve_event(), finish_event()])
    captured: dict = {}
    result = review(monkeypatch, binary, captured)
    assert result["verdict"] == "APPROVE"
    assert result["findings"] == "scoped and tested"
    assert captured["steps"] == 1
    assert captured["cost"] == 0.001
    assert captured["input_tokens"] == 123
    assert captured["output_tokens"] == 7
    assert captured["reasoning_tokens"] == 0
    assert captured["cache_read_tokens"] == 0
    assert captured["model"] == "test/model"
    assert captured["stage"] == "review"
    assert captured["exit_code"] == 0
    assert captured["duration_source"] == "wall"
    assert captured["malformed_lines"] == 0
    assert captured["session_id"] == "ses_fake"


def test_plain_output_still_parses_without_telemetry(tmp_path, monkeypatch):
    path = tmp_path / "plain-opencode"
    path.write_text('#!/bin/sh\nprintf \'%s\\n\' \'{"verdict": "CHANGES", "findings": "needs work"}\'\n')
    path.chmod(0o755)
    result = review(monkeypatch, str(path), None)
    assert result["verdict"] == "CHANGES"
    assert result["findings"] == "needs work"


def test_nonzero_exit_blocks_but_keeps_reported_telemetry(tmp_path, monkeypatch):
    binary = fake(tmp_path, [approve_event(), finish_event()], exit_code=3)
    captured: dict = {}
    result = review(monkeypatch, binary, captured)
    assert result["verdict"] == "BLOCKED"
    assert result["findings"].startswith("review failed:")
    assert captured["exit_code"] == 3
    assert captured["cost"] == 0.001


def test_missing_telemetry_fields_are_unavailable(tmp_path, monkeypatch):
    binary = fake(tmp_path, [approve_event()])
    captured: dict = {}
    result = review(monkeypatch, binary, captured)
    assert result["verdict"] == "APPROVE"
    assert captured["steps"] == 0
    assert captured["cost"] == telemetry.UNAVAILABLE
    assert captured["input_tokens"] == telemetry.UNAVAILABLE


def test_final_text_json_is_preferred_over_earlier_text(tmp_path, monkeypatch):
    binary = fake(tmp_path, [
        approve_event('{"verdict": "CHANGES", "findings": "draft"}'),
        approve_event('{"verdict": "APPROVE", "findings": "final"}'),
        finish_event(),
    ])
    result = review(monkeypatch, binary, {})
    assert result["verdict"] == "APPROVE"
    assert result["findings"] == "final"


def test_reviewer_sets_pwd_to_its_scratch_directory(tmp_path, monkeypatch):
    """A shared OpenCode service resolves the session directory from PWD."""
    marker = tmp_path / "pwd.txt"
    path = tmp_path / "pwd-opencode"
    path.write_text(
        "#!/bin/sh\n"
        f"printf '%s' \"$PWD\" > {marker}\n"
        'cat <<\'EOF\'\n'
        '{"verdict": "CHANGES", "findings": "pwd checked"}\n'
        "EOF\n")
    path.chmod(0o755)
    result = review(monkeypatch, str(path), None)
    assert result["verdict"] == "CHANGES"
    observed = marker.read_text()
    assert "factory-review-" in observed
    assert str(tmp_path) not in observed


def test_step_model_detection_helpers():
    assert telemetry.model_from_argv(
        ["opencode", "run", "--auto", "-m", "opencode-go/deepseek-v4.1-flash", "go"]) \
        == "opencode-go/deepseek-v4.1-flash"
    assert telemetry.model_from_argv(["opencode", "--model=x/y", "go"]) == "x/y"
    assert telemetry.model_from_argv(["opencode", "run", "go"]) == telemetry.UNAVAILABLE
    assert telemetry.is_opencode(["/usr/local/bin/opencode", "run"])
    assert not telemetry.is_opencode(["python3", "tests/fake_agent.py"])
