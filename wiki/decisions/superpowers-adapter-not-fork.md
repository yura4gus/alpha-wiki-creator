---
title: Superpowers Adapter Not Fork
slug: superpowers-adapter-not-fork
status: accepted
date: 2026-04-29
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-002-superpowers-adapter-not-fork.md
---
# Superpowers Adapter Not Fork

## Provenance

- Source: docs/ADR-002-superpowers-adapter-not-fork.md.

## Context

Superpowers provides execution discipline that AgentOps can benefit from, but a hard dependency would reduce platform compatibility and make AgentOps less composable.

## Decision

AgentOps integrates Superpowers through a process-level adapter. It detects availability, instructs the agent to invoke Superpowers skills when present, and falls back to native AgentOps discipline when absent.

AgentOps does not fork, copy wholesale, or call Superpowers programmatically.

## Consequences

- Superpowers remains optional.
- AgentOps can run on machines without Superpowers.
- Drift is managed through defensive detection and native fallback tests.
- Alpha-Wiki remains outside this integration and only records the decision as wiki memory.

