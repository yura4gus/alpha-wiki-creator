---
title: Ecosystem Plugin Architecture
slug: ecosystem-plugin-architecture
kind: architecture-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/00-architecture.md
---
# Ecosystem Plugin Architecture

## Provenance

- Source: docs/00-architecture.md.

## Entities

- Alpha-Wiki: memory and knowledge layer.
- AgentOps: agent operating model layer.
- Superpowers: optional execution discipline layer.
- Target project: host repository where the tools are installed.

## Requirements

- Alpha-Wiki must run alone and own wiki memory, schema, graph artifacts, structural lint, Obsidian/static rendering, and wiki-scoped query.
- AgentOps must run alone and own team roles, process rhythms, review levels, architecture canon, and AgentOps state.
- Superpowers remains optional and supplies process discipline when installed.
- Integrations are process-level adapters, not runtime imports.
- Slash namespaces stay separate: `/alpha-wiki:*`, `/agentops:*`, `/superpowers:*`.

## Links

- Boundary decision: [[alpha-wiki-agentops-boundary]]
- Superpowers adapter decision: [[superpowers-adapter-not-fork]]
- Marketplace decision: [[marketplace-topology-deferred]]
- Spawn-agent boundary: [[spawn-agent-boundary]]

