---
title: Codex Skill Adapter Contract
slug: codex-skill-adapter-contract
transport: rpc
service: "[[alpha-wiki-runtime]]"
consumers: "[[alpha-wiki-runtime]]"
version: v1
status: stable
date_updated: 2026-05-05
evidence: scripts/install_codex.py, docs/codex-adapter.md
---
# Codex Skill Adapter Contract

## Provenance

- Source: scripts/install_codex.py, docs/codex-adapter.md.

## Contract

`scripts/install_codex.py` transforms each Alpha-Wiki skill into a prefixed Codex skill under `$CODEX_HOME/skills`.

## Consumers

- [[alpha-wiki-runtime]]

## Migration notes

- Initial v1 contract. No migration required.
