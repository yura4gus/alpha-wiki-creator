# Alpha-wiki

> **Agent memory that compounds — in plain markdown, in your repo.**

A Claude Code plugin that turns Andrej Karpathy's LLM-Wiki sketch into a production runtime. Agents read, write, and grow a typed, lint-enforced markdown knowledge base across sessions. No embeddings. No vector store. No drift. Just files your team can read, diff, and review.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![CI](https://github.com/yura4gus/alpha-wiki-creator/actions/workflows/plugin-ci.yml/badge.svg)](https://github.com/yura4gus/alpha-wiki-creator/actions)

---

## Why Alpha-wiki

LLM agents forget. RAG hides what they remember. Embeddings drift silently and obscure why a retrieval landed. **Plain markdown with `[[wikilinks]]` doesn't have these problems** — but raw markdown alone is undisciplined: pages go stale, links rot, structure entropies.

Alpha-wiki gives the wiki a **runtime contract** — typed entities, required frontmatter, bidirectional links the lint enforces, automated hooks that load compressed context at session start and run lint at session end. The result: **agent memory that compounds week-over-week instead of decaying.**

Use it for engineering projects (decisions, modules, contracts, ADRs), research (papers, claims, experiments), product (features, personas, flows), or as a personal knowledge base. Five domain presets plus four architectural overlays (clean / hexagonal / DDD / layered) ship out of the box, and the schema **evolves through ingest** — new entity types are proposed, not preempted.

## What's different from Karpathy's LLM-Wiki

Karpathy's 2025 [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) sketched the idea in ~80 lines: three layers (raw / wiki / CLAUDE.md), three operations (ingest / query / lint), two service files (index.md / log.md). It is a beautiful sketch. Alpha-wiki is the production extension.

| Karpathy's gist (sketch) | Alpha-wiki (runtime) |
|---|---|
| 3 untyped layers | Same 3 layers, made explicit as **mutability contracts** + 5 domain presets + 4 architectural overlays |
| 3 operations (ingest, query, lint) | **10 skills + 10 slash commands** — ingest, query, lint, evolve, status, spawn-agent, render, init, review, rollup |
| No frontmatter rules | **Required frontmatter per entity type**, lint-blocked on violations |
| Manual cross-links | **Bidirectional enforcement** — every forward link gets a reverse, written automatically by the engine |
| No automation | **Three-layer hooks** — session-start loads `context_brief.md`, post-tool-use rebuilds the graph, session-end runs lint and appends a log entry, pre-commit blocks 🔴 errors, weekly CI review |
| Static index.md | **Auto-generated graph layer** — `edges.jsonl`, `context_brief.md` (≤8000 chars, loaded into every session for free), `open_questions.md` |
| Bring your own UI | **Obsidian-first** — `.obsidian/` config ships with semantic color groups (🔴 repos/services, 🟢 modules/domains, 🔵 features/flows, ⚫ docs, 🟠 contracts) so the graph view reads like a system diagram |
| One-shot setup | **Schema evolution** — `/alpha-wiki:evolve` adds new entity types through ingest, gates them by default, logs every schema change |
| You write the subagents | **Subagent slot** — `/alpha-wiki:spawn-agent` generates wiki-aware Claude Code subagents that honor the mutability matrix |

