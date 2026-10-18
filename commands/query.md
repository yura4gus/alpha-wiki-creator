---
description: "Ask / Find in wiki — answer a human question from cited wiki pages"
argument-hint: "<question>"
---

Invoke the `query` skill from the `alpha-wiki` plugin. Human meaning: answer from
relevant cited project memory or supplied evidence, keeping their sources clear.

$ARGUMENTS

When a wiki lookup is needed, run:
`python3 .alpha-wiki/run.py -m tools.wiki_search --wiki-dir <wiki_dir> --query "$ARGUMENTS"`

Use the smallest sufficient evidence set. If supplied excerpts already answer
the question, cite them without inventing a wiki search or extra reading.
Preserve uncertainty and return a concise answer. Save an artifact only when
requested; append to `log.md` only when a file is written.
