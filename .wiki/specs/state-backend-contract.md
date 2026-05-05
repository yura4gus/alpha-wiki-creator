---
title: State Backend Contract
slug: state-backend-contract
kind: integration-contract
status: accepted
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/04-state-backend-contract.md, docs/ADR-004-state-backend-abstraction.md
---
# State Backend Contract

## Provenance

- Source: docs/04-state-backend-contract.md.
- Decision source: docs/ADR-004-state-backend-abstraction.md.

## Entities

- State backend root.
- AgentOps `agentops/` subnamespace.
- Alpha-Wiki root wiki namespace.
- `wiki/graph/context_brief.md` as shared read context when Alpha-Wiki is present.

## Requirements

- If Alpha-Wiki is present, AgentOps state resolves to `wiki/agentops/`.
- If Alpha-Wiki is absent, AgentOps state resolves to `docs/agentops/`.
- AgentOps must not write root-level wiki directories such as `wiki/decisions/`, `wiki/contracts/`, `wiki/state/`, or `wiki/reviews/`.
- The structure under `agentops/` stays identical across both backends.
- The adapter logs backend choice and uses the same path resolver for all writes.

## Links

- Decision: [[state-backend-abstraction]]
- Boundary: [[alpha-wiki-agentops-boundary]]

