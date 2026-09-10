---
title: Codex Skill Adapter Contract
slug: codex-skill-adapter-contract
transport: rpc
service: "[[alpha-wiki-runtime]]"
consumers: "[[alpha-wiki-runtime]]"
version: v1
status: stable
date_updated: 2026-09-08
evidence: scripts/install_codex.py, docs/codex-adapter.md, references/codex-subagent-orchestration.md
---
# Codex Skill Adapter Contract

## Provenance

- Source: scripts/install_codex.py, docs/codex-adapter.md, references/codex-subagent-orchestration.md.

## Contract

`scripts/install_codex.py` packages exactly 16 Alpha-Wiki skills as one Codex plugin and activates it through the local marketplace. Twelve are core memory workflows; four are optional AgentOps workflows. Claude `commands/` are excluded. Standalone skills are compatibility fallback only and must not coexist with the active plugin.

Codex subagent runs use the native Codex runtime. The controller pins one repository snapshot, assigns disjoint read/write ownership, waits for terminal results, rejects stale evidence, and preserves deterministic Alpha-Wiki tools as the source of truth.

## Consumers

- [[alpha-wiki-runtime]]

## Migration notes

- Upgrade with `python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone` to remove duplicate legacy/fallback surfaces.
