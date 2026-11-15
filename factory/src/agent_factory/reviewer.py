"""Independent review adapters.

`opencode` runs any model through the OpenCode CLI (`opencode run -m provider/model`),
using OpenCode's own stored authentication; no API key passes through this package.
It sends the diff to that model's provider, so it runs only when a spec asks for it.
Any failure or unparseable answer returns BLOCKED: a review is never approved by
default. `stub` is rule-based and labelled as such; it does not replace the
independent review.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile

PROMPT = """You are an independent code reviewer. Judge the diff against the task contract.
Reply with JSON only: {"verdict": "APPROVE" | "CHANGES", "findings": "<text>"}.
Request CHANGES for any defect, scope creep, missing tests, or contract violation.

# Contracts and context
%s

# Test result
%s

# Diff
%s
"""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def stub_review(owned_paths: list[str], diff: str, tests_passed: bool, head_sha: str) -> dict:
    diff_sha = _sha(diff)
    if not diff.strip():
        return {"verdict": "CHANGES", "findings": "empty diff", "reviewer": "stub-rule-based",
                "head_sha": head_sha, "diff_sha256": diff_sha, "prompt_sha256": ""}
    if not tests_passed:
        return {"verdict": "CHANGES", "findings": "tests did not pass", "reviewer": "stub-rule-based",
                "head_sha": head_sha, "diff_sha256": diff_sha, "prompt_sha256": ""}
    return {"verdict": "APPROVE", "findings": "rule-based: non-empty diff, tests passed",
            "reviewer": "stub-rule-based", "head_sha": head_sha, "diff_sha256": diff_sha,
            "prompt_sha256": ""}


def _parse_verdict(text: str) -> dict:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # strip terminal colour codes
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object in reply")
    parsed = json.loads(match.group(0))
    if parsed.get("verdict") not in {"APPROVE", "CHANGES"}:
        raise ValueError(f"bad verdict {parsed.get('verdict')!r}")
    return parsed


def opencode_review(model: str, context: str, tests_summary: str, diff: str, head_sha: str,
                    timeout: int = 300) -> dict:
    binary = os.environ.get("FACTORY_OPENCODE_BIN", "opencode")
    prompt = PROMPT % (context[:12000], tests_summary, diff)
    reviewer = f"opencode:{model}"
    diff_sha, prompt_sha = _sha(diff), _sha(prompt)
    blocked = {"verdict": "BLOCKED", "reviewer": reviewer, "head_sha": head_sha,
               "diff_sha256": diff_sha, "prompt_sha256": prompt_sha}
    if "passed=True" not in tests_summary:
        return {**blocked, "verdict": "CHANGES", "findings": "tests did not pass"}
    if not diff.strip():
        return {**blocked, "verdict": "CHANGES", "findings": "empty diff"}
    try:
        # Empty scratch cwd and minimal env: the reviewer sees only the prompt, not the repo.
        with tempfile.TemporaryDirectory(prefix="factory-review-") as cwd:
            proc = subprocess.run(
                [binary, "run", "-m", model, prompt], cwd=cwd, capture_output=True, text=True,
                timeout=timeout,
                env={k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TMPDIR") if k in os.environ})
        if proc.returncode != 0:
            raise RuntimeError((proc.stdout + proc.stderr).strip()[-300:] or f"exit {proc.returncode}")
        parsed = _parse_verdict(proc.stdout)
        findings = str(parsed.get("findings", "")).strip()
        if parsed["verdict"] == "APPROVE" and not findings:
            raise ValueError("APPROVE without findings")
        return {"verdict": parsed["verdict"], "findings": findings,
                "reviewer": reviewer, "head_sha": head_sha, "diff_sha256": diff_sha,
                "prompt_sha256": prompt_sha}
    except Exception as exc:  # a failed or unparseable review must never approve
        return {**blocked, "findings": f"review failed: {type(exc).__name__}: {exc}"[:400]}
