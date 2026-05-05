---
title: Alpha-Wiki Init Operation
slug: alpha-wiki-init-operation
kind: operation-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/init.md, skills/init/SKILL.md
---
# Alpha-Wiki Init Operation

## Provenance

- Source: commands/init.md.
- Source: skills/init/SKILL.md.

## Entities

- Operation: `/alpha-wiki:init` / `$alpha-wiki-init`.
- Runtime output: `raw/`, `wiki/`, `CLAUDE.md`, graph artifacts, optional hooks, CI, and `wiki/.obsidian/` config.
- Deterministic tool: `tools/init_audit.py`.

## Requirements

- Use init only when durable project memory should be established.
- Inspect the existing repo before writing files.
- Produce a source corpus plan: candidate documents, raw placement, wiki structure, and ingest batches.
- Preserve protected project files unless the user explicitly approves merge behavior.
- Verify immediately with init audit, lint, graph rebuild, doctor, and status.
- Hand content conversion to [[alpha-wiki-ingest-operation]] after bootstrap.

## Gates

- User confirms preset, overlay, visible `wiki/` vault path, hooks, CI, schema evolution mode, and source migration mode.
- Existing protected files trigger safe-existing mode.
- Schema changes remain gated.
