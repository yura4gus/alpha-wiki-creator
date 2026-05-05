---
title: Alpha-Wiki Product Spec
slug: alpha-wiki-product-spec
kind: product-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/01-alpha-wiki.md
---
# Alpha-Wiki Product Spec

## Provenance

- Source: docs/01-alpha-wiki.md.

## Entities

- Runtime layers: `raw/`, wiki pages, graph artifacts, gated schema contract.
- User operations: init, doctor, ingest, query, lint, evolve, status, spawn-agent, render, review, rollup.
- Deterministic tools: wiki engine, lint, init audit, ingest pipeline, query/search, status/review/rollup, renderers, release audit, trust-depth checks.
- Presentation layer: Obsidian config plus Mermaid, DOT, and static HTML exports.

## Requirements

- Alpha-Wiki is standalone and must not import AgentOps or Superpowers.
- Wiki pages use typed frontmatter, stable slugs, provenance, and wikilinks.
- `ingest`, `query`, and `lint` remain the core Karpathy operations.
- `init` must audit the existing source corpus before migration.
- Graph artifacts are generated from markdown; users should not hand-edit `graph/*`.
- Colors label node roles, while typed links form clusters.

## Operation Pages

- [[alpha-wiki-init-operation]]
- [[alpha-wiki-ingest-operation]]
- [[alpha-wiki-query-operation]]
- [[alpha-wiki-lint-operation]]
- [[alpha-wiki-status-operation]]
- [[alpha-wiki-review-operation]]

## Links

- Runtime module: [[alpha-wiki-runtime]]
- Source migration: [[source-corpus-inventory]]
- No embeddings decision: [[no-embeddings-mvp]]
- Graph semantics decision: [[graph-cluster-semantics]]
