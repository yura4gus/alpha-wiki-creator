---
title: Alpha-Wiki Runtime
slug: alpha-wiki-runtime
status: stable
date_updated: 2026-09-08
owner: yuragus
description: Plain-markdown agent memory runtime with Claude Code primary support and Codex skill adapters.
evidence: README.md, docs/final-release-readiness-audit-2026-05-04.md, CHANGELOG.md, raw/docs/source-manifest-2026-05-05.md
consumes:
  - "[[codex-skill-adapter-contract]]"
  - "[[claude-plugin-marketplace-contract]]"
decisions:
  - "[[no-embeddings-mvp]]"
  - "[[graph-cluster-semantics]]"
  - "[[alpha-wiki-agentops-boundary]]"
  - "[[superpowers-adapter-not-fork]]"
  - "[[state-backend-abstraction]]"
  - "[[marketplace-topology-deferred]]"
  - "[[spawn-agent-boundary]]"
  - "[[optional-agentops-control-layer]]"
---
# Alpha-Wiki Runtime

## Provenance

- Source: README.md, docs/final-release-readiness-audit-2026-05-04.md, CHANGELOG.md.

## Provides

- Bootstrap for a typed markdown wiki in a target project.
- Deterministic graph rebuild through `tools/wiki_engine.py`.
- Structural lint/status/review/rollup tools.
- Codex plugin installation and duplicate cleanup through `scripts/install_codex.py`.
- Native Codex subagent orchestration through [[codex-skill-adapter-contract]] and [[spawn-agent-boundary]].
- Optional controlled execution memory through [[agentops-control-layer]].
- Release gates through `tools/release_audit.py` and `tools/release_smoke.py`.
- Source inventory through [[source-corpus-inventory]].
- Marketplace metadata through [[claude-plugin-marketplace-contract]].

## Consumes

- [[codex-skill-adapter-contract]]

## Decisions

- [[no-embeddings-mvp]]
- [[graph-cluster-semantics]]
- [[alpha-wiki-agentops-boundary]]
- [[superpowers-adapter-not-fork]]
- [[state-backend-abstraction]]
- [[marketplace-topology-deferred]]
- [[spawn-agent-boundary]]
- [[optional-agentops-control-layer]]

## Active tasks

- Keep release audit `READY`.
- Pilot native Codex subagent workflows on real repositories and keep the first-run path single-agent by default.
