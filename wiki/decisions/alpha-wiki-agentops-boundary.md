---
title: Alpha-Wiki AgentOps Boundary
slug: alpha-wiki-agentops-boundary
status: superseded
date: 2026-04-29
date_updated: 2026-09-08
superseded_by: "[[optional-agentops-control-layer]]"
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-001-alpha-wiki-agentops-boundary.md
---
# Alpha-Wiki AgentOps Boundary

## Provenance

- Source: docs/ADR-001-alpha-wiki-agentops-boundary.md.

## Context

This page records the historical boundary for a separate AgentOps product. The
lightweight v0.2 implementation is governed by [[optional-agentops-control-layer]].

## Decision

Alpha-Wiki owns the wiki memory layer: raw/wiki/schema mutability, page lifecycle, schema evolution, structural lint, graph artifacts, Obsidian/static rendering, and wiki-scoped queries.

AgentOps owns the agent operating model: roles, communication mechanisms, process rhythms, review levels, architecture canon, state backend abstraction, and the `agentops/` subnamespace.

## Consequences

- The large standalone AgentOps product remains outside Alpha-Wiki.
- Alpha-Wiki may expose a small opt-in control layer under `wiki/agentops/`.
- Core wiki workflows do not depend on or initialize that namespace.
