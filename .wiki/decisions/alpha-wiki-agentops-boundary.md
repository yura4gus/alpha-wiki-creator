---
title: Alpha-Wiki AgentOps Boundary
slug: alpha-wiki-agentops-boundary
status: accepted
date: 2026-04-29
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-001-alpha-wiki-agentops-boundary.md
---
# Alpha-Wiki AgentOps Boundary

## Provenance

- Source: docs/ADR-001-alpha-wiki-agentops-boundary.md.

## Context

Alpha-Wiki and AgentOps both persist project state, but they serve different product layers. A clean boundary prevents a monolithic plugin and keeps both products independently installable.

## Decision

Alpha-Wiki owns the wiki memory layer: raw/wiki/schema mutability, page lifecycle, schema evolution, structural lint, graph artifacts, Obsidian/static rendering, and wiki-scoped queries.

AgentOps owns the agent operating model: roles, communication mechanisms, process rhythms, review levels, architecture canon, state backend abstraction, and the `agentops/` subnamespace.

## Consequences

- Alpha-Wiki never imports AgentOps.
- AgentOps may use Alpha-Wiki as an optional state backend through a namespaced adapter.
- Shared installs keep AgentOps state under `wiki/agentops/`, not at wiki root.
- Each plugin can be tested, released, and upgraded independently.

