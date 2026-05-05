---
title: Graph Cluster Semantics
slug: graph-cluster-semantics
status: accepted
date: 2026-05-05
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
affects: "[[alpha-wiki-runtime]]"
evidence: docs/final-release-hardening-plan.md, README.md, assets/obsidian/COLOR-LEGEND.md
---
# Graph Cluster Semantics

## Provenance

- Source: docs/final-release-hardening-plan.md, README.md, assets/obsidian/COLOR-LEGEND.md.

## Context

The graph must help both operator and AI understand project structure quickly. Documents should not scatter randomly by color.

## Decision

Clusters are formed by typed links such as `belongs_to`, `service`, `implements`, `affects`, `owned_by`, and `defined_in`. Colors identify node roles inside clusters.

## Consequences

- A healthy cluster can contain mixed colors.
- Red means repo/service boundary, green module/domain, blue feature/flow, black document/evidence, orange contract.
- Color-only grouping is treated as a modeling mistake.
