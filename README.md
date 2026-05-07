# Alpha-wiki

> **Agent memory that compounds — in plain markdown, in your repo.**

A Claude Code plugin that turns Andrej Karpathy's LLM-Wiki sketch into a production runtime. Agents read, write, and grow a typed, lint-enforced markdown knowledge base across sessions. No embeddings. No vector store. No drift. Just files your team can read, diff, and review.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![CI](https://github.com/yura4gus/alpha-wiki-creator/actions/workflows/plugin-ci.yml/badge.svg)](https://github.com/yura4gus/alpha-wiki-creator/actions)

---

## Release status

Alpha-Wiki is ready as a **v0.1 release candidate** for real Claude Code and Codex pilots.

Current verified gates:

- Fresh install smoke: `init -> doctor -> ingest -> query -> status -> review -> render`
- Claude runtime: current hook schema (`SessionStart`, `PreToolUse`, `PostToolUse`, `SessionEnd`) with JSON stdin handling
- Codex runtime: installed `$alpha-wiki-*` skill adapters
- Deterministic tools: invoked as modules (`python -m tools.*`) so copied target-project tools import correctly
- Obsidian: open the generated `wiki/` folder as the vault; Obsidian runtime state is ignored by git
- Release audit: expected verdict `READY`
- Test suite: expected green state `127 passed`

Remaining external prerequisite: install `uv` for the smoothest Claude/CI path (`pipx install uv`). Hooks can fall back to `.venv/bin/python` or `python3`, but `uv` is the supported release path.

## Why Alpha-wiki

LLM agents forget. RAG hides what they remember. Embeddings drift silently and obscure why a retrieval landed. **Plain markdown with `[[wikilinks]]` doesn't have these problems** — but raw markdown alone is undisciplined: pages go stale, links rot, structure entropies.

Alpha-wiki gives the wiki a **runtime contract** — typed entities, required frontmatter, bidirectional links the lint enforces, automated hooks that load compressed context at session start and run lint at session end. The result: **agent memory that compounds week-over-week instead of decaying.**

Use it for engineering projects (decisions, modules, contracts, ADRs), research (papers, claims, experiments), product (features, personas, flows), or as a personal knowledge base. Five domain presets plus four architectural overlays (clean / hexagonal / DDD / layered) ship out of the box, and the schema **evolves through ingest** — new entity types are proposed, not preempted.

## What's different from Karpathy's LLM-Wiki

Karpathy's 2025 [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) sketched the idea in ~80 lines: three layers (raw / wiki / CLAUDE.md), three operations (ingest / query / lint), two service files (index.md / log.md). It is a beautiful sketch. Alpha-wiki is the production extension.

| Karpathy's gist (sketch) | Alpha-wiki (runtime) |
|---|---|
| 3 untyped layers | Same 3 layers, made explicit as **mutability contracts** + 5 domain presets + 4 architectural overlays |
| 3 operations (ingest, query, lint) | **11 skills + 11 slash commands** — init, doctor, ingest, query, lint, evolve, status, spawn-agent, render, review, rollup |
| No frontmatter rules | **Required frontmatter per entity type**, lint-blocked on violations |
| Manual cross-links | **Bidirectional enforcement** — every forward link gets a reverse, written automatically by the engine |
| No automation | **Three-layer hooks** — session-start loads `context_brief.md`, post-tool-use rebuilds the graph, session-end runs lint and appends a log entry, pre-commit blocks 🔴 errors, weekly CI review |
| Static index.md | **Auto-generated graph layer** — `edges.jsonl`, `context_brief.md` (≤8000 chars, loaded into every session for free), `open_questions.md` |
| Bring your own UI | **Obsidian-first** — the generated `wiki/.obsidian/` config ships with semantic color groups (🔴 repos/services, 🟢 modules/domains, 🔵 features/flows, ⚫ docs, 🟠 contracts) so the graph view reads like a system diagram |
| One-shot setup | **Schema evolution** — `/alpha-wiki:evolve` adds new entity types through ingest, gates them by default, logs every schema change |
| You write the subagents | **Subagent slot** — `/alpha-wiki:spawn-agent` generates wiki-aware Claude Code subagents that honor the mutability matrix |

