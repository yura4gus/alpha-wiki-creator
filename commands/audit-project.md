---
description: "Read-only delivery-readiness audit — git, docs, tests, deploy, security, providers, tech debt → structured status report"
argument-hint: "--project <name> [--repo <path> ...] [--period today|24h|week|all] [--focus <areas>]"
---

Invoke the `audit-project` skill from the `alpha-wiki` plugin. Human meaning: start or end a development session with a reliable, evidence-first project status report. Read-only — never edits, commits, pushes, or deploys.

Arguments: $ARGUMENTS

Honor the user's requested format and scope. For a full audit, the optional
backend prints a 17-section skeleton to stdout:

```bash
uv run python -m tools.project_audit --project "<name>" --repo <path> --period <period>
```

Use only applicable sections for a bounded request. Strict read-only creates no
report file or graph refresh. Ground conclusions in evidence; distinguish failed,
unverified, and optional items. A release blocker needs its existing requirement,
failure, affected step, and smallest fix. Do not add signing, secrets, approvals,
or cosmetic gates. Return the result, evidence, and useful next actions concisely.
