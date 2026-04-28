# Karpathy LLM Wiki — original gist (excerpt)

Source: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Three layers

- `raw/` — immutable inputs (papers, transcripts, web saves)
- `wiki/` — LLM-curated markdown with `[[wiki-links]]`
- `CLAUDE.md` — runtime instructions for the agent

## Three operations

- `ingest` — agent reads raw → produces or updates wiki pages
- `query` — agent reads index.md and relevant pages → answers
- `lint` — structural sanity check (broken links, missing pages)

## Two service files

- `wiki/index.md` — catalog (table of contents, YAML-style)
- `wiki/log.md` — append-only diary of operations

## Karpathy's claim

For most projects, this is enough. RAG/embeddings introduce opacity; markdown + a good
index reads with no surprises. Vector search becomes useful only past ~100 sources.

## What we keep

All of it. wiki-creator preserves Karpathy's spirit while adding production-grade
extensions from OmegaWiki (typed entities, edges, bidirectional enforcement).