In one line: **Karpathy gave the idea, Alpha-wiki gives the runtime.**

## Install

### Claude Code

```bash
claude plugins marketplace add yura4gus/alpha-wiki-creator
claude plugins install alpha-wiki
```

Requires Python 3.12+ and `uv` (`pipx install uv` if missing).

Then in any project:

```
/alpha-wiki:init
/alpha-wiki:doctor --platform both --refresh
```

### Codex CLI (OpenAI)

Install and sign in to Codex, then install Alpha-Wiki's Codex skill adapters:

```bash
npm install -g @openai/codex
codex --login
git clone https://github.com/yura4gus/alpha-wiki-creator
cd alpha-wiki-creator
python3 scripts/install_codex.py
```

Then in any project:

```bash
codex
```

Ask Codex to use `$alpha-wiki-init` to bootstrap the wiki. Codex skill names are prefixed (`$alpha-wiki-query`, `$alpha-wiki-lint`, `$alpha-wiki-status`, etc.) so they do not collide with generic local skills. Claude slash commands stay unchanged.

OpenAI Codex CLI setup reference: `npm install -g @openai/codex`, then `codex --login`.

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
                       │  /alpha-wiki:doctor      │
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
- **Obsidian-compatible** — `wiki/.obsidian/` config generated, so opening the `wiki/` folder as a vault works out of the box
- **Claude hook runtime** — official hook event names, JSON stdin parsing, wiki-path filtering, and graph rebuild after wiki writes
- **Deterministic engine** — `tools.doctor`, `tools.lint`, and `tools.wiki_engine` are pure Python modules, no LLM, fully tested
- **Schema-evolution gate** — every new entity type confirmed before added (or auto-mode if you trust)
- **CI-ready** — deterministic GitHub Actions run `tools.lint`, `tools.review`, and `tools.rollup` without Claude secrets

## Workflow

```
1. /alpha-wiki:init           Audit corpus → plan raw/wiki migration → bootstrap
2. /alpha-wiki:doctor         Verify install/runtime/wiki health
3. /alpha-wiki:ingest <path>  Raw artifact (PRD, ADR, OpenAPI spec, …) → wiki page(s)
4. /alpha-wiki:query <q>      Ask/find in the wiki with cited evidence
5. /alpha-wiki:lint --fix     Check/fix structure (links, reverses, frontmatter)
6. /alpha-wiki:status         Health + mandatory Gap Check
7. /alpha-wiki:evolve <type>  Add a new entity type to the schema
8. /alpha-wiki:spawn-agent    Add a wiki-aware subagent
9. /alpha-wiki:render         Refresh Obsidian config or generate static HTML
10. /alpha-wiki:review        Weekly structural review — status + lint + next actions
11. /alpha-wiki:rollup        Weekly/monthly activity summary
```

The `session-start` hook auto-loads `context_brief.md` so the agent has compressed context for free.
The `session-end` hook runs lint and appends a log entry. Most users never invoke `/alpha-wiki:lint` manually.

On existing projects, `init` first audits the repo: it enumerates current durable documents, proposes which ones belong in `raw/` or a source manifest, proposes target wiki slots, and creates a batch plan so the first wiki pages are small, linked, and reviewable.

## Skills

| Slash command | Purpose |
|---|---|
| `/alpha-wiki:init` | Bootstrap wiki + scaffolding into the current project |
| `/alpha-wiki:doctor` | Verify Python/tools/wiki graph/hooks/CI/Codex/Claude runtime health |
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

The bootstrap ships a default `wiki/.obsidian/graph.json` with **color groups** so the graph view tells a story at a glance. Open the generated `wiki/` directory itself as the Obsidian vault; do not open the repository root.

