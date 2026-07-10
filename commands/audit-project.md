---
description: "Read-only delivery-readiness audit — git, docs, tests, deploy, security, providers, tech debt → structured status report"
argument-hint: "--project <name> [--repo <path> ...] [--period today|24h|week|all] [--focus <areas>]"
---

Invoke the `audit-project` skill from the `alpha-wiki` plugin. Human meaning: start or end a development session with a reliable, evidence-first project status report. Read-only — never edits, commits, pushes, or deploys.

Arguments: $ARGUMENTS

Generate the structured skeleton (all 17 sections, status labels, always-present security section, provider/business-coverage tables, read-only git inventory, `not confirmed` defaults):

```bash
uv run python -m tools.project_audit --project "<name>" --repo <path> --period <period> --out <wiki_dir>/outputs/delivery-audit.md $ARGUMENTS
```

Then fill every table from real evidence (git/docs/tests/logs), mark confidence, distinguish facts from assumptions, do not invent blockers, and finish with a concrete Next 3 Actions. This is a project-wide delivery audit, not the per-change `receiving-code-review`.
