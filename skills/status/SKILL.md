---
name: status
description: "Produce a read-only wiki health dashboard: page count, graph count, open questions, stale pages, recent activity, schema changes, lint summary, and suggested next actions. Use after a break, before rollup/review, after ingest, or whenever the user asks what shape the wiki is in."
---

# wiki:status - health dashboard

## Mission

Give the user a fast, honest picture of wiki health. Status should teach what needs attention without changing the wiki.

## Name Contract

`status` means "observe and summarize current health". It does not edit source wiki pages. It may refresh generated graph artifacts (`edges.jsonl`, `context_brief.md`, `open_questions.md`) before reporting so health is measured from current pages, not stale derived files.

## Workflow

1. Detect wiki dir:
   - Prefer `CLAUDE.md` "Wiki dir" line.
   - Fall back to `wiki/`.

2. Read:
   - `<wiki_dir>/log.md`
   - `<wiki_dir>/graph/edges.jsonl`
   - `<wiki_dir>/graph/open_questions.md`
   - All pages via `tools/wiki_engine.py`.

3. Generate report:
   - Status Summary: pages, edges, open questions, log entries, gap count.
   - Gap Check: cross-cutting holes that block wiki usefulness.
   - Recent activity.
   - Schema evolution events.
   - Stale pages.
   - Pages without `date_updated`.
   - Lint summary.
   - Suggested next actions.

4. Optionally save:
   - `<wiki_dir>/outputs/status-YYYY-MM-DD.md`
   - Link saved report to relevant source pages if it becomes long-lived.

## Health Interpretation

- Healthy wiki: low errors, few orphans, active graph, recent log, open questions visible.
- Thin wiki: few pages, low edge count, no decisions/specs/contracts.
- Stale wiki: many pages without `date_updated` or old stable pages.
- Noisy wiki: many outputs or sources with no inbound links.
- Miscolored graph: likely directory/type mismatch; run `/alpha-wiki:render` or revisit schema.

## Required Status Format

Use one stable format so every session can compare status over time:

1. `Status Summary`
   - Pages.
   - Edges.
   - Open questions.
   - Recent log entries.
   - Gap check count.
2. `Gap Check`
   - Content gap: no durable pages yet.
   - Graph gap: pages exist but typed edges are absent.
   - Process gap: no auditable log entries.
   - Decision gap: open questions have no owner or next action.
   - Freshness gap: pages are stale.
   - Metadata gap: pages miss `date_updated`.
   - Coverage gap: no decisions/specs/contracts/features/claims/papers.
3. `Recent activity`
4. `Schema evolution`
5. `Stale pages`
6. `Pages without date_updated`
7. `Lint summary`
8. `Suggested next actions`

The Gap Check is cross-cutting. It should tell the user where the wiki is structurally blind, even when individual lint checks pass.

## Suggested Actions

Status should recommend concrete next steps:

- Run `/alpha-wiki:lint --fix` for missing reverse links.
- Run `/alpha-wiki:ingest <path>` when raw sources exist but wiki pages are missing.
- Run `/alpha-wiki:evolve` when repeated content does not fit.
- Run `/alpha-wiki:review` before sharing or release.
- Run `/alpha-wiki:rollup month --write` at period end.
- Run `/alpha-wiki:render obsidian` if visual semantics look stale.

## Done Criteria

- Report is clear enough for a user to decide next action.
- It distinguishes facts from recommendations.
- It does not mutate source pages unless the user explicitly asks to save.
- It always includes `Gap Check`.

## References

- `tools/status.py`
- `tools/review.py`
- `tools/lint.py`
