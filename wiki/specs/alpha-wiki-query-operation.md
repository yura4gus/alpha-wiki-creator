---
title: Alpha-Wiki Query Operation
slug: alpha-wiki-query-operation
kind: operation-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/query.md, skills/query/SKILL.md, tools/wiki_search.py
---
# Alpha-Wiki Query Operation

## Provenance

- Source: commands/query.md.
- Source: skills/query/SKILL.md.
- Tool source: tools/wiki_search.py.

## Entities

- Operation: `/alpha-wiki:query` / `$alpha-wiki-query`.
- Read path: `context_brief.md`, `index.md`, deterministic search, targeted page reads.
- Output: cited answer with truth status.

## Requirements

- Answer from maintained wiki evidence, not the open web.
- Start from graph context and index before targeted search.
- Cite wiki pages, slugs, and paths when precision matters.
- Distinguish accepted facts, assumptions, risks, open questions, and stale material.
- Do not mutate the wiki unless the user explicitly asks to save a reusable output.
- If knowledge is missing, route to [[alpha-wiki-ingest-operation]] instead of inventing memory.

## Gates

- Conflicting evidence must be surfaced.
- Reusable synthesis is saved only on explicit request.
- Query answers should recommend ingest, lint, evolve, review, or no action.

