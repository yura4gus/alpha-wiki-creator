---
description: "Visualize wiki graph — refresh Obsidian colors/config or export Mermaid/DOT graph QA snapshots"
argument-hint: "[obsidian | mermaid | dot | html]"
---

Invoke the `render` skill from the `alpha-wiki` plugin. Human meaning: refresh how the wiki graph is seen in Obsidian or exported views.

Mode: $ARGUMENTS (default: `obsidian`)

For `obsidian`: refresh `.obsidian/graph.json` colorGroups and `.obsidian/community-plugins.json` to match semantic graph layers: red repos/services, green modules/domains, blue features/flows, black documents, orange contracts. Idempotent — safe to re-run.

For `mermaid`: run `uv run python tools/render_mermaid.py --wiki-dir <wiki_dir>` and write `<wiki_dir>/graph/graph.mmd`.

For `dot`: run `uv run python tools/render_dot.py --wiki-dir <wiki_dir>` and write `<wiki_dir>/graph/graph.dot`.

For `html`: render a static site to `dist/wiki/` (v0.2 — refuse with a pointer to `references/concept.md` until shipped).
