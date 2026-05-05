---
title: No Embeddings MVP
slug: no-embeddings-mvp
status: accepted
date: 2026-05-05
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-003-no-embeddings-mvp.md, README.md
---
# No Embeddings MVP

## Provenance

- Source: docs/ADR-003-no-embeddings-mvp.md, README.md.

## Context

Alpha-Wiki follows the Karpathy LLM-Wiki pattern: simple markdown memory, explicit index/brief files, and deterministic operations before any retrieval infrastructure.

## Decision

The MVP uses plain markdown, frontmatter, wikilinks, graph artifacts, and deterministic search. It does not require embeddings or a vector store.

## Consequences

- Context remains inspectable and reviewable in git.
- Agents can cite exact pages and lines.
- Search quality can later improve with BM25 before any embedding backend is reconsidered.
