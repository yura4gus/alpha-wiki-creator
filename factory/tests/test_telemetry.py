import json

import pytest

from agent_factory import telemetry


def line(**payload) -> str:
    return json.dumps(payload)


def step(part_id: str, tokens: dict | None = None, cost=0, **extra) -> str:
    body = {
        "id": part_id,
        "sessionID": "ses_test",
        "messageID": f"msg_{part_id}",
        "type": "step-finish",
        "reason": "stop",
        "tokens": tokens if tokens is not None else {},
    }
    if cost is not None:
        body["cost"] = cost
    body.update(extra)
    return line(type="step_finish", sessionID="ses_test", part=body)


def tokens(input=0, output=0, reasoning=0, cache_read=0, cache_write=0, total=None):
    value = {
        "input": input,
        "output": output,
        "reasoning": reasoning,
        "cache": {"read": cache_read, "write": cache_write},
    }
    if total is not None:
        value["total"] = total
    return value


def test_single_step_finish_matches_opencode_sample():
    text = step("prt_1", tokens(13051, 3, 0, 512, 0, total=13566), cost=0)
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["schema"] == telemetry.SCHEMA
    assert summary["source"] == "opencode-jsonl"
    assert summary["steps"] == 1
    assert summary["input_tokens"] == 13051
    assert summary["output_tokens"] == 3
    assert summary["reasoning_tokens"] == 0
    assert summary["cache_read_tokens"] == 512
    assert summary["cache_write_tokens"] == 0
    assert summary["total_tokens"] == 13566
    assert summary["cost"] == 0.0
    assert summary["missing"] == []
    assert summary["sessions"] == ["ses_test"]


def test_multiple_steps_are_summed_not_replaced():
    text = "\n".join([
        step("prt_1", tokens(100, 10, 5, 20, 2), cost=0.0012),
        step("prt_2", tokens(50, 4, 1, 0, 0), cost=0.0003),
    ])
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["steps"] == 2
    assert summary["input_tokens"] == 150
    assert summary["output_tokens"] == 14
    assert summary["reasoning_tokens"] == 6
    assert summary["cache_read_tokens"] == 20
    assert summary["cache_write_tokens"] == 2
    assert summary["total_tokens"] == 192
    assert summary["cost"] == pytest.approx(0.0015)
    assert summary["missing"] == []


def test_missing_cost_is_unavailable_not_zero():
    text = step("prt_1", tokens(10, 1, 0, 0, 0), cost=None)
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["input_tokens"] == 10
    assert summary["cost"] == telemetry.UNAVAILABLE
    assert "cost" in summary["missing"]


def test_missing_tokens_are_unavailable_not_zero():
    text = step("prt_1", tokens=None, cost=0.002)
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["cost"] == 0.002
    for field in ("input_tokens", "output_tokens", "reasoning_tokens",
                  "cache_read_tokens", "cache_write_tokens", "total_tokens"):
        assert summary[field] == telemetry.UNAVAILABLE
        assert field in summary["missing"]


def test_no_events_returns_all_unavailable():
    summary = telemetry.parse_opencode_telemetry("")
    assert summary["source"] == "unavailable"
    assert summary["steps"] == 0
    assert summary["model"] == telemetry.UNAVAILABLE
    assert set(summary["missing"]) == {
        "input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens",
        "cache_write_tokens", "total_tokens", "cost",
    }


def test_explicit_zero_is_a_value_and_is_preserved():
    text = step("prt_1", tokens(0, 0, 0, 0, 0, total=0), cost=0)
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["cost"] == 0.0
    assert summary["total_tokens"] == 0
    assert summary["missing"] == []


def test_total_is_computed_only_when_all_components_exist():
    text = step("prt_1", tokens(10, 2, 1, 3, 4), cost=0)
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["total_tokens"] == 20
    assert summary["missing"] == []
    partial = json.dumps({
        "type": "step_finish",
        "part": {"id": "prt_2", "type": "step-finish", "cost": 0,
                 "tokens": {"input": 10, "output": 2}},
    })
    incomplete = telemetry.parse_opencode_telemetry(partial)
    assert incomplete["input_tokens"] == 10
    assert incomplete["total_tokens"] == telemetry.UNAVAILABLE
    assert incomplete["reasoning_tokens"] == telemetry.UNAVAILABLE


