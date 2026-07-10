# Project Delivery Audit

`/alpha-wiki:audit-project` produces a read-only, evidence-first delivery-readiness
report so any Claude/Codex session can **start or end** with a reliable project
status snapshot — not a hallucinated one.

## When to run it

- **Session start**: "Where did development stop? What is the next safe action?"
- **Session end / handoff**: "Can this be handed to the next developer/agent?"
- **Pre-release**: "Is deploy actually ready, or does only testing remain?"
- **Founder/PM check-in**: a compact status with an approximate readiness %.

## What it guarantees

The deterministic backend (`tools/project_audit.py`) always emits:

- all **17 sections** in order (executive summary → next 3 actions);
- the exact **status-label legend** (🟢 🟡 ⚪ 🔴 🔵);
- an **always-present Security Review** section for software projects;
- **provider-coverage** and **SDK+backend business-case** tables;
- a **read-only git inventory** per repository (branch, remote, divergence,
  recent commits, uncommitted/untracked, branch sprawl);
- `not confirmed` in every cell without evidence — nothing is invented.

The operator (skill) then fills the tables from real git/docs/tests/logs evidence.

## Read-only guarantee

The audit never edits, commits, pushes, or deploys. Git inspection uses only
`git status`, `git log`, `git rev-list`, and reads. Anything that could mutate
state (a deploy, a write) must be confirmed with the user first.

## Running it

```bash
# skeleton for one repo
uv run python -m tools.project_audit --project "ZamWallet" --repo /path/to/repo \
  --period week --focus backend --focus sdk --out wiki/outputs/delivery-audit.md

# multi-repo workspace
uv run python -m tools.project_audit --project "Zamio" \
  --repo /path/to/backend --repo /path/to/sdk --repo /path/to/web \
  --period all --out wiki/outputs/delivery-audit.md
```

Then open the generated report and fill each section from evidence. Missing
inputs do not block the audit — they lower confidence and are marked
`not confirmed`.

## Evidence discipline

Always distinguish: **confirmed fact · likely assumption · unconfirmed claim ·
missing evidence · real blocker · suspected (non-root-cause) blocker**. Every
important status needs a commit hash, file path, command output, PR/MR number,
test line, or log line. Do not mark deploy blocked without a proven root cause;
if deploy is configured and only verification remains, say so.

## Relationship to `receiving-code-review`

`receiving-code-review` (Superpowers) is a **per-change** review discipline —
what changed, intended behavior, evidence, tests, residual risk, next action. It
stays separate. `/alpha-wiki:audit-project` is **project-wide** and references the
per-change review as a checklist rather than replacing it. Recommendation: keep
`receiving-code-review` as-is; link to it from the audit's Tech Debt / Mismatches
sections when a specific change needs a focused review.
