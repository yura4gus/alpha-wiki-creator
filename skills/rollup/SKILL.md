---
name: rollup
description: "Generate a weekly or monthly wiki rollup, optionally including AgentOps sessions, handoffs, and backlog updates. Use before stakeholder updates or when durable activity needs a compact summary."
argument-hint: "[week | month] [--scope wiki|agentops|all] [--write]"
---

# wiki:rollup - period summary

## Mission

Compress a period of wiki activity into a durable summary while preserving links back to source pages. Rollup is how the wiki compounds without forcing users to reread every log entry.

## Name Contract

`rollup` means "summarize a time window". It does not rewrite the underlying pages and does not replace `log.md`.

## Periods

- `month`: default. Output label `YYYY-MM`.
- `week`: ISO week. Output label `YYYY-Www`.

## Workflow

1. Detect wiki dir.
2. Determine period.
3. Run backend:
   - `uv run python -m tools.rollup --wiki-dir <wiki_dir> --period <week|month>`
   - Add `--scope agentops` for execution memory or `--scope all` for both layers.
   - Add `--write` when persistence is requested.
4. Read generated report and improve presentation if needed without inventing facts.
5. If written, ensure output path:
   - `<wiki_dir>/rollups/YYYY-MM.md`
   - `<wiki_dir>/rollups/YYYY-Www.md`
   - AgentOps-only: `<wiki_dir>/agentops/rollups/<period>.md`
6. Link the rollup from index or a summary page if the project uses rollups as navigation.
7. Run `/alpha-wiki:lint --suggest` if links were added.

## Rollup Content

Include:

- Activity from `log.md`.
- Pages updated in period via `date_updated`.
- Important decisions/specs/contracts touched.
- Open questions created or still unresolved.
- Stale pages that block confidence.
- Suggested next actions.

## Quality Bar

- A reader can understand what changed without reading every page.
- Every claim links to wiki pages or log entries.
- Rollup is idempotent: same period, same inputs, same output.
- It does not hide unresolved questions.

## Boundaries

- Do not summarize raw files that have not been ingested.
- Do not mark decisions accepted unless the source page says so.
- Do not create new schema.
- Do not use rollup to fix graph problems; route to `lint`, `ingest`, `evolve`, or `render`.

## Codex Native Delegation

Do not fan out rollup. The deterministic backend already reads one bounded time
window and must produce an idempotent result. Parallel summaries create duplicate
claims and inconsistent period boundaries. Delegate only a separate source
investigation when the rollup proves evidence is missing.

## References

- `tools/rollup.py`
- `<wiki_dir>/log.md`
- `<wiki_dir>/graph/open_questions.md`
- `references/codex-subagent-orchestration.md`
- `references/agentops-control-layer.md`
