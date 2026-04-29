---
description: "Ask the wiki — synthesize an answer from index + relevant pages"
argument-hint: "<question>"
---

Invoke the `query` skill from the `alpha-wiki` plugin to answer the following question from the wiki:

$ARGUMENTS

Read `<wiki_dir>/graph/context_brief.md` and `<wiki_dir>/index.md`, identify 3-7 relevant pages, read them, synthesize an answer that cites pages by `[[slug]]`. Distinguish settled facts from open questions. Offer to save the answer to `<wiki_dir>/outputs/` if it's worth referencing later. Append a `query` entry to `<wiki_dir>/log.md`.
