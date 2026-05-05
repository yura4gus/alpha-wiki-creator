---
title: Alpha-Wiki Runtime
slug: alpha-wiki-runtime
status: stable
date_updated: 2026-05-05
owner: yuragus
description: Plain-markdown agent memory runtime with Claude Code primary support and Codex skill adapters.
evidence: README.md, docs/final-release-readiness-audit-2026-05-04.md, CHANGELOG.md, raw/docs/source-manifest-2026-05-05.md
consumes:
  - "[[codex-skill-adapter-contract]]"
decisions:
  - "[[no-embeddings-mvp]]"
  - "[[graph-cluster-semantics]]"
---
# Alpha-Wiki Runtime

## Provenance

- Source: README.md, docs/final-release-readiness-audit-2026-05-04.md, CHANGELOG.md.

## Provides

- Bootstrap for a typed markdown wiki in a target project.
- Deterministic graph rebuild through `tools/wiki_engine.py`.
- Structural lint/status/review/rollup tools.
- Codex skill adapter installation through `scripts/install_codex.py`.
- Release gates through `tools/release_audit.py` and `tools/release_smoke.py`.
- Source inventory through [[source-corpus-inventory]].

## Consumes

- [[codex-skill-adapter-contract]]

## Decisions

- [[no-embeddings-mvp]]
- [[graph-cluster-semantics]]

## Active tasks

- Keep release audit `READY`.
- Improve unified health scoring and Codex automation parity in the next hardening pass.
