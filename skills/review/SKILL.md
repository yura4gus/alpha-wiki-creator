---
name: review
description: "Run a wiki-level review: health snapshot, lint findings, graph risks, stale pages, open questions, and next actions. Use for weekly review, before release, before sharing the wiki, or when the user asks whether the wiki can be trusted. This is not AgentOps CTO/team review."
argument-hint: "[--out <path>]"
---

# wiki:review - structural wiki review

## Mission

Provide a disciplined review of the wiki as a memory system. Review answers: is this wiki coherent, current, navigable, and safe for an agent to rely on?

## Name Contract

`review` means "audit wiki memory quality". It is broader than `lint` and deeper than `status`, but still Alpha-Wiki scoped. It does not evaluate team process, delivery quality, or AgentOps handoffs.

## Review Questions

Always consider:

1. Are there blocking structural errors?
2. Are important pages stale?
3. Are there orphan services/modules/contracts?
4. Are open questions visible and actionable?
5. Are contracts linked to owners and consumers?
6. Are decisions linked to affected modules/specs?
7. Does the Obsidian graph tell the same story as the markdown?
8. Is any source material still only in `raw/` and not ingested?
9. Did schema evolve recently, and did migration complete?
10. What are the next three maintenance actions?

## Workflow

1. Detect wiki dir and config.
2. Run deterministic backend:
   - `uv run python tools/review.py --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml`
3. Inspect graph semantics:
   - Red nodes isolated.
   - Orange contracts missing consumers/owners.
   - Dark grey docs with no inbound links.
   - Pages missing typed cluster ownership (`belongs_to`, `affects`, `implements`, `service`, `target_module`, `consumers`).
   - Pages without `date_updated`.
4. Surface report with:
   - Summary.
   - Health snapshot.
   - Trust checks: cluster gaps, isolated services, provenance, freshness.
   - Structural findings.
   - Graph/Obsidian observations.
   - Suggested next actions.
5. If requested, save to `<wiki_dir>/outputs/review-YYYY-MM-DD.md`.
6. If CI generated the report, ensure it is suitable as a GitHub issue body.

## Boundaries

- Not AgentOps `cto-review`.
- Not semantic truth arbitration unless evidence is in the wiki.
- Not a place to invent content.
- If review finds missing knowledge, route to `/alpha-wiki:ingest`.
- If review finds schema gaps, route to `/alpha-wiki:evolve`.

## Done Criteria

- User can see blockers vs warnings vs maintenance suggestions.
- Every suggested action maps to a command or file.
- Review strengthens the wiki without hiding uncertainty.

## References

- `tools/review.py`
- `tools/status.py`
- `tools/lint.py`
- `assets/obsidian/COLOR-LEGEND.md`
