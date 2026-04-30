---
name: rollup
description: Generate a weekly or monthly wiki activity rollup from log entries and updated pages. Triggers include "roll up the wiki", "monthly wiki summary", "weekly wiki summary", or scheduled CI rollup.
argument-hint: "[week | month] [--write]"
---

# wiki:rollup - period summary

## Process

1. Determine period: `month` by default, or `week` if requested.
2. Detect wiki dir from `CLAUDE.md` or default to `wiki/`.
3. Run:
   ```bash
   uv run python tools/rollup.py --wiki-dir <wiki_dir> --period <week|month>
   ```
4. If persistence is requested or CI is running, add `--write` to create:
   - `<wiki_dir>/rollups/YYYY-MM.md`
   - `<wiki_dir>/rollups/YYYY-Www.md`
5. Surface the rollup path and key sections.

## Output

- Activity from `<wiki_dir>/log.md`
- Pages updated during the period via `date_updated`
- Follow-up checklist

## Boundaries

- This is deterministic summarization, not semantic rewriting.
- It does not mutate existing wiki pages except for the explicit `--write` rollup output.
