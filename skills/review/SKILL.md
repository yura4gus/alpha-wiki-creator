---
name: review
description: Run a wiki-level structural review: status snapshot, lint findings, and suggested next actions. Triggers include "review the wiki", "weekly wiki review", "audit wiki structure", or scheduled CI review. This is Alpha-Wiki-level review, not AgentOps CTO/team review.
argument-hint: "[--out <path>]"
---

# wiki:review - structural wiki review

## Process

1. Detect wiki dir from `CLAUDE.md` or default to `wiki/`.
2. Run:
   ```bash
   uv run python tools/review.py --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml
   ```
3. Surface the report to the user.
4. If the user requested a file, pass `--out <path>` or save under `<wiki_dir>/outputs/review-YYYY-MM-DD.md`.

## Output

- Summary counts: errors, warnings, total findings
- Health snapshot from `/alpha-wiki:status`
- Structural findings from `/alpha-wiki:lint`
- Suggested next actions

## Boundaries

- This is wiki-level review only: stale pages, link integrity, frontmatter, graph health.
- It is not AgentOps `cto-review`, does not inspect team process, and does not produce AgentOps review artifacts.