| Color | Meaning |
|---|---|
| 🔴 Red | Repo / service / top-level architectural unit (`services/`, `repos/`, `bounded-contexts/`, `applications/`) |
| 🟢 Green | Module / domain / sub-component within a service (`modules/`, `components/`, `core/`, `ports/`, `domains/`, `adapters/`) |
| 🔵 Blue | Feature / function / user-facing flow (`features/`, `flows/`, `use-cases/`, `application/`) |
| ⚫ Black | Document/evidence page — decisions, specs, concepts, APIs, papers, claims, summaries, etc. |
| 🟠 Orange | Contract — REST/GraphQL/gRPC/events at service boundaries (`contracts/`) |
| ⚪ Light grey | People / tasks — meta layer |

A red node is a repo/service boundary. A green cluster around red is the service's modules/domains/components. A blue node shows a feature or function implemented by those modules. Black nodes are documents/evidence attached to the architecture. An orange node bridging two reds is a contract owned by one service and consumed by another. Isolated red or black nodes are maintenance gaps.

Color is not a clustering mechanism. Clusters should emerge from typed links and shared architecture boundaries; colors only label the kind of node you are looking at.

Customize: edit `wiki/.obsidian/graph.json` → `colorGroups` array. Full legend at `wiki/.obsidian/COLOR-LEGEND.md` after bootstrap.

Obsidian may rewrite `wiki/.obsidian/graph.json`, `workspace.json`, `app.json`, `appearance.json`, and `core-plugins.json` during normal use. Alpha-Wiki treats those as local runtime state and ignores them in git; the portable defaults live under `assets/obsidian/`.

## Documentation

Current architecture set:

- [`docs/00-architecture.md`](docs/00-architecture.md) — ecosystem boundaries and plugin topology
- [`docs/01-alpha-wiki.md`](docs/01-alpha-wiki.md) — Alpha-Wiki product specification
- [`docs/02-agentops.md`](docs/02-agentops.md) — AgentOps product specification
- [`docs/03-superpowers-adapter.md`](docs/03-superpowers-adapter.md) — optional Superpowers integration contract
- [`docs/04-state-backend-contract.md`](docs/04-state-backend-contract.md) — state backend abstraction
- [`docs/roadmap-execution.md`](docs/roadmap-execution.md) — execution roadmap
- [`docs/implementation-plan-2026-04-30.md`](docs/implementation-plan-2026-04-30.md) — implementation plan for the current repo
- [`docs/quickstart.md`](docs/quickstart.md) — 10-minute install → init → ingest → query path
- [`docs/codex-adapter.md`](docs/codex-adapter.md) — OpenAI Codex CLI install and skill mapping
- [`docs/best-practices-gap-analysis-2026-04-30.md`](docs/best-practices-gap-analysis-2026-04-30.md) — operator/AI ergonomics gap scan
- [`docs/karpathy-llm-wiki-compliance-audit-2026-05-01.md`](docs/karpathy-llm-wiki-compliance-audit-2026-05-01.md) — Phase 0 audit against the Karpathy LLM-Wiki core
- [`docs/final-release-hardening-plan.md`](docs/final-release-hardening-plan.md) — consolidated key improvements required for final release
- [`docs/alpha-wiki-lifecycle-automation-audit-2026-05-01.md`](docs/alpha-wiki-lifecycle-automation-audit-2026-05-01.md) — end-to-end lifecycle automation and closure audit
- [`docs/platform-compatibility-matrix.md`](docs/platform-compatibility-matrix.md) — Claude/Codex/Gemini support and limitation matrix
- [`docs/final-release-readiness-audit-2026-05-04.md`](docs/final-release-readiness-audit-2026-05-04.md) — final-release gate audit and blocking gaps
- [`docs/release-smoke-2026-05-05.md`](docs/release-smoke-2026-05-05.md) — fresh-project Claude/Codex release smoke evidence

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

Run the deterministic final-release gate:

```bash
.venv/bin/python -m tools.release_audit --root .
```

Current expected release-audit verdict: `READY`.

## License

MIT
