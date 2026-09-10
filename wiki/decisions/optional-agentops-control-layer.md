---
title: Optional AgentOps Control Layer
slug: optional-agentops-control-layer
status: accepted
date: 2026-09-08
date_updated: 2026-09-08
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
supersedes: "[[alpha-wiki-agentops-boundary]]"
evidence: docs/ADR-007-optional-agentops-control-layer.md
---
# Optional AgentOps Control Layer

## Provenance

- Source: `docs/ADR-007-optional-agentops-control-layer.md`.

## Context

Large projects need controlled multi-track execution, but Alpha-Wiki must stay
useful as simple repo-native Markdown memory for small projects.

## Decision

Alpha-Wiki includes an optional AgentOps v0.2 control layer under
`wiki/agentops/`. It uses native Claude/Codex agents and deterministic Markdown
tools for goals, tracks, backlog, sessions, handoffs, decisions, and project
release checks. Normal init does not create AgentOps state.

## Consequences

- Twelve core workflows remain the normal first-run path.
- Four optional workflows add orchestrate, backlog, handoff, and release-check.
- No second agent runtime, raw-log store, RAG system, or external orchestrator is introduced.
- [[agentops-control-layer]] defines the executable schema and lifecycle.
