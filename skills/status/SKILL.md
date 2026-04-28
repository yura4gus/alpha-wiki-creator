---
name: status
description: Wiki health report — recent activity, stale pages, schema-evolution log, gaps, lint summary. Triggers include "wiki status", "wiki health", "what's stale in the wiki", "show me the wiki dashboard", "audit the wiki". Auto-invokable; pure read-only operation, no side effects beyond an optional saved report.
---

# wiki:status — wiki health report

## Process

1. Detect wiki dir: read `CLAUDE.md` for `Wiki dir:` line, or default to `wiki/`.
2. Run `uv run python -m tools.status --wiki-dir <wiki_dir>` to generate the report.
   (If module-style invocation isn't wired, run `uv run python -c "from tools.status import status_report; from pathlib import Path; print(status_report(Path('<wiki_dir>')))"`.)
3. Surface the report to the user.
4. Run `uv run python tools/lint.py --wiki-dir <wiki_dir> --suggest --config .alpha-wiki/config.yaml` and append a brief summary (lint counts) to the user's view.
5. Offer to save the report to `<wiki_dir>/outputs/status-YYYY-MM-DD.md` (yes / no).

## What's included

- **Stats**: page count, edge count, open-question count, log-entry count
- **Recent activity**: last 10 log entries (any op type)
- **Schema evolution**: every `schema-change` log entry, full history
- **Stale pages**: pages with `date_updated` more than 30 days old
- **Pages without `date_updated`**: candidates for a maintenance pass
- **Lint summary**: brief count of errors + warnings (full detail via `/alpha-wiki:lint`)

## When to run

- After a long break — see what changed, what's stale
- Weekly cadence as a self-check
- Before a `/alpha-wiki:rollup` so you know what to highlight
- After someone else has been working in the wiki

This skill is read-only. It never mutates the wiki except for the optional saved report.
