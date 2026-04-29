---
description: "Refresh the wiki's visual layer — Obsidian config or static HTML"
argument-hint: "[obsidian | html]"
---

Invoke the `render` skill from the `alpha-wiki` plugin.

Mode: $ARGUMENTS (default: `obsidian`)

For `obsidian`: refresh `.obsidian/graph.json` colorGroups and `.obsidian/community-plugins.json` to match current preset+overlay. Idempotent — safe to re-run.

For `html`: render a static site to `dist/wiki/` (v0.2 — refuse with a pointer to `references/concept.md` until shipped).
