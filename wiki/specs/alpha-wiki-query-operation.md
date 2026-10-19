---
title: Alpha-Wiki Query Operation
slug: alpha-wiki-query-operation
kind: operation-spec
status: stable
date_updated: 2026-10-19
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/query.md, skills/query/SKILL.md, tools/wiki_search.py
source_files:
  - commands/query.md
  - skills/query/SKILL.md
  - tools/wiki_search.py
  - references/concept.md
---
# Alpha-Wiki Query Operation

## Provenance

- Sources: commands/query.md, skills/query/SKILL.md, tools/wiki_search.py.
- Shared authority and read-only contract: references/concept.md.
- Reviewed against local development sources on 2026-10-19; this does not upgrade the installed 0.6.2 plugin.

## Entities

- Operation: `/alpha-wiki:query` / `$alpha-wiki:query`.
- Read path: existing brief/index for orientation, deterministic Markdown search, targeted source-page reads.
- Output: candidate pages with line citations; the agent synthesizes the cited answer.

## Requirements

- Answer from maintained wiki evidence, not the open web.
- Use supplied evidence directly when sufficient; otherwise orient through the brief/index and search the smallest relevant scope.
- Cite wiki pages, slugs, and paths when precision matters.
- Distinguish accepted facts, assumptions, risks, open questions, and stale material.
- Backend ranking is lexical, not semantic search. Its `accepted` label means an accepted/stable page matched, not that the answer or a deployment was approved.
- Wiki guides retrieval; accepted source contracts, exact code snapshots, and runtime observations retain their distinct authority.
- Do not mutate the wiki unless the user explicitly asks to save a reusable output.
- For strict zero-write execution, use a prepared environment and suppress bytecode; do not bootstrap a runtime or refresh generated files.
- If knowledge is missing, route to [[alpha-wiki-ingest-operation]] instead of inventing memory.

## Gates

- Surface conflicting or stale evidence before relying on it.
- Save reusable synthesis only on explicit request; log actual persisted changes, not every lookup.
- Recommend ingest, lint, evolve, review, or no action only when relevant to the answer.
