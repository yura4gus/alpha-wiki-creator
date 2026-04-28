---
name: wiki-init
description: Use this skill whenever the user wants to bootstrap a wiki, knowledge base, or persistent memory layer for an LLM agent or multi-agent system. Triggers include "create a wiki", "set up a knowledge base", "bootstrap project memory", "agent memory layer", "Karpathy LLM wiki", "OmegaWiki style", "Obsidian + Claude Code workflow", "set up CLAUDE.md", "wiki for my project", "memory for agents". Also use when the user describes wanting raw → wiki → schema separation, persistent compounding knowledge instead of RAG, or session-end automation that keeps documentation current. Do NOT use for one-off doc generation, single-file summaries, or static documentation that won't be incrementally maintained.
---

# wiki-init — bootstrap an LLM wiki into the current project

## Process

1. **Environment check**
   - Verify Python ≥ 3.12 and `uv` are available (suggest `pipx install uv` if missing).
   - Run `git rev-parse --is-inside-work-tree`; if not a repo, ask before `git init`.
   - Detect existing source code (src/, package.json, pyproject.toml, etc.).

2. **Interview** — sequentially ask:
   1. Project name (default: directory basename)
   2. One-line description
   3. Wiki dir — auto-suggest `wiki/` (greenfield) or `.wiki/` (existing code); allow override
   4. Preset: software-project (default) | research | product | personal | knowledge-base | custom
   5. (if software-project) Architectural overlay — none | clean | hexagonal | ddd | ddd+clean | ddd+hexagonal | layered (no default — explicit choice)
   6. (if custom) Define entity types — for each: name, dir, required frontmatter, sections
   7. i18n: en-only (default) or en + other
   8. Hooks installation: all (default) | session-only | git-only | none
   9. CI workflows: yes (default if `.github/` exists or remote is GitHub) | no
   10. Schema-evolve mode: gated (default) | auto

3. **Propose plan** — show resolved tree + key decisions; require user confirmation before any writes.

4. **Render** — invoke `uv run python -m scripts.bootstrap` (calls `scripts.bootstrap.bootstrap(target, config)`).

5. **Post-render** — `uv sync`, `tools/lint.py --dry-run`, `wiki_engine.py rebuild-context-brief`, `git add . && git commit -m "wiki bootstrap"`.

6. **First ingest (optional)** — if `raw/` has files, prompt to ingest now via `/wiki-ingest`.

7. **Handoff** — print 3 main commands, Obsidian instructions, session-end hook explainer.

## Idempotency

If `CLAUDE.md` already exists, enter upgrade mode: diff requested config vs existing, never overwrite wiki pages, only touch schema/scaffolding with confirmation.

## References

- `references/concept.md` — Karpathy + OmegaWiki philosophy
- `references/presets/` — preset YAMLs
- `references/overlays/` — overlay YAMLs
- `references/cross-reference-rules.md` — bidirectional link canon
- `references/hooks-design.md` — hook contracts
