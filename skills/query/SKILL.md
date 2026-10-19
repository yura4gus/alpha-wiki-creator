---
name: query
description: "Answer questions from the wiki using explicit markdown evidence. Use when the user asks what the project knows, why a decision was made, what changed, what is stale, or where related pages are. Do not use as generic web search or as a substitute for ingesting durable new material."
---

# wiki:query - ask the wiki

## Mission

Synthesize answers from maintained wiki memory with citations, uncertainty labels, and follow-up actions. Query should make the wiki more useful without pretending it knows more than the files say.

## Name Contract

`query` means "read and synthesize existing wiki memory". If the answer requires new source material, say what must be ingested. If the answer should become reusable knowledge, offer to save it as an output or update a page.

## Retrieval Discipline

When supplied excerpts already answer the request, cite those excerpts and their
limits directly. Do not invent wiki pages, searches, or extra retrieval steps.
Use the following path when a wiki lookup is actually needed:

1. Start with `<wiki_dir>/graph/context_brief.md`.
2. Read `<wiki_dir>/index.md`.
3. Run `tools/wiki_search.py` for deterministic candidate ranking and line citations.
4. Use explicit filenames, slugs, wikilinks, and frontmatter. Avoid embedding-style guesses.
5. Read the smallest relevant evidence set; expand when the answer remains
   uncertain or crosses domains. A single page can be sufficient.
6. Prefer accepted/stable pages over draft/stub pages, but mention stale or draft status when it matters.

## Answer Format

Lead with a cited answer. Use only the following details needed to resolve the
question; do not turn a short lookup into a mandatory multi-section report:

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

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

1. Detect wiki dir from `AGENTS.md` or default to `wiki/`.
2. Read `context_brief.md` and `index.md`.
3. Search candidate pages by slug, title, directory, frontmatter, and body:
   - `python3 .alpha-wiki/run.py -m tools.wiki_search --wiki-dir <wiki_dir> --query "<question>"`
4. Read candidate pages deeply enough to avoid shallow summary.
5. Check for contradictions:
   - Conflicting statuses.
   - Pages using `contradicts`, `supersedes`, `superseded_by`.
   - Same concept described differently in decisions/specs.
6. Answer with citations and truth status.
7. Persist an output or page update only when requested. Mention a maintenance
   action only when a concrete evidence gap affects the answer.
8. Append log entry only when the query materially changes wiki state or writes an output.

For strict no-write requests, follow `references/concept.md` (Strict Read-Only
Operations), including the prepared-runtime and bytecode constraints. A search
result labelled `accepted` means an accepted/stable page matched; verify its
source, freshness, and applicable acceptance before treating it as approval or
runtime proof.

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

## Codex Native Delegation

Keep normal queries single-agent. Use read-only subagents only when the question
crosses independent repositories or domains and cannot be answered from the
relevant evidence set. Additional agents are not a substitute for opening the
one source that answers the question.

- The controller defines one sub-question per agent and supplies the same pinned
  snapshot when runtime evidence is involved.
- Agents return citations, truth status, contradictions, unknowns, and one
  terminal status. They do not save outputs or modify wiki pages.
- The controller reconciles duplicate or conflicting claims and returns one
  answer. Runtime evidence and ratified contracts keep their distinct authority.
- Do not use parallelism to compensate for a thin wiki; route missing durable
  knowledge to ingest instead.

Follow `references/codex-subagent-orchestration.md`.

## Done Criteria

- Answer is grounded in pages read.
- Uncertainty is explicit.
- Stale/open/conflicting material is not hidden.
- User knows whether to ingest, lint, evolve, or leave the wiki unchanged.

## References

- `references/concept.md`
- `references/cross-reference-rules.md`
- `references/codex-subagent-orchestration.md`
- `tools/wiki_search.py`
