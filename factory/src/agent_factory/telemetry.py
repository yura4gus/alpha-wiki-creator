"""Token and cost telemetry parsed from OpenCode's own JSON output.

OpenCode v2 emits one JSON object per line for ``opencode run --format json``.
The final ``step-finish`` part carries ``cost`` and ``tokens``; a multi-step
run emits one such part per model call. This module turns that stream into a
JSON-serialisable summary for receipts. It is deliberately a parser, not a
provider client: no HTTP request, credential or pricing table is involved.

A field that the stream does not contain is reported as ``UNAVAILABLE``. It is
never reported as zero, because zero is a real value for a free model or an
empty cache. Totals are only computed when every contributing step supplies the
component, so a partial stream cannot inflate a receipt.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "agent-factory.opencode-telemetry/1"
UNAVAILABLE = "UNAVAILABLE"

_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "total_tokens",
)
_VALUE_FIELDS = (*_TOKEN_FIELDS, "cost")


@dataclass(frozen=True)
class UsageEvent:
    """One OpenCode model call, normalised without inventing missing values."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    provider: str | None = None
    model: str | None = None
    session_id: str | None = None
    message_id: str | None = None
    part_id: str | None = None
    kind: str = "step-finish"


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def _first_present(*mappings: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for name in keys:
        for mapping in mappings:
            if name in mapping:
                return mapping[name]
    return None


def _model_name(provider: Any, model: Any) -> tuple[str | None, str | None]:
    provider_text = provider.strip() if isinstance(provider, str) and provider.strip() else None
    model_text = model.strip() if isinstance(model, str) and model.strip() else None
    return provider_text, model_text


def _event_from_mapping(obj: Mapping[str, Any]) -> UsageEvent | None:
    """Recognise the three shapes OpenCode uses for usage data."""
    part = obj.get("part") if isinstance(obj.get("part"), Mapping) else None
    event_type = str(obj.get("type") or (part or {}).get("type") or "")

    # Stream event shape: {"type":"step_finish","part":{...,"type":"step-finish"}}
    # A bare part (from a session export) is accepted through the same branch.
    step_like = event_type in {"step_finish", "step-finish"} or (
        part is not None and str(part.get("type") or "") in {"step-finish", "step_finish"})
    if step_like:
        body = part if part is not None else obj
        tokens = body.get("tokens") if isinstance(body.get("tokens"), Mapping) else None
        if tokens is None and isinstance(obj.get("tokens"), Mapping):
            tokens = obj["tokens"]
        cost = _first_present(body, obj, keys=("cost",)) if (
            "cost" in body or "cost" in obj) else None
        if tokens is None and cost is None:
            return None
        return _build_event(tokens or {}, cost, body, obj, kind="step-finish")

    # Stored assistant message shape:
    # {"role":"assistant",...,"cost":0,"tokens":{...},"modelID":...}
    if obj.get("role") == "assistant" and (
            isinstance(obj.get("tokens"), Mapping) or "cost" in obj):
        tokens = obj.get("tokens") if isinstance(obj.get("tokens"), Mapping) else {}
        cost = obj.get("cost") if "cost" in obj else None
        return _build_event(tokens, cost, obj, obj, kind="assistant-message")

    # Server event shape: {"type":"message.updated","properties":{"info":{...}}}
    properties = obj.get("properties") if isinstance(obj.get("properties"), Mapping) else None
    if properties is not None:
        info = properties.get("info") if isinstance(properties.get("info"), Mapping) else None
        if info is not None and info.get("role") == "assistant" and (
                isinstance(info.get("tokens"), Mapping) or "cost" in info):
            tokens = info.get("tokens") if isinstance(info.get("tokens"), Mapping) else {}
            cost = info.get("cost") if "cost" in info else None
            return _build_event(tokens, cost, info, obj, kind="assistant-message")
    return None


def _build_event(tokens: Mapping[str, Any], cost: Any, metadata: Mapping[str, Any],
                 outer: Mapping[str, Any], *, kind: str) -> UsageEvent:
    cache = tokens.get("cache") if isinstance(tokens.get("cache"), Mapping) else {}
    input_tokens = _integer(tokens.get("input"))
    output_tokens = _integer(tokens.get("output"))
    reasoning_tokens = _integer(tokens.get("reasoning"))
    cache_read = _integer(cache.get("read"))
    cache_write = _integer(cache.get("write"))
    total = _integer(tokens.get("total"))
    components = (input_tokens, output_tokens, reasoning_tokens, cache_read, cache_write)
    if total is None and all(value is not None for value in components):
        total = sum(value for value in components if value is not None)

    provider = _first_present(metadata, outer, keys=("providerID", "provider"))
    model = _first_present(metadata, outer, keys=("modelID", "model"))
    provider, model = _model_name(provider, model)
    session_id = _first_present(metadata, outer, keys=("sessionID", "session_id"))
    message_id = _first_present(metadata, outer, keys=("messageID", "message_id", "id"))
    part_id = _first_present(metadata, outer, keys=("partID", "part_id"))

    return UsageEvent(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        total_tokens=total,
        cost=_number(cost),
        provider=provider if isinstance(provider, str) else None,
        model=model if isinstance(model, str) else None,
        session_id=session_id if isinstance(session_id, str) else None,
        message_id=message_id if isinstance(message_id, str) else None,
        part_id=part_id if isinstance(part_id, str) else None,
        kind=kind,
    )


def _iter_json_objects(text: str):
    """Yield JSON objects embedded in JSONL or noisy log text, in order."""
    decoder = json.JSONDecoder()
    index = 0
    length = len(text)
    while index < length:
        start = text.find("{", index)
        if start < 0:
            return
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(value, dict):
            yield value
        index = end


def _dedupe(events: Iterable[UsageEvent]) -> list[UsageEvent]:
    """Keep one event per OpenCode part/message, preserving first-seen order."""
    seen: set[tuple[str, str, str]] = set()
    result: list[UsageEvent] = []
    for event in events:
        key = (event.kind, event.part_id or "", event.message_id or "")
        if key != (event.kind, "", "") and key in seen:
            continue
        seen.add(key)
        result.append(event)
    return result


def events_from_text(text: str) -> list[UsageEvent]:
    """Parse usage events from a JSONL stream or a noisy captured log."""
    step_events: list[UsageEvent] = []
    message_events: list[UsageEvent] = []
    for obj in _iter_json_objects(text):
        event = _event_from_mapping(obj)
        if event is None:
            continue
        if event.kind == "step-finish":
            step_events.append(event)
        else:
            message_events.append(event)
    # step-finish is the per-call source of truth. Message records aggregate the
    # same calls, so using both would double count.
    return _dedupe(step_events or message_events)


def _text_parts(text: str) -> list[dict[str, str]]:
    parts: list[dict[str, str]] = []
    for obj in _iter_json_objects(text):
        part = obj.get("part") if isinstance(obj.get("part"), Mapping) else obj
        if str(obj.get("type") or part.get("type") or "") != "text":
            continue
        value = part.get("text")
        if not isinstance(value, str):
            continue
        message_id = part.get("messageID") or obj.get("messageID")
        session_id = part.get("sessionID") or obj.get("sessionID")
        parts.append({
            "text": value,
            "message_id": message_id if isinstance(message_id, str) else "",
            "session_id": session_id if isinstance(session_id, str) else "",
        })
    return parts


def extract_text(text: str) -> str:
    """Recover all assistant text from ``--format json`` text parts."""
    return "".join(part["text"] for part in _text_parts(text))


def _is_verdict_json(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return False
    return isinstance(parsed, dict) and parsed.get("verdict") in {"APPROVE", "CHANGES"}


def final_text(text: str) -> str:
    """Recover the model's final answer, not an earlier draft step.

    A run can emit several assistant text parts. Prefer text that is itself a
    complete verdict object, then the last message's parts, then everything.
    """
    parts = _text_parts(text)
    if not parts:
        return ""
    joined = "".join(part["text"] for part in parts)
    if _is_verdict_json(joined):
        return joined
    message_id = parts[-1]["message_id"]
    if message_id:
        group = "".join(part["text"] for part in parts if part["message_id"] == message_id)
        if _is_verdict_json(group):
            return group
    for part in reversed(parts):
        if _is_verdict_json(part["text"]):
            return part["text"]
    if message_id:
        return "".join(part["text"] for part in parts if part["message_id"] == message_id)
    return joined


def _count_malformed_json_lines(text: str) -> int:
    count = 0
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            count += 1
    return count


def _sum_or_unavailable(events: list[UsageEvent], field: str) -> int | float | str:
    values = [getattr(event, field) for event in events]
    if not values or any(value is None for value in values):
        return UNAVAILABLE
    total = sum(value for value in values if value is not None)
    return round(float(total), 6) if field == "cost" else int(total)


def summarize_events(events: Iterable[UsageEvent], *, model: str | None = None) -> dict[str, Any]:
    """Return a receipt-safe summary; absent fields are ``UNAVAILABLE``."""
    items = list(events)
    models = {
        f"{event.provider}/{event.model}"
        for event in items
        if event.provider and event.model
    }
    if not models and model:
        models.add(model)
    sessions = {event.session_id for event in items if event.session_id}
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "source": "opencode-jsonl" if items else "unavailable",
        "steps": len(items),
        "models": sorted(models),
        "model": next(iter(models)) if len(models) == 1 else UNAVAILABLE,
        "sessions": sorted(sessions),
    }
    for field in _VALUE_FIELDS:
        summary[field] = _sum_or_unavailable(items, field)
    summary["missing"] = [
        field for field in (*(_TOKEN_FIELDS), "cost")
        if summary.get(field) == UNAVAILABLE
    ]
    return summary


def parse_opencode_telemetry(text: str, *, model: str | None = None) -> dict[str, Any]:
    """Parse OpenCode ``--format json`` output into a telemetry summary."""
    return summarize_events(events_from_text(text or ""), model=model)


def parse_run(text: str, *, model: str | None = None, wall_seconds: float | None = None,
              exit_code: int | None = None, stage: str = "run") -> dict[str, Any]:
    """Telemetry for one bounded CLI invocation.

    Adds execution facts that live outside OpenCode's token objects. A missing
    duration or exit code is ``UNAVAILABLE``; the wall clock is never inferred
    from model steps.
    """
    summary = parse_opencode_telemetry(text, model=model)
    sessions = summary.get("sessions") or []
    summary.update({
        "stage": stage,
        "exit_code": exit_code if exit_code is not None else UNAVAILABLE,
        "wall_seconds": round(float(wall_seconds), 3) if wall_seconds is not None else UNAVAILABLE,
        "duration_source": "wall" if wall_seconds is not None else UNAVAILABLE,
        "malformed_lines": _count_malformed_json_lines(text),
        "session_id": sessions[0] if len(sessions) == 1 else UNAVAILABLE,
    })
    return summary


def parse_opencode_log(path: str | Path, *, model: str | None = None) -> dict[str, Any]:
    """Parse a captured OpenCode log file, tolerating non-JSON noise."""
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        text = ""
    return parse_opencode_telemetry(text, model=model)


def model_from_argv(argv: Iterable[str]) -> str:
    """Read `-m/--model` from a step argv without executing or importing it."""
    args = list(argv)
    for index, arg in enumerate(args):
        if arg in ("-m", "--model") and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--model=") and len(arg) > len("--model="):
            return arg.split("=", 1)[1]
    return UNAVAILABLE


def is_opencode(argv: Iterable[str]) -> bool:
    """True when argv starts an OpenCode CLI process."""
    args = list(argv)
    return bool(args) and Path(str(args[0])).name.lower().startswith("opencode")


# Short aliases used by callers that do not care about the OpenCode detail.
summarize = parse_opencode_telemetry
summarize_log = parse_opencode_log
text_from_events = extract_text
