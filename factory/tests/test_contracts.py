"""Contract boundaries: what this package may and may not touch.

These are static checks. They complement the behavioural tests: a future edit
that adds a provider SDK, an xPlan writer or a second architecture renderer
fails here even if the happy path still passes.
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "agent_factory"
PY = sorted(SRC.glob("*.py"))


def source() -> dict[str, str]:
    return {p.name: p.read_text() for p in PY}


def test_no_direct_model_provider_client():
    text = "\n".join(source().values())
    for pattern in (r"\bimport\s+(requests|httpx|aiohttp|openai|anthropic)\b",
                    r"\bfrom\s+(requests|httpx|aiohttp|openai|anthropic)\b",
                    r"api\.(openai|deepseek|anthropic)\.com",
                    r"DEEPSEEK_API_KEY"):
        assert not re.search(pattern, text), f"forbidden provider path: {pattern}"


def test_openflowkit_and_harness2_are_never_executed_here():
    text = "\n".join(source().values())
    assert "integrations.read_evidence" in source()["activities.py"]
    assert "npx" not in text.lower() and "openflowkit@" not in text.lower()
    assert "harness2.core" not in text
    assert not re.search(r"\bimport\s+harness2\b", text)


def test_xplan_is_read_only():
    text = "\n".join(source().values())
    assert "xplan_dry_run" in text
    for pattern in (r"PATCH\s+/", r"\.patch\(", r"\.put\(", r"xplan.*write"):
        assert not re.search(pattern, text, re.I), f"forbidden xPlan write path: {pattern}"


def test_one_owner_per_worktree_contract_is_enforced():
    text = source()["gitops.py"]
    assert "OwnershipViolation" in text and "owned_paths" in text
    assert "worktree" in text
    # A task's branch is derived from its id; no random or shared branch name.
    assert 'f"factory/{task_id}"' in text


def test_receipts_are_validated_before_freeze():
    text = source()["activities.py"]
    assert "receipts.validate(doc)" in text
    assert "ReceiptInvalid" in text
