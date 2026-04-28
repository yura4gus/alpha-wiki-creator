# wiki-creator

A Claude Code plugin that bootstraps an LLM-maintained wiki into any project.

Inspired by:
- [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — three-layer raw/wiki/schema model.
- [OmegaWiki](https://github.com/skyllwt/OmegaWiki) — typed entities, edges, bidirectional enforcement.

## What you get

- Persistent agent memory: a markdown wiki that compounds over time
- Auto-generated context brief loaded at every session start
- Lint enforcement: broken links, missing reverses, orphans, dependency rules
- Schema evolution: new entity types added through ingest, never preempted
- Obsidian-compatible — open `wiki/` as a vault for graph view

## Install

```bash
claude plugins install wiki-creator
```

Requires Python 3.12+ and `uv` (install via `pipx install uv`).

## Quick start

In a project directory:

```
/wiki-init
```

Walks you through preset/overlay choice and renders the scaffolding. Then ingest:

```
/wiki-ingest raw/PRD.md raw/AUDIT_TASKS.md
```

Then ask:

```
/wiki-query "What modules does the auth feature touch?"
```

## Skills

- `/wiki-init` — bootstrap
- `/wiki-ingest` — raw → wiki
- `/wiki-query` — ask the wiki
- `/wiki-lint` — structural validation
- `/wiki-evolve` — add an entity type
- `/wiki-spawn-agent` — add a subagent
- `/wiki-render` — refresh Obsidian / generate HTML

## Design

See [`docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`](docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md).

## Development

```bash
uv sync --dev
uv run pytest
```
