---
title: Spawn Agent Boundary
slug: spawn-agent-boundary
status: accepted
date: 2026-04-29
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-006-spawn-agent-boundary.md
---
# Spawn Agent Boundary

## Provenance

- Source: docs/ADR-006-spawn-agent-boundary.md.

## Context

Alpha-Wiki has `/alpha-wiki:spawn-agent` for wiki-aware subagents. AgentOps has `agent-skills-bootstrap` for team-role agents. The names overlap conceptually, so the boundary must be explicit.

## Decision

Alpha-Wiki `spawn-agent` remains wiki-scoped only. It generates subagents that understand wiki mutability and page rules.

AgentOps owns team-role logic and may use Alpha-Wiki `spawn-agent` only as a registration helper when Alpha-Wiki is installed.

## Consequences

- Alpha-Wiki never becomes the AgentOps team bootstrapper.
- AgentOps does not reimplement wiki mutability rules.
- Standalone Alpha-Wiki users can still create wiki-aware subagents without AgentOps.
- Boundary tests must prevent team-role names from leaking into Alpha-Wiki `spawn-agent`.

