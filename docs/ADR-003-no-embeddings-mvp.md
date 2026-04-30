# ADR-003 — No embeddings in MVP

**Status**: Accepted
**Date**: 2026-04-29

## Context

Wiki-style memory systems often add embedding-based retrieval to scale beyond simple file search. Karpathy's LLM-Wiki sketch explicitly recommends against this for projects up to roughly 100 sources, arguing that a content-oriented `index.md` plus targeted file reads gives better results with full transparency and no drift.

The question is whether Alpha-Wiki and AgentOps should add a vector store, embedding pipeline, or hybrid retrieval layer in the MVP.

## Decision

No embeddings. No vector store. No hybrid retrieval layer in MVP across Alpha-Wiki and AgentOps.

Retrieval is implemented as:

1. `wiki/00_index.md` and `wiki/index/*.md` — content-oriented YAML / markdown indexes maintained on every ingest.
2. Targeted file reads guided by index entries.
3. Optional BM25 keyword search over `wiki/` (Phase 6, only if proven justified).
4. `wiki/graph/context_brief.md` — auto-generated compressed context (≤8000 chars) loaded at session start.

This applies to both Alpha-Wiki query operations and AgentOps onboard/plan operations.

## Reasoning

1. **Karpathy's analysis stands.** For project knowledge bases up to ~100 sources, embedding retrieval introduces opaque ranking decisions, drift over time, and loss of provenance. Plain markdown with explicit indexes scales further than commonly assumed.
2. **Markdown is auditable.** Every retrieval path is a file path. Every fact is a line in a file. Diffs work. Code review works. Embeddings give none of this.
3. **No drift.** Re-indexing is an explicit operation, not a silent decay.
4. **No infrastructure.** No vector database to operate, no embedding model to version, no pipeline to maintain.
5. **Cheaper to verify.** Tests assert on file content, not on similarity scores.
6. **MVP scope discipline.** Adding embeddings now would expand Phase 1 by an order of magnitude with marginal benefit.

## Alternatives rejected

- **Embeddings in Alpha-Wiki MVP.** Rejected: violates Karpathy's design principle; adds infrastructure we cannot justify.
- **BM25 in MVP.** Rejected: deferred to Phase 6 only if real-world usage shows that file search is insufficient. Most projects will never hit that threshold.
- **Hybrid retrieval (BM25 + embeddings).** Rejected on the same grounds.

## Risks

- **Scaling beyond 100 sources** could degrade retrieval quality. Mitigation: schema evolution and rollup skills compress the wiki. If real usage shows degradation, BM25 is a Phase 6 candidate.
- **User expectation mismatch.** Some users may expect embedding-based retrieval. Mitigation: explicit documentation of the design choice with rationale.

## Validation

- Alpha-Wiki query skill produces useful results on test wikis up to 200 pages without embeddings.
- AgentOps onboard skill produces useful summaries from `context_brief.md` without retrieval beyond targeted reads.
- No vector store, embedding model, or external service dependency in either plugin's `pyproject.toml`.
