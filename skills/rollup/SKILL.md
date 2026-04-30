---
name: rollup
description: "Generate a weekly or monthly wiki activity rollup from log entries, updated pages, open questions, and follow-ups. Use at the end of a week/month, before stakeholder updates, or when the wiki needs a compact changelog. Do not use as a substitute for ingesting source material."
argument-hint: "[week | month] [--write]"
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
   - `uv run python tools/rollup.py --wiki-dir <wiki_dir> --period <week|month>`
   - Add `--write` when persistence is requested.
4. Read generated report and improve presentation if needed without inventing facts.
5. If written, ensure output path:
   - `<wiki_dir>/rollups/YYYY-MM.md`
   - `<wiki_dir>/rollups/YYYY-Www.md`
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

## References

- `tools/rollup.py`
- `<wiki_dir>/log.md`
- `<wiki_dir>/graph/open_questions.md`
