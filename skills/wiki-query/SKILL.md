---
name: wiki-query
description: Use when the user asks a question that should be answered from the wiki rather than from general knowledge or the codebase. Triggers include "ask the wiki", "what does the wiki say about X", "summarize what we know about X", "find pages about X", "what decisions were made about X". Use after at least one `/wiki-ingest` has populated the wiki.
---

# wiki-query — ask the wiki

## Process

1. Read `<wiki_dir>/graph/context_brief.md` (loaded by session-start hook anyway).
2. Read `<wiki_dir>/index.md` to find candidate pages.
3. Identify 3-7 pages most relevant to the question. Read them.
4. Synthesize an answer that:
   a. Cites pages by `[[slug]]`.
   b. Distinguishes between settled facts (status: stable/accepted) and open questions.
   c. Flags contradictions if any.
5. Offer to save the answer to `<wiki_dir>/outputs/<slug>.md` (a fresh page) or as a section in an existing summary page.
6. Append `<wiki_dir>/log.md`: `## [date] query | <question excerpt> | answered from <N> pages`.

## When to save

- One-off conversational answer → don't save.
- Synthesis the user will reference later → save under `outputs/`.
- Update to an existing finding → suggest editing the existing page via `/wiki-ingest` or manual edit (then `/wiki-lint`).

## References

- `references/concept.md` — Karpathy's claim that index.md is sufficient up to ~100 sources
