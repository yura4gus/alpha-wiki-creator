---
title: Claude Plugin Marketplace Contract
slug: claude-plugin-marketplace-contract
transport: rpc
service: "[[alpha-wiki-runtime]]"
consumers: "[[alpha-wiki-runtime]]"
version: v1
status: stable
date_updated: 2026-05-05
evidence: .claude-plugin/plugin.json, .claude-plugin/marketplace.json
---
# Claude Plugin Marketplace Contract

## Provenance

- Source: .claude-plugin/plugin.json.
- Source: .claude-plugin/marketplace.json.

## Contract

The package exposes one Claude Code plugin named `alpha-wiki`, version `0.1.0`, with repository and homepage pointing to `yura4gus/alpha-wiki-creator`.

The marketplace entry describes Alpha-Wiki as an LLM-maintained wiki bootstrap with 11 skills, typed cross-links, schema evolution, and Obsidian-compatible graph support.

## Consumers

- [[alpha-wiki-runtime]]

## Migration notes

- Initial v1 marketplace contract. At publish time, `pyproject.toml`, plugin metadata, marketplace metadata, changelog, and tag must stay aligned.

