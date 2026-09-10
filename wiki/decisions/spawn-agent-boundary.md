---
title: Spawn Agent Boundary
slug: spawn-agent-boundary
status: accepted
date: 2026-04-29
date_updated: 2026-07-29
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-006-spawn-agent-boundary.md, skills/spawn-agent/SKILL.md, references/codex-subagent-orchestration.md
---
# Spawn Agent Boundary

## Provenance

- Source: docs/ADR-006-spawn-agent-boundary.md.
- Source: skills/spawn-agent/SKILL.md, references/codex-subagent-orchestration.md.

## Context

Alpha-Wiki has `/alpha-wiki:spawn-agent` for wiki-aware subagents. AgentOps has `agent-skills-bootstrap` for team-role agents. The names overlap conceptually, so the boundary must be explicit.

## Decision

Alpha-Wiki `spawn-agent` remains wiki-scoped only. For Codex it either creates a reusable profile or runs native Codex subagents in bounded `run-now` / `run-parallel` modes. It does not implement a separate scheduler or agent runtime.

AgentOps owns team-role logic and may use Alpha-Wiki `spawn-agent` only as a registration helper when Alpha-Wiki is installed.

## Consequences

- Alpha-Wiki never becomes the AgentOps team bootstrapper.
- AgentOps does not reimplement wiki mutability rules.
- Standalone Alpha-Wiki users can still create wiki-aware subagents without AgentOps.
- The controller owns deterministic tool execution, snapshot pinning, synthesis, and shared-file writes.
- Subagents do not spawn nested agents and return evidence through one stable result envelope.
- Boundary tests must prevent team-role names from leaking into Alpha-Wiki `spawn-agent`.
