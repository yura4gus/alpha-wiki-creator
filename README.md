# wiki

> LLM-maintained wiki as persistent agent memory — Karpathy + OmegaWiki, in your repo.

A Claude Code plugin that bootstraps a structured, lint-enforced markdown wiki into any project. Agents read, write, and grow it across sessions. Three layers, typed cross-links, no embeddings, no surprises.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![CI](https://github.com/yura4gus/alpha-wiki-creator/actions/workflows/plugin-ci.yml/badge.svg)](https://github.com/yura4gus/alpha-wiki-creator/actions)

---

## Why

RAG hides things. Embeddings drift. Plain markdown with `[[wikilinks]]` doesn't. Karpathy's 2025 LLM-Wiki insight: a curated index plus typed cross-references is enough up to ~100 sources — and reads transparently. OmegaWiki extends this with bidirectional enforcement, typed edges, and lint discipline. `wiki` ships both, plus presets, architectural overlays, and schema evolution that grows with the project.

## Install

One command:

```bash
claude plugins marketplace add yura4gus/alpha-wiki-creator
claude plugins install alpha-wiki
```

Requires Python 3.12+ and `uv` (`pipx install uv` if missing).

Then in any project:

```
/alpha-wiki:init
```

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                          Target Project                         │
│                                                                 │
│  ┌──────────┐     ┌─────────────────┐     ┌────────────────┐  │
│  │   raw/   │ ──> │     wiki/       │ <── │   CLAUDE.md    │  │
│  │ (L1)     │     │   (L2 + L3)     │     │   (L4 schema)  │  │
│  │ sources  │     │ pages + graph/  │     │ contract       │  │
│  │ read-    │     │ LLM-mutable     │     │ for the agent  │  │
│  │ only     │     │ + auto-derived  │     │                │  │
│  └──────────┘     └─────────────────┘     └────────────────┘  │
│        ▲                  ▲                       ▲             │
│        │                  │                       │             │
│        │ ingest           │ query/lint            │ evolve     │
│        │                  │                       │             │
│  ┌─────┴──────────────────┴───────────────────────┴───────┐    │
│  │              .claude/hooks/  (session + git + CI)       │    │
│  │  session-start: load context_brief.md                   │    │
│  │  pre/post-tool-use: validate + rebuild graph            │    │
│  │  session-end: lint + log + summary                      │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
                       ┌─────────┴──────────┐
                       │  wiki plugin       │
                       │  /alpha-wiki:init        │
                       │  /alpha-wiki:ingest      │
                       │  /alpha-wiki:query       │
                       │  /alpha-wiki:lint        │
                       │  /alpha-wiki:evolve      │
                       │  /alpha-wiki:status      │
                       │  /alpha-wiki:spawn-agent │
                       │  /alpha-wiki:render      │
                       └────────────────────┘
```

## Features

- **Three-layer mutability** — raw (read-only), wiki (LLM-mutable), schema (gated)
- **5 domain presets** — software-project (default), research, product, personal, knowledge-base, custom
- **4 architectural overlays** — clean, hexagonal, ddd (combinable), layered
- **Typed cross-references** — bidirectional enforcement, lint flags missing reverses
- **Schema evolution** — new entity types added through ingest, never preempted
- **Auto-generated context** — `wiki/graph/context_brief.md` (≤8000 chars) loaded at every session start
- **Obsidian-compatible** — `.obsidian/` config generated, graph view works out of the box
- **Deterministic engine** — `tools/lint.py` + `tools/wiki_engine.py` are pure Python, no LLM, fully tested
- **Schema-evolution gate** — every new entity type confirmed before added (or auto-mode if you trust)
- **CI-ready** — weekly `/alpha-wiki:review`, monthly `/alpha-wiki:rollup` via headless Claude

## Workflow

```
1. /alpha-wiki:init           Bootstrap (interview → render → first commit)
2. /alpha-wiki:ingest <path>  Raw artifact (PRD, ADR, OpenAPI spec, …) → wiki page(s)
3. /alpha-wiki:query <q>      Synthesize an answer from wiki pages
4. /alpha-wiki:lint --fix     Apply safe corrections (missing reverses, etc.)
5. /alpha-wiki:status         Health report — staleness, gaps, recent activity
6. /alpha-wiki:evolve <type>  Add a new entity type to the schema
7. /alpha-wiki:spawn-agent    Add a wiki-aware subagent
8. /alpha-wiki:render         Refresh Obsidian config or generate static HTML
```

The `session-start` hook auto-loads `context_brief.md` so the agent has compressed context for free.
The `session-end` hook runs lint and appends a log entry. Most users never invoke `/alpha-wiki:lint` manually.

## Skills

| Slash command | Purpose |
|---|---|
| `/alpha-wiki:init` | Bootstrap wiki + scaffolding into the current project |
| `/alpha-wiki:ingest` | raw → wiki page(s); triggers schema-evolve if no slot fits |
| `/alpha-wiki:query` | Ask the wiki; synthesize from index + relevant pages |
| `/alpha-wiki:lint` | Structural validation (broken links, missing reverses, orphans, dependency rules) |
| `/alpha-wiki:status` | Health report — recent activity, stale pages, gaps, schema-evolution log |
| `/alpha-wiki:evolve` | Add a new entity type to the schema |
| `/alpha-wiki:spawn-agent` | Generate a wiki-aware subagent |
| `/alpha-wiki:render` | Refresh Obsidian config or render static HTML |

## Reading the Obsidian graph

The bootstrap ships a default `.obsidian/graph.json` with **color groups** so the graph view tells a story at a glance:

| Color | Meaning |
|---|---|
| 🔴 Red | Service / repo / top-level architectural unit (`modules/`, `bounded-contexts/`, `application/`) |
| 🟢 Green | Module / sub-component within a service (`components/`, `core/`, `ports/`, `domains/`, `use-cases/`) |
| ⚫ Dark grey | Document — decisions, specs, concepts, APIs, papers, claims, summaries, etc. |
| 🟠 Orange | Contract — REST/GraphQL/gRPC/events at service boundaries (`contracts/`) |
| ⚪ Light grey | People / tasks — meta layer |

A red node with many grey edges = a service that has accumulated decisions and specs. A green cluster around a red node = a service with multiple modules. An orange node bridging two reds = a contract owned by one, consumed by the other. Isolated red node = service with no docs (lint flags this as a maintenance gap).

Customize: edit `.obsidian/graph.json` → `colorGroups` array. Full legend at `.obsidian/COLOR-LEGEND.md` after bootstrap.

## Design

Full spec: [`docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`](docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md)
Implementation plan: [`docs/superpowers/plans/2026-04-28-wiki-creator-implementation.md`](docs/superpowers/plans/2026-04-28-wiki-creator-implementation.md)
References:
- Karpathy's LLM Wiki gist — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- OmegaWiki — https://github.com/skyllwt/OmegaWiki

## Development

```bash
git clone https://github.com/yura4gus/alpha-wiki-creator
cd alpha-wiki-creator
uv sync --dev
.venv/bin/python -m pytest
```

45 tests across unit + integration.

## License

MIT
