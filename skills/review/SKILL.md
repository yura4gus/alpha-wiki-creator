---
name: review
description: "Run a wiki-level review: health snapshot, lint findings, graph risks, stale pages, open questions, and next actions. Use for weekly review, before release, before sharing the wiki, or when the user asks whether the wiki can be trusted. This is not AgentOps CTO/team review."
---

# wiki:review - structural wiki review

## Mission

Provide a disciplined review of the wiki as a memory system. Review answers: is this wiki coherent, current, navigable, and safe for an agent to rely on?

## Name Contract

`review` means "audit wiki memory quality". It is broader than `lint` and deeper than `status`, but still Alpha-Wiki scoped. It does not evaluate team process, delivery quality, or AgentOps handoffs.

## Review Questions

Use the questions relevant to the requested scope; a full wiki review can cover
all of them. Present only findings and evidence useful to that scope:

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
11. Is the **active scope** recorded (`raw/docs/source-manifest.md`), and is anything out-of-scope creeping in?
12. Is **security memory** captured (auth/session, secrets/env, release/custody gates), or only placeholders?

## Scope And Security

The deterministic backend emits scope, security memory, and a release-readiness
label. Report that label as the backend's wiki-quality result with its concrete
findings. Missing scope or security pages are documentation gaps, not proof of
a runtime vulnerability or a universal package-release prohibition. Inspect
existing project evidence before proposing new pages or controls. Scaffold
placeholders only when the user requests wiki repair; a review alone does not
authorize it. Never invent security facts, secrets, signatures, or owner votes.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

1. Detect wiki dir and config.
2. Run deterministic backend:
   - `python3 .alpha-wiki/run.py -m tools.review --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml`
   - For a strict no-write audit, add `--read-only` and follow
     `references/concept.md` (Strict Read-Only Operations). Do not use `--out`,
     refresh/fix commands, a cold target runtime, or bytecode writes.
3. Inspect graph semantics:
   - Distinguish `_index.md` catalogs from entities. A catalog does not need
     contract/owner fields and does not prove substantive cluster coverage;
     its broken links and duplicate slugs still matter.
   - Red nodes isolated.
   - Orange contracts missing consumers/owners.
   - Dark grey docs with no inbound links.
   - Pages missing typed cluster ownership (`belongs_to`, `affects`, `implements`, `service`, `target_module`, `consumers`).
   - Pages without `date_updated`.
4. Return the requested format. Summarize concrete errors, warnings, relevant
   gaps, and next actions; the full backend report need not be pasted again.
5. If requested, save to `<wiki_dir>/outputs/review-YYYY-MM-DD.md`.
6. If CI generated the report, ensure it is suitable as a GitHub issue body.

## Boundaries

- Not AgentOps `cto-review`.
- Not semantic truth arbitration unless evidence is in the wiki.
- Not a place to invent content.
- If review finds missing knowledge, route to `/alpha-wiki:ingest`.
- If review finds schema gaps, route to `/alpha-wiki:evolve`.

## Codex Native Delegation

Run the deterministic review backend once in the controller. For substantial
independent evidence needs, optionally delegate relevant read-only scopes:

1. Structure and graph: links, clusters, isolated roles, and generated-view
   consistency.
2. Contracts and provenance: owners, consumers, source evidence, accepted
   decisions, and runtime pointers.
3. Freshness and gaps: stale pages, scope drift, security placeholders, open
   questions, and missing owner/timebox.

Each agent receives the same wiki/runtime snapshot, does not edit files, and
uses the common result envelope. Wait for all terminal results, preserve
disagreements, and merge them with deterministic findings into one review.
Route fixes to ingest/evolve/lint; do not repair during a read-only review.
Follow `references/codex-subagent-orchestration.md`.

## Done Criteria

- User can see blockers vs warnings vs maintenance suggestions.
- Every suggested action maps to a command or file.
- Review strengthens the wiki without hiding uncertainty.

## References

- `tools/review.py`
- `tools/status.py`
- `tools/lint.py`
- `assets/obsidian/COLOR-LEGEND.md`
- `references/codex-subagent-orchestration.md`