In one line: **Karpathy gave the idea, Alpha-wiki gives the runtime.**

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
                       │  /alpha-wiki:review      │
                       │  /alpha-wiki:rollup      │
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
3. /alpha-wiki:query <q>      Ask/find in the wiki with cited evidence
4. /alpha-wiki:lint --fix     Check/fix structure (links, reverses, frontmatter)
5. /alpha-wiki:status         Health + mandatory Gap Check
6. /alpha-wiki:evolve <type>  Add a new entity type to the schema
7. /alpha-wiki:spawn-agent    Add a wiki-aware subagent
8. /alpha-wiki:render         Refresh Obsidian config or generate static HTML
9. /alpha-wiki:review         Weekly structural review — status + lint + next actions
10. /alpha-wiki:rollup        Weekly/monthly activity summary
```

The `session-start` hook auto-loads `context_brief.md` so the agent has compressed context for free.
The `session-end` hook runs lint and appends a log entry. Most users never invoke `/alpha-wiki:lint` manually.

## Skills

| Slash command | Purpose |
|---|---|
| `/alpha-wiki:init` | Bootstrap wiki + scaffolding into the current project |
| `/alpha-wiki:ingest` | raw → wiki page(s); triggers schema-evolve if no slot fits |
| `/alpha-wiki:query` | Ask/find in the wiki; synthesize from index + relevant cited pages |
| `/alpha-wiki:lint` | Check/fix wiki structure: links, reverses, orphans, frontmatter, dependency rules |
| `/alpha-wiki:status` | Health + Gap Check — recent activity, stale pages, structural blind spots, schema-evolution log |
| `/alpha-wiki:evolve` | Add a new entity type to the schema |
| `/alpha-wiki:spawn-agent` | Generate a wiki-aware subagent |
| `/alpha-wiki:render` | Refresh Obsidian config or render static HTML |
| `/alpha-wiki:review` | Wiki-level structural review — status snapshot, lint findings, next actions |
| `/alpha-wiki:rollup` | Weekly/monthly wiki activity rollup |

## Reading the Obsidian graph

The bootstrap ships a default `.obsidian/graph.json` with **color groups** so the graph view tells a story at a glance:

| Color | Meaning |
|---|---|
| 🔴 Red | Repo / service / top-level architectural unit (`services/`, `repos/`, `bounded-contexts/`, `applications/`) |
| 🟢 Green | Module / domain / sub-component within a service (`modules/`, `components/`, `core/`, `ports/`, `domains/`, `adapters/`) |
| 🔵 Blue | Feature / function / user-facing flow (`features/`, `flows/`, `use-cases/`, `application/`) |
| ⚫ Black | Document/evidence page — decisions, specs, concepts, APIs, papers, claims, summaries, etc. |
| 🟠 Orange | Contract — REST/GraphQL/gRPC/events at service boundaries (`contracts/`) |
| ⚪ Light grey | People / tasks — meta layer |

A red node is a repo/service boundary. A green cluster around red is the service's modules/domains/components. A blue node shows a feature or function implemented by those modules. Black nodes are documents/evidence attached to the architecture. An orange node bridging two reds is a contract owned by one service and consumed by another. Isolated red or black nodes are maintenance gaps.

Customize: edit `.obsidian/graph.json` → `colorGroups` array. Full legend at `.obsidian/COLOR-LEGEND.md` after bootstrap.

## Documentation

Current architecture set:

- [`docs/00-architecture.md`](docs/00-architecture.md) — ecosystem boundaries and plugin topology
- [`docs/01-alpha-wiki.md`](docs/01-alpha-wiki.md) — Alpha-Wiki product specification
- [`docs/02-agentops.md`](docs/02-agentops.md) — AgentOps product specification
- [`docs/03-superpowers-adapter.md`](docs/03-superpowers-adapter.md) — optional Superpowers integration contract
- [`docs/04-state-backend-contract.md`](docs/04-state-backend-contract.md) — state backend abstraction
- [`docs/roadmap-execution.md`](docs/roadmap-execution.md) — execution roadmap
- [`docs/implementation-plan-2026-04-30.md`](docs/implementation-plan-2026-04-30.md) — implementation plan for the current repo

Decision records:

- [`docs/ADR-001-alpha-wiki-agentops-boundary.md`](docs/ADR-001-alpha-wiki-agentops-boundary.md)
- [`docs/ADR-002-superpowers-adapter-not-fork.md`](docs/ADR-002-superpowers-adapter-not-fork.md)
- [`docs/ADR-003-no-embeddings-mvp.md`](docs/ADR-003-no-embeddings-mvp.md)
- [`docs/ADR-004-state-backend-abstraction.md`](docs/ADR-004-state-backend-abstraction.md)
- [`docs/ADR-005-marketplace-topology-deferred.md`](docs/ADR-005-marketplace-topology-deferred.md)
- [`docs/ADR-006-spawn-agent-boundary.md`](docs/ADR-006-spawn-agent-boundary.md)

Original design materials:

- [`docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`](docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md)
- [`docs/superpowers/plans/2026-04-28-wiki-creator-implementation.md`](docs/superpowers/plans/2026-04-28-wiki-creator-implementation.md)

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