def test_assistant_message_shape_is_supported():
    text = line(role="assistant", cost=0, modelID="deepseek-v4.1-flash",
                providerID="opencode-go", sessionID="ses_msg",
                tokens={"total": 99, "input": 90, "output": 9,
                        "reasoning": 0, "cache": {"read": 0, "write": 0}})
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["steps"] == 1
    assert summary["models"] == ["opencode-go/deepseek-v4.1-flash"]
    assert summary["total_tokens"] == 99
    assert summary["cost"] == 0.0


def test_step_events_take_precedence_over_duplicate_message_records():
    text = "\n".join([
        step("prt_1", tokens(10, 1, 0, 0, 0, total=11), cost=0.001),
        line(role="assistant", cost=99, modelID="m", providerID="p",
             tokens={"total": 999, "input": 900, "output": 99,
                     "reasoning": 0, "cache": {"read": 0, "write": 0}}),
    ])
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["steps"] == 1
    assert summary["total_tokens"] == 11
    assert summary["cost"] == 0.001


def test_duplicate_part_ids_are_counted_once():
    one = step("prt_1", tokens(10, 1, 0, 0, 0), cost=0.001)
    summary = telemetry.parse_opencode_telemetry("\n".join([one, one]))
    assert summary["steps"] == 1
    assert summary["input_tokens"] == 10


def test_partial_cache_field_makes_only_that_field_unavailable():
    first = step("prt_1", tokens(10, 1, 0, 5, 0), cost=0)
    second = json.dumps({
        "type": "step_finish",
        "part": {"id": "prt_2", "type": "step-finish", "cost": 0,
                 "tokens": {"input": 20, "output": 2, "reasoning": 0,
                            "cache": {"read": 1}}},
    })
    summary = telemetry.parse_opencode_telemetry("\n".join([first, second]))
    assert summary["input_tokens"] == 30
    assert summary["cache_read_tokens"] == 6
    assert summary["cache_write_tokens"] == telemetry.UNAVAILABLE
    assert "cache_write_tokens" in summary["missing"]


def test_noisy_log_prefix_and_ansi_are_tolerated():
    text = "\x1b[32mINFO\x1b[0m 2026-11-25 opencode " + step(
        "prt_1", tokens(5, 1, 0, 0, 0, total=6), cost=0.0001) + "\nnot json at all\n"
    summary = telemetry.parse_opencode_telemetry(text)
    assert summary["steps"] == 1
    assert summary["total_tokens"] == 6


def test_model_can_come_from_caller_when_stream_omits_it():
    text = step("prt_1", tokens(5, 1, 0, 0, 0), cost=0)
    assert telemetry.parse_opencode_telemetry(text)["model"] == telemetry.UNAVAILABLE
    summary = telemetry.parse_opencode_telemetry(
        text, model="opencode-go/deepseek-v4.1-flash")
    assert summary["model"] == "opencode-go/deepseek-v4.1-flash"
    assert summary["models"] == ["opencode-go/deepseek-v4.1-flash"]


def test_text_parts_are_recoverable_from_json_output():
    text = "\n".join([
        line(type="text", part={"type": "text", "text": '{"verdict":'}),
        line(type="text", part={"type": "text", "text": ' "APPROVE"}'}),
        line(type="step_finish", part={"type": "step-finish", "tokens": {}}),
    ])
    assert telemetry.text_from_events(text) == '{"verdict": "APPROVE"}'


def test_log_file_parser_handles_missing_and_present_files(tmp_path):
    assert telemetry.parse_opencode_log(tmp_path / "absent.log")["source"] == "unavailable"
    path = tmp_path / "step.log"
    path.write_text(step("prt_1", tokens(7, 2, 0, 0, 0), cost=0) + "\n")
    summary = telemetry.parse_opencode_log(path)
    assert summary["steps"] == 1
    assert summary["input_tokens"] == 7
