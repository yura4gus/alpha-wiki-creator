---
name: init
description: Bootstrap an LLM-maintained wiki into the current project (Karpathy + OmegaWiki style). Triggers include "create a wiki", "set up a knowledge base", "bootstrap project memory", "agent memory layer", "Karpathy LLM wiki", "OmegaWiki style", "Obsidian + Claude Code workflow", "set up CLAUDE.md", "wiki for my project", "memory for agents". Use for raw → wiki → schema separation, persistent compounding knowledge instead of RAG, session-end automation. Do NOT use for one-off doc generation or static documentation that won't be incrementally maintained.
argument-hint: "[project-description]"
---

# wiki:init — bootstrap an LLM wiki into the current project

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

4. **Safe-existing check** — if protected project files already exist (`CLAUDE.md`, `README.md`, `pyproject.toml`, `.gitignore`, `.env.example`), run bootstrap dry-run first and show the conflict report. Do not overwrite these files silently.

5. **Render** — invoke `uv run python -m scripts.bootstrap` (calls `scripts.bootstrap.bootstrap(target, config)`). Existing protected files are preserved by default and conflicts are recorded in `.alpha-wiki/bootstrap-report.md`.

6. **Post-render** — `uv sync`, `tools/lint.py --dry-run`, `wiki_engine.py rebuild-context-brief`, `git add . && git commit -m "wiki bootstrap"`.

7. **First ingest (optional)** — if `raw/` has files, prompt to ingest now via `/alpha-wiki:ingest`.

8. **Handoff** — print 3 main commands, Obsidian instructions, session-end hook explainer.

## Idempotency

If `CLAUDE.md` already exists, enter upgrade mode: diff requested config vs existing, never overwrite wiki pages, never reset graph artifacts, and only touch schema/scaffolding with confirmation.

## References

- `references/concept.md` — Karpathy + OmegaWiki philosophy
- `references/presets/` — preset YAMLs
- `references/overlays/` — overlay YAMLs
- `references/cross-reference-rules.md` — bidirectional link canon
- `references/hooks-design.md` — hook contracts
