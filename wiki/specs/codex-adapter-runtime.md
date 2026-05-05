---
title: Codex Adapter Runtime
slug: codex-adapter-runtime
kind: adapter
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/codex-adapter.md, scripts/install_codex.py, tests/unit/test_install_codex.py
---
# Codex Adapter Runtime

## Provenance

- Source: docs/codex-adapter.md, scripts/install_codex.py, tests/unit/test_install_codex.py.

## Entities

- `$alpha-wiki-*` skill namespace.
- `scripts/install_codex.py`.
- Repository-local deterministic tools.

## Requirements

- Install exactly 11 prefixed Codex skills.
- Preserve Claude slash-command equivalents in adapter notes.
- Keep Codex support honest: skills and deterministic tools are supported; Claude hooks are not equivalent.

## Current Evidence

- Installed in `/Users/yuragus/.codex/skills`.
- Expected skills include `$alpha-wiki-init`, `$alpha-wiki-doctor`, `$alpha-wiki-ingest`, `$alpha-wiki-query`, `$alpha-wiki-lint`, `$alpha-wiki-status`, `$alpha-wiki-review`, and `$alpha-wiki-rollup`.
