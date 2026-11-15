"""Live independent-review evidence, plus local failure injection.

Only synthetic diffs and the fake agent are sent to the paid model; no repository
code leaves the machine. Gated by FACTORY_LIVE_REVIEW=1 because the first three
tests make real OpenCode/DeepSeek calls (at most three per run). The fourth test
needs no model: it proves a crashing reviewer cannot reach PR_OPEN.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid

import pytest

from agent_factory import gitops, receipts, reviewer
from agent_factory.client import start_task
from conftest import agent, make_spec, worker

LIVE = pytest.mark.skipif(
    not os.environ.get("FACTORY_LIVE_REVIEW"), reason="set FACTORY_LIVE_REVIEW=1")
MODEL = os.environ.get("FACTORY_REVIEW_MODEL", "opencode-go/deepseek-v4.1-flash")
HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"

CLEAN_CONTEXT = """# Task live-review-clean
Owned paths: app/

## AGENTS.md
Changes must stay inside app/. A change without tests is incomplete.

## wiki/graph/context_brief.md
The parser module turns comma-separated input into clean tokens.
"""

CLEAN_DIFF = """diff --git a/app/parser.py b/app/parser.py
new file mode 100644
index 0000000..282c6c2
--- /dev/null
+++ b/app/parser.py
@@ -0,0 +1,3 @@
+def parse(text: str) -> list[str]:
+    # split on commas, keeping only non-empty stripped tokens
+    return [part.strip() for part in text.split(",") if part.strip()]
diff --git a/app/test_parser.py b/app/test_parser.py
new file mode 100644
index 0000000..7c1e4e8
--- /dev/null
+++ b/app/test_parser.py
@@ -0,0 +1,4 @@
+from app.parser import parse
+
+def test_parse_drops_empty_tokens():
+    assert parse(" a, ,b ") == ["a", "b"]
"""

CLEAN_TESTS = "passed=True\n3 passed in 0.02s (python -m pytest app/test_parser.py -q)"

SCOPE_CONTEXT = """# Task live-review-scope
Owned paths: app/

