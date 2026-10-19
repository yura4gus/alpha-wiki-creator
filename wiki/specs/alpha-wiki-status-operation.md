---
title: Alpha-Wiki Status Operation
slug: alpha-wiki-status-operation
kind: operation-spec
status: stable
date_updated: 2026-10-19
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/status.md, skills/status/SKILL.md, tools/status.py
source_files:
  - commands/status.md
  - skills/status/SKILL.md
  - tools/status.py
  - tools/wiki_engine.py
  - references/concept.md
---
# Alpha-Wiki Status Operation

## Provenance

- Sources: commands/status.md, skills/status/SKILL.md, tools/status.py, tools/wiki_engine.py.
- Shared authority and read-only contract: references/concept.md.
- Reviewed against local development sources on 2026-10-19; strict read-only mode is not in public 0.6.2.

## Entities

- Operation: `/alpha-wiki:status` / `$alpha-wiki:status`.
- Report: Status Summary, Gap Check, Cluster Health, Provenance, Freshness, Open Question Follow-Up, Recent Activity, Suggested Next Actions.
- Read model: current Markdown, journal, typed links, and source-binding maintenance state when configured.

## Requirements

- Status does not edit source pages. Default execution refreshes generated edges, brief, and open questions.
- `--read-only` derives current edges/questions in memory, including when graph exports are absent or stale. It writes no graph, report, or worker checkpoint.
- `--read-only` with `--out` is rejected before reporting or writing.
- Strict zero-write execution additionally requires a prepared runtime and bytecode suppression; cold environment setup is a separate write.
- The Gap Check is mandatory and cross-cutting.
- Report pages, edges, open questions, log entries, provenance, stale/missing dates, and concrete next actions.
- When document governance is configured, expose pending source-bound jobs and unmapped coverage without invoking a model. Neither missing bindings nor an empty queue proves global freshness.
- Thin, noisy, stale, and disconnected memory are maintenance findings, not automatic production-release blockers.

## Gates

- Saving a requested report does not authorize source-page repair.
- Suggested actions map to commands or files; honor the user's output format.
- Use [[alpha-wiki-review-operation]] for deeper structural review; status alone does not accept contracts, ratify decisions, or prove deployment.
