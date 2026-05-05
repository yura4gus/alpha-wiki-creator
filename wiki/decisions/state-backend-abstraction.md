---
title: State Backend Abstraction
slug: state-backend-abstraction
status: accepted
date: 2026-04-29
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-004-state-backend-abstraction.md
---
# State Backend Abstraction

## Provenance

- Source: docs/ADR-004-state-backend-abstraction.md.

## Context

AgentOps needs persistent markdown state whether or not Alpha-Wiki is installed. If Alpha-Wiki is present, AgentOps must avoid colliding with Alpha-Wiki root namespace.

## Decision

AgentOps writes under exactly one subnamespace:

- `wiki/agentops/` when Alpha-Wiki is present.
- `docs/agentops/` when Alpha-Wiki is absent.

The internal structure under `agentops/` remains identical in both cases.

## Consequences

- Alpha-Wiki keeps ownership of root-level wiki directories.
- AgentOps can migrate from fallback docs into Alpha-Wiki through one directory move.
- Integration tests must catch any AgentOps write outside its namespace.
- The detailed contract is summarized in [[state-backend-contract]].

