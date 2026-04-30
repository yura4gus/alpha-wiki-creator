---
description: "Visualize wiki graph — refresh Obsidian colors/config or static exports"
argument-hint: "[obsidian | html]"
---

Invoke the `render` skill from the `alpha-wiki` plugin. Human meaning: refresh how the wiki graph is seen in Obsidian or exported views.

Mode: $ARGUMENTS (default: `obsidian`)

For `obsidian`: refresh `.obsidian/graph.json` colorGroups and `.obsidian/community-plugins.json` to match semantic graph layers: red repos/services, green modules/domains, blue features/flows, black documents, orange contracts. Idempotent — safe to re-run.

For `html`: render a static site to `dist/wiki/` (v0.2 — refuse with a pointer to `references/concept.md` until shipped).
