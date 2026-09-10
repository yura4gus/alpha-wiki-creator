---
title: AgentOps Control Layer
slug: agentops-control-layer
kind: operational-spec
status: beta
date_updated: 2026-09-08
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v0.2
evidence: references/agentops-control-layer.md
---
# AgentOps Control Layer

## Provenance

- Source: `references/agentops-control-layer.md` and
  `docs/ADR-007-optional-agentops-control-layer.md`.

## Entities

- Orchestrator, track, agent role, session, handoff, decision, backlog item, and release.
- Eight role declarations: CTO, Architect, Backend, Frontend, DevOps, QA, Documentation, Release.
- Backlog items are one Markdown file per task; session and handoff records are concise summaries.

## Requirements

- AgentOps is enabled only by an explicit `orchestrate init` operation.
- All state remains under `wiki/agentops/`; core Alpha-Wiki works without it.
- Native subagents receive a pinned snapshot, bounded scope, permissions, evidence format, and terminal status.
- The controller uses two to four agents by default and six only when explicitly requested.
- Governance reports exactly `GREEN`, `WARNING`, or `BLOCKED`.
- Backlog, handoff, session, rollup, and project release checks are deterministic.
- No raw logs, autonomous daemon, external orchestrator, RAG, embeddings, or SaaS UI.

## Links

- Decision: [[optional-agentops-control-layer]]
- Runtime: [[alpha-wiki-runtime]]
