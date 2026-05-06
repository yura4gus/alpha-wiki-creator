---
name: query
description: "Answer questions from the wiki using explicit markdown evidence. Use when the user asks what the project knows, why a decision was made, what changed, what is stale, or where related pages are. Do not use as generic web search or as a substitute for ingesting durable new material."
argument-hint: "<question>"
---

# wiki:query - ask the wiki

## Mission

Synthesize answers from maintained wiki memory with citations, uncertainty labels, and follow-up actions. Query should make the wiki more useful without pretending it knows more than the files say.

## Name Contract

`query` means "read and synthesize existing wiki memory". If the answer requires new source material, say what must be ingested. If the answer should become reusable knowledge, offer to save it as an output or update a page.

## Retrieval Discipline

1. Start with `<wiki_dir>/graph/context_brief.md`.
2. Read `<wiki_dir>/index.md`.
3. Run `tools/wiki_search.py` for deterministic candidate ranking and line citations.
4. Use explicit filenames, slugs, wikilinks, and frontmatter. Avoid embedding-style guesses.
5. Select 3-7 relevant pages for normal questions; expand only when the topic crosses domains.
6. Prefer accepted/stable pages over draft/stub pages, but mention stale or draft status when it matters.

## Answer Format

Use this structure unless the user asked for something smaller:

- Short answer.
- Evidence: cite pages as `[[slug]]` and include file paths when precision matters.
- Truth status:
  - `accepted`: explicitly recorded and current.
  - `assumption`: plausible but not decided.
  - `risk`: recorded risk or unresolved tradeoff.
  - `open`: explicit open question or missing page.
  - `stale`: page date/status suggests caution.
- Related pages.
- Suggested next action: ingest, lint, evolve, review, or no action.

## Workflow

1. Detect wiki dir from `CLAUDE.md` or default to `wiki/`.
2. Read `context_brief.md` and `index.md`.
3. Search candidate pages by slug, title, directory, frontmatter, and body:
   - `uv run python -m tools.wiki_search --wiki-dir <wiki_dir> --query "<question>"`
4. Read candidate pages deeply enough to avoid shallow summary.
5. Check for contradictions:
   - Conflicting statuses.
   - Pages using `contradicts`, `supersedes`, `superseded_by`.
   - Same concept described differently in decisions/specs.
6. Answer with citations and truth status.
7. If the answer is reusable, offer one of:
   - Save to `<wiki_dir>/outputs/<slug>.md`.
   - Update an existing page via `/alpha-wiki:ingest`.
   - Create an open question entry.
8. Append log entry only when the query materially changes wiki state or writes an output.

## Graph Hygiene

- Do not create new pages during query unless the user explicitly asks to save the synthesis.
- If saving an output, link it to source pages so it is not an orphan.
- If the answer reveals a missing page, suggest ingest/evolve instead of inventing memory.

## Teaching Behavior

When the wiki is thin, explain how to make the next query better:

- "Ingest the PRD first."
- "Add owner/status/date_updated to this page."
- "This should be a contract page so it becomes orange in Obsidian."
- "This service is isolated in the graph; link it to decisions/specs."

## Done Criteria

- Answer is grounded in pages read.
- Uncertainty is explicit.
- Stale/open/conflicting material is not hidden.
- User knows whether to ingest, lint, evolve, or leave the wiki unchanged.

## References

- `references/concept.md`
- `references/cross-reference-rules.md`
- `tools/wiki_search.py`
