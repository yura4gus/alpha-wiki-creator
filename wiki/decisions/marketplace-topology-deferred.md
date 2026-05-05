---
title: Marketplace Topology Deferred
slug: marketplace-topology-deferred
status: accepted
date: 2026-04-29
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/ADR-005-marketplace-topology-deferred.md
---
# Marketplace Topology Deferred

## Provenance

- Source: docs/ADR-005-marketplace-topology-deferred.md.

## Context

Alpha-Wiki already exists as `yura4gus/alpha-wiki-creator`. AgentOps is a separate planned plugin. The packaging topology should avoid disrupting existing users.

## Decision

For Phase 1, keep Alpha-Wiki as its current standalone repository and create AgentOps as a separate plugin repository.

Do not create an umbrella marketplace yet. Revisit an umbrella listing in Phase 5 after both plugins are stable and demand is proven.

## Consequences

- No rename, relocation, or repo restructuring for Alpha-Wiki.
- Users install Alpha-Wiki and AgentOps independently.
- Future marketplace topology remains an explicit deferred decision rather than an accidental coupling.

