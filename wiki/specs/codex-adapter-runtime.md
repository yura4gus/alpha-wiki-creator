---
title: Codex Adapter Runtime
slug: codex-adapter-runtime
kind: adapter
status: stable
date_updated: 2026-09-08
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/codex-adapter.md, scripts/install_codex.py, tests/unit/test_install_codex.py
---
# Codex Adapter Runtime

## Provenance

- Source: docs/codex-adapter.md, scripts/install_codex.py, tests/unit/test_install_codex.py.

## Entities

- `$alpha-wiki:*` plugin skill namespace.
- `scripts/install_codex.py`.
- `.codex/hooks.json` and the Alpha-Wiki hook adapter.
- `references/codex-subagent-orchestration.md`.
- Repository-local deterministic tools.

## Requirements

- Install exactly 16 Alpha-Wiki plugin skills: 12 core and 4 optional AgentOps workflows.
- Use plugin-only mode by default; standalone fallback skills must not coexist with the plugin.
- Exclude Claude `commands/` from the Codex package.
- Preserve Claude slash-command equivalents in adapter notes.
- Use native Codex subagents for bounded evidence collection and keep deterministic tools in the controller.
- Inject the common snapshot, truth-precedence, write-ownership, and result-envelope contract at `SubagentStart`.
- Keep platform support honest: Claude and Codex have different command and hook surfaces.

## Current Evidence

- The Codex package is installed through the local `plugins-cli` marketplace.
- Doctor verifies 16 plugin skills, no standalone or legacy duplicates, no packaged Claude commands, marketplace activation, project instructions, and the session/subagent/tool/session-end hook lifecycle.
- `spawn-agent` supports `create-profile`, `run-now`, and bounded `run-parallel` modes without creating a second agent runtime.
- Optional AgentOps uses the same native subagents and stores only summarized execution memory under `wiki/agentops/`.
