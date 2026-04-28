---
name: ingest
description: Use when the user wants to add new sources (papers, docs, transcripts, OpenAPI specs, ADRs, etc.) into an existing wiki. Triggers include "ingest this", "add to wiki", "process raw/", "import these docs", "feed this into the wiki". Use after `/wiki:init` has bootstrapped the wiki. Skip for one-off summaries that won't be persisted.
---

# wiki:ingest — raw artifact → wiki page(s)

## Process

1. Validate target paths exist (under `raw/` or absolute paths).
2. For each path:
   a. Run `tools/classify.py` to determine artifact kind.
   b. Match to existing slot in `CLAUDE.md` page types.
   c. If no match:
      - **gated mode** → propose options: (a) new top-level type, (b) sub-folder under existing layer, (c) section append on related page. Wait for user.
      - **auto mode** → pick best default and proceed (write `[schema-change]` log).
   d. If a new type is needed → invoke `/wiki:evolve <type>`.
   e. Render page from frontmatter template + artifact body. Use the entity type's required sections.
   f. Compute forward links from content; let `wiki_engine.add_edge --bidirectional` write reverse links automatically.
   g. Update `<wiki_dir>/index.md` (auto section for the page type).
   h. Append to `<wiki_dir>/log.md`: `## [date] ingest | <path> → <slot>`.
3. After all ingests:
   a. `uv run python tools/wiki_engine.py rebuild-edges --wiki-dir <wiki_dir>`
   b. `uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir <wiki_dir>`
   c. `uv run python tools/wiki_engine.py rebuild-open-questions --wiki-dir <wiki_dir>`
4. Run `tools/lint.py --suggest` and surface findings to user.

## Stub creation

If a forward link target doesn't exist yet, `pre-tool-use` creates a stub with `status: stub` and a TODO. The stub is logged. Don't block the ingest on this — a follow-up ingest can fill the stub.

## References

- `references/classifier.md` — artifact taxonomy
- `references/schema-evolution.md` — evolve flow
- `references/cross-reference-rules.md` — bidirectional canon