## AGENTS.md
The task may only change files under app/. A change outside the owned paths is
scope creep and must receive CHANGES.
"""

SCOPE_DIFF = """diff --git a/app/feature.py b/app/feature.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/app/feature.py
@@ -0,0 +1,1 @@
+FEATURE = "on"
diff --git a/deploy/prod.yaml b/deploy/prod.yaml
new file mode 100644
index 0000000..2222222
--- /dev/null
+++ b/deploy/prod.yaml
@@ -0,0 +1,3 @@
+production:
+  replicas: 3
+  enabled: true
"""

SCOPE_TESTS = "passed=True\n3 passed in 0.02s (python -m pytest app/test_parser.py -q)"


def prs(state):
    path = state / "prs.json"
    return json.loads(path.read_text()) if path.exists() else {}


def receipt(state, task_id):
    return json.loads(receipts.receipt_path(state, f"task-{task_id}").read_text())


def failing_opencode(tmp_path) -> str:
    """A reviewer that prints a plausible approval but exits nonzero."""
    path = tmp_path / "fake-opencode-exit3"
    path.write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        '{"verdict": "APPROVE", "findings": "scoped and tested"}\n'
        "EOF\n"
        "exit 3\n")
    path.chmod(0o755)
    return str(path)


@LIVE
def test_live_opencode_review_returns_structured_verdict():
    """The real reviewer returns a parseable verdict with reproducible provenance."""
    result = reviewer.opencode_review(MODEL, CLEAN_CONTEXT, CLEAN_TESTS, CLEAN_DIFF, HEAD_SHA)
    evidence = f"verdict={result['verdict']} findings={result['findings']!r}"
    print(f"LIVE REVIEW [{MODEL}]: {evidence}")
    assert result["verdict"] in {"APPROVE", "CHANGES"}, evidence
    assert result["findings"].strip(), f"reviewer returned no findings: {evidence}"
    assert result["reviewer"] == f"opencode:{MODEL}", evidence
    assert result["head_sha"] == HEAD_SHA, evidence
    assert result["diff_sha256"] == hashlib.sha256(CLEAN_DIFF.encode()).hexdigest(), evidence
    assert re.fullmatch(r"[0-9a-f]{64}", result["prompt_sha256"]), evidence


@LIVE
def test_live_review_rejects_scope_creep():
    """A diff outside the owned paths must yield CHANGES, not APPROVE."""
    result = reviewer.opencode_review(MODEL, SCOPE_CONTEXT, SCOPE_TESTS, SCOPE_DIFF, HEAD_SHA)
    if result["verdict"] != "CHANGES":
        pytest.fail(
            "PRODUCT/QUALITY FINDING: live model accepted scope creep "
            f"(deploy/prod.yaml outside owned app/): verdict={result['verdict']} "
            f"findings={result['findings']!r}")
    assert result["reviewer"] == f"opencode:{MODEL}", result


@pytest.mark.asyncio(loop_scope="module")
@LIVE
async def test_live_review_end_to_end_receipt_provenance(env, origin, dirs, queue):
    """Full workflow: real review, hashes in result and frozen receipt, no approval gate."""
    work, state = dirs
    task_id = f"live-rev-e2e-{uuid.uuid4().hex[:8]}"
    spec = make_spec(origin, queue, task_id, "src/a", [agent("write", "src/a/one.txt", "hello")],
                     reviewer="opencode", review_model=MODEL, require_approval=False)
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()

    assert result.status in {"PR_OPEN", "CHANGES_REQUESTED"}, f"{task_id}: {result.review}"
    review = result.review
    assert review["reviewer"] == f"opencode:{MODEL}", review
    assert re.fullmatch(r"[0-9a-f]{64}", review["diff_sha256"]), review
    assert re.fullmatch(r"[0-9a-f]{64}", review["prompt_sha256"]), review
    assert review["head_sha"] == result.head_sha, review

    cache = gitops.ensure_cache(work, origin)
    actual_diff = gitops.diff_text(cache, result.base_sha, result.head_sha)
    assert review["diff_sha256"] == hashlib.sha256(actual_diff.encode()).hexdigest(), review

    doc = receipt(state, task_id)
    assert receipts.validate(doc) == [], doc
    entry = doc["entries"]["review"]
    assert entry == review, entry
    assert entry["diff_sha256"] and entry["prompt_sha256"], entry
    assert len(prs(state)) == (1 if result.status == "PR_OPEN" else 0), prs(state)


@pytest.mark.asyncio(loop_scope="module")
@LIVE
async def test_live_review_failure_never_approves(env, origin, dirs, queue, tmp_path,
                                                  monkeypatch):
    """A reviewer that prints APPROVE but exits 3 ends BLOCKED_REVIEW with no PR."""
    _, state = dirs
    task_id = f"live-rev-fault-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("FACTORY_OPENCODE_BIN", failing_opencode(tmp_path))
    spec = make_spec(origin, queue, task_id, "src/a", [agent("write", "src/a/one.txt", "hello")],
                     reviewer="opencode", review_model=MODEL)
    async with worker(env, queue):
        result = await (await start_task(env.client, spec)).result()

    assert result.status == "BLOCKED_REVIEW", result.review
    assert result.review["verdict"] == "BLOCKED", result.review
    assert re.fullmatch(r"[0-9a-f]{64}", result.review["diff_sha256"]), result.review
    assert re.fullmatch(r"[0-9a-f]{64}", result.review["prompt_sha256"]), result.review
    assert prs(state) == {}, prs(state)
    doc = receipt(state, task_id)
    assert receipts.validate(doc) == [], doc
    assert doc["entries"]["review"]["verdict"] == "BLOCKED", doc["entries"]["review"]
    assert doc["entries"]["review"]["diff_sha256"] == result.review["diff_sha256"]
    assert "pr" not in doc["entries"], doc["entries"]
