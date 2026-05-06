---
description: "Ask / Find in wiki — answer a human question from cited wiki pages"
argument-hint: "<question>"
---

Invoke the `query` skill from the `alpha-wiki` plugin. Human meaning: ask the maintained wiki, not the open web, and answer only from cited pages.

$ARGUMENTS

Run: `uv run python -m tools.wiki_search --wiki-dir <wiki_dir> --query "$ARGUMENTS"`

Use the deterministic report to identify relevant pages and citations. Then synthesize the final answer from those cited pages only. Distinguish settled facts from open questions. Offer to save the answer to `<wiki_dir>/outputs/` only if the user asks for a reusable artifact. Do not append to `log.md` unless a file is written.
