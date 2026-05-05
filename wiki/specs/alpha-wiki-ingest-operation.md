---
title: Alpha-Wiki Ingest Operation
slug: alpha-wiki-ingest-operation
kind: operation-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/ingest.md, skills/ingest/SKILL.md, tools/ingest_pipeline.py
---
# Alpha-Wiki Ingest Operation

## Provenance

- Source: commands/ingest.md.
- Source: skills/ingest/SKILL.md.
- Tool source: tools/ingest_pipeline.py.

## Entities

- Operation: `/alpha-wiki:ingest` / `$alpha-wiki-ingest`.
- Inputs: durable sources such as PRDs, ADRs, specs, transcripts, API files, and research notes.
- Outputs: typed wiki pages, log entries, graph artifacts, lint summary.

## Requirements

- Preserve provenance and keep raw evidence immutable.
- Use existing schema first; route repeated no-fit cases to evolve.
- Write stable slugs, frontmatter, status, source metadata, and typed links.
- Attach pages to clusters through fields such as `belongs_to`, `affects`, `implements`, `service`, or `target_module`.
- Rebuild `edges.jsonl`, `context_brief.md`, and `open_questions.md` after writes.
- Stop and fix structural issues before continuing a batch.

## Gates

- Schema evolution is gated unless configured as auto.
- Ambiguous truth becomes assumption, risk, or open question.
- Duplicate pages are merged or updated rather than duplicated.

