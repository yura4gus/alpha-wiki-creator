"""Independent review adapters.

`deepseek` talks to an OpenAI-compatible endpoint and sends the diff to it, so
it runs only when a spec asks for it. Without credentials it returns BLOCKED:
a review is never approved by default. `stub` is rule-based and labelled as
such in every result; it does not replace the independent review.
"""

from __future__ import annotations

import json
import os
import urllib.request

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


def stub_review(owned_paths: list[str], diff: str, tests_passed: bool, head_sha: str) -> dict:
    if not diff.strip():
        return {"verdict": "CHANGES", "findings": "empty diff", "reviewer": "stub-rule-based",
                "head_sha": head_sha}
    if not tests_passed:
        return {"verdict": "CHANGES", "findings": "tests did not pass", "reviewer": "stub-rule-based",
                "head_sha": head_sha}
    return {"verdict": "APPROVE", "findings": "rule-based: non-empty diff, tests passed",
            "reviewer": "stub-rule-based", "head_sha": head_sha}


def deepseek_review(context: str, tests_summary: str, diff: str, head_sha: str) -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return {"verdict": "BLOCKED", "findings": "DEEPSEEK_API_KEY is not set on the worker",
                "reviewer": "deepseek", "head_sha": head_sha}
    base = os.environ.get("FACTORY_REVIEW_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("FACTORY_REVIEW_MODEL")
    if not model:
        return {"verdict": "BLOCKED", "findings": "FACTORY_REVIEW_MODEL is not set",
                "reviewer": "deepseek", "head_sha": head_sha}
    body = json.dumps({
        "model": model, "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT % (context[:12000], tests_summary, diff)}],
    }).encode()
    request = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content = json.loads(response.read())["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        verdict = parsed["verdict"]
        if verdict not in {"APPROVE", "CHANGES"}:
            raise ValueError(verdict)
        return {"verdict": verdict, "findings": str(parsed.get("findings", "")),
                "reviewer": f"deepseek:{model}", "head_sha": head_sha}
    except Exception as exc:  # unparseable or failed review must never approve
        return {"verdict": "BLOCKED", "findings": f"review failed: {type(exc).__name__}: {exc}",
                "reviewer": "deepseek", "head_sha": head_sha}
