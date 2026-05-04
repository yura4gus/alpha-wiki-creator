---
description: "Visualize wiki graph — refresh Obsidian config or export Mermaid/DOT/HTML snapshots"
argument-hint: "[obsidian | mermaid | dot | html]"
---

Invoke the `render` skill from the `alpha-wiki` plugin. Human meaning: refresh how the wiki graph is seen in Obsidian or exported views.

Mode: $ARGUMENTS (default: `obsidian`)

For `obsidian`: refresh `.obsidian/graph.json` colorGroups and `.obsidian/community-plugins.json` to match semantic graph layers: red repos/services, green modules/domains, blue features/flows, black documents, orange contracts. Idempotent — safe to re-run.

For `mermaid`: run `uv run python tools/render_mermaid.py --wiki-dir <wiki_dir>` and write `<wiki_dir>/graph/graph.mmd`.

For `dot`: run `uv run python tools/render_dot.py --wiki-dir <wiki_dir>` and write `<wiki_dir>/graph/graph.dot`.

For `html`: run `uv run python tools/render_html.py --wiki-dir <wiki_dir>` and write `<wiki_dir>/render/html/index.html`. Use `--out <dir>` when the user wants a release/shareable bundle somewhere else.
