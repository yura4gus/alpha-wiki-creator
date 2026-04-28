# Concept

## Karpathy LLM Wiki (origin)

Three layers, three operations, two service files.

- **Raw** — immutable sources (read-only after capture)
- **Wiki** — LLM-generated markdown with cross-links
- **Schema** — `CLAUDE.md`, the runtime contract for the agent

Operations: `ingest`, `query`, `lint`. Service files: `index.md`, `log.md`.

Karpathy's claim: index.md is sufficient up to ~100 sources. RAG/embeddings are not needed
at small/medium scale and obscure understanding.

## OmegaWiki (production extensions)

Same three layers, but with:
- Typed entities (papers, claims, experiments, ...) with required frontmatter and sections
- Typed edge graph (`graph/edges.jsonl`) — `extends`, `contradicts`, `supports`, etc.
- Bidirectional link enforcement (forward write triggers reverse write)
- Auto-generated `graph/context_brief.md` (≤8000 chars compressed context)
- Lint with `--fix` / `--suggest` / `--dry-run`
- GitHub Actions cron (daily-arxiv equivalent in our case: weekly review)

## wiki-creator additions

- **Three-layer model = mutability contracts**, not folders
- **Domain presets** (software-project default + 4 alternatives + custom)
- **Architectural overlays** (clean, hexagonal, ddd, layered)
- **Schema evolution** through ingest (new artifact type → CLAUDE.md mutation)
- **Session-end automation** (lint + log + context_brief rebuild)
- **Sibling skill `wiki:spawn-agent`** for adding subagents

The full design spec lives at `docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`.
