# Audit Verified Inventory

Date: 2026-04-30
Scope: Phase 0 audit for `alpha-wiki-creator`.

## Result

Phase 0 audit is complete.

- `T0.1` inventory: closed.
- `T0.2` `review` / `rollup` status: closed.
- `T0.3` ADR approval: already closed; ADR-001..006 are marked `Status: Accepted`.
- `T0.4` marketplace topology: closed by ADR-005.
- `T0.5` spawn-agent boundary: closed by ADR-006.

Phase 1a can start with confirmed repo facts, not assumptions.

## Verified Repository Surface

| Area | Verified state | Notes |
|---|---|---|
| Root package | Present | `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`. Package name is `alpha-wiki`, version `0.1.0`. |
| Plugin metadata | Present | `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. Marketplace lists one plugin: `alpha-wiki`. |
| GitHub workflows | Present | Repo CI has only `.github/workflows/plugin-ci.yml` for tests and coverage. Generated target-project workflow templates live under `assets/workflows/`. |
| Skills | 8 present | `init`, `ingest`, `query`, `lint`, `evolve`, `status`, `spawn-agent`, `render`. |
| Commands | 8 present | One command file per existing skill under `commands/`. |
| Deterministic tools | 6 Python modules | `_env.py`, `_models.py`, `classify.py`, `lint.py`, `status.py`, `wiki_engine.py`. |
| Scripts | 3 Python modules | `bootstrap.py`, `interview.py`, `add_entity_type.py`. |
| Tests | 29 test files | Unit + integration coverage exists for bootstrap, lint, classify, status, wiki engine, and templates. |
| References | Present | Presets, overlays, classifier, schema evolution, hooks, cross-reference docs, examples. |
| Assets | Present | Frontmatter templates, hooks, workflows, Obsidian config, README/CLAUDE/pyproject templates. |

## Skills Inventory

| Skill | File | Status | Phase 1a action |
|---|---|---|---|
| `init` | `skills/init/SKILL.md` | Present, operational-manual-lite | Harden to 15-dimension standard; add safe existing-repo behavior. |
| `ingest` | `skills/ingest/SKILL.md` | Present as workflow instructions | Back with deterministic ingest pipeline and pressure tests. |
| `query` | `skills/query/SKILL.md` | Present as agent workflow | Add citation policy, truth-status taxonomy, contradiction surfacing. |
| `lint` | `skills/lint/SKILL.md` | Present and backed by `tools/lint.py` | Expand severity/check model to target spec. |
| `evolve` | `skills/evolve/SKILL.md` | Present and backed by `scripts/add_entity_type.py` | Add migration planning for existing pages. |
| `status` | `skills/status/SKILL.md` | Present and backed by `tools/status.py` | Add health score and suggested-next-actions logic. |
| `spawn-agent` | `skills/spawn-agent/SKILL.md` | Present as workflow instructions | Enforce ADR-006 boundary with tests. |
| `render` | `skills/render/SKILL.md` | Present, HTML documented as future | Add/refuse modes explicitly; implement later HTML/Mermaid if kept in Phase 1a. |

Missing Phase 1a skills:

- `contracts-check`
- `claims-check`
- `daily-maintenance`
- `review`
- `rollup`

## Commands Inventory

| Command | File | Backing skill | Notes |
|---|---|---|---|
| `/alpha-wiki:init` | `commands/init.md` | `init` | Present. |
| `/alpha-wiki:ingest` | `commands/ingest.md` | `ingest` | Present. |
| `/alpha-wiki:query` | `commands/query.md` | `query` | Present. |
| `/alpha-wiki:lint` | `commands/lint.md` | `lint` | Present. |
| `/alpha-wiki:evolve` | `commands/evolve.md` | `evolve` | Present. |
| `/alpha-wiki:status` | `commands/status.md` | `status` | Present. |
| `/alpha-wiki:spawn-agent` | `commands/spawn-agent.md` | `spawn-agent` | Present. |
| `/alpha-wiki:render` | `commands/render.md` | `render` | Present. |
| `/alpha-wiki:review` | none | none | Not implemented as command or skill. |
| `/alpha-wiki:rollup` | none | none | Not implemented as command or skill. |

## Tools Inventory

| Module | Verified responsibilities |
|---|---|
| `tools/wiki_engine.py` | Markdown/frontmatter parsing, wikilink extraction, edge rebuild, context brief rebuild, open questions rebuild, `add-edge` CLI. |
| `tools/lint.py` | Broken wikilinks, missing reverse links, orphans, required frontmatter, duplicate slugs, dependency rules, safe missing-reverse fixes. |
| `tools/status.py` | Basic wiki status report. |
| `tools/classify.py` | Deterministic artifact classification plus LLM fallback stub. |
| `tools/_models.py` | `Page`, `Edge`, `LintFinding`, `LintSeverity`. |
| `tools/_env.py` | Minimal dotenv loading. |
| `scripts/bootstrap.py` | Renders target project scaffolding, copies assets/tools, initializes graph, writes merged config. |
| `scripts/interview.py` | `InterviewConfig`, auto-detection, answer-to-config conversion. |
| `scripts/add_entity_type.py` | Adds entity type schema/frontmatter and updates wiki metadata. |

Confirmed missing deterministic tools from Phase 1a target:

- `tools/ingest_pipeline.py`
- `tools/contradiction_detector.py`
- `tools/wiki_search.py`
- `tools/status_report.py`
- `tools/contracts_check.py`
- `tools/claims_check.py`
- `tools/render_html.py`
- `tools/render_mermaid.py`

## Tests Inventory

Verified test files: 29.

Coverage areas:

- Bootstrap rendering and idempotency.
- Existing-codebase wiki-dir autodetect.
- Greenfield software/research bootstrap paths.
- Upgrade preserving wiki pages.
- Lint checks and CLI.
- Wiki engine parsing, edges, context brief, open questions, CLI.
- Classifier and LLM fallback stub.
- Status report.
- Template rendering.
- Entity-type addition.

Missing Phase 1a pressure-test suites:

- `tests/skills/test_init_pressure.py`
- `tests/skills/test_ingest_pressure.py`
- `tests/skills/test_query_pressure.py`
- `tests/skills/test_evolve_pressure.py`
- `tests/skills/test_status_pressure.py`
- `tests/skills/test_spawn_agent_boundary.py`
- `tests/skills/test_render_snapshots.py`
- `tests/skills/test_contracts_check.py`
- `tests/skills/test_claims_check.py`
- `tests/skills/test_daily_maintenance_idempotency.py`
- `tests/skills/test_review.py`
- `tests/skills/test_rollup.py`

## Workflow And Hook Findings

| Finding | Evidence | Phase 1a implication |
|---|---|---|
| Repo CI only runs tests | `.github/workflows/plugin-ci.yml` | Generated target-project workflows are not tested as live repo workflows. |
| Target CI templates include lint/review/rollup | `assets/workflows/wiki-lint.yml`, `wiki-review.yml`, `wiki-rollup.yml` | Templates exist, but review/rollup commands are not backed by skills. |
| Generated review/rollup templates use old namespace | `claude -p "/wiki-review"` and `claude -p "/wiki-rollup month"` | Must align with `/alpha-wiki:*` or intentionally document old alias support. |
| `wiki-lint.yml` hardcodes `wiki` | `uv run python tools/lint.py --wiki-dir wiki --dry-run` | Does not honor custom `wiki_dir`, including `.wiki`. |
| Hook mode selection is not honored | `scripts/bootstrap.py` copies all `assets/hooks/*` when hooks is `all`, `session`, or `git` | Must split session hooks from git hooks. |
| Hooks default to `wiki` | Hook scripts use `WIKI_DIR="${WIKI_DIR:-wiki}"` | `settings-local.j2` uses `path_glob` but does not set `WIKI_DIR`; custom `wiki_dir` can drift. |
| `post-tool-use` rebuilds only context brief | `assets/hooks/post-tool-use.sh` calls `rebuild-context-brief` only | Must rebuild `edges.jsonl` and `open_questions.md` too. |
| Upgrade graph initialization is destructive | `scripts/bootstrap.py` always writes graph files in `_initialize_graph` | Must preserve existing graph artifacts during upgrade unless explicitly rebuilding. |
| Existing repo bootstrap overwrite risk remains | `_render_top_level_files` skips only `README.md` on upgrade | Must protect `pyproject.toml`, `.gitignore`, `CLAUDE.md`, `.env.example`, and provide dry-run conflict report. |

## T0.2 Decision: review / rollup Status

| Capability | Full skill? | Command? | CI template? | Status | Decision |
|---|---:|---:|---:|---|---|
| `/alpha-wiki:review` | No | No | Partial old-template only | CI-template-only, not runnable as current alpha-wiki command | Implement `skills/review/SKILL.md` and `commands/review.md` in Phase 1a, or remove/disable generated workflow until backed. |
| `/alpha-wiki:rollup` | No | No | Partial old-template only | CI-template-only, not runnable as current alpha-wiki command | Implement `skills/rollup/SKILL.md` and `commands/rollup.md` in Phase 1a, or remove/disable generated workflow until backed. |

This resolves `T0.2`: `review` and `rollup` are not full skills and are not commands. They exist only as generated CI templates using the older `/wiki-*` namespace.

## Phase 1a Entry Backlog

P0:

1. Add safe bootstrap mode for existing repos; prevent silent overwrites.
2. Propagate and honor `wiki_dir` across hooks and generated workflows.
3. Make upgrade graph initialization non-destructive.
4. Honor hook selection mode (`session`, `git`, `all`, `none`).
5. Rebuild the full graph after wiki writes: edges, context brief, open questions.
6. Resolve `review` / `rollup` mismatch: either implement backed skills/commands or remove generated workflows from default CI path.

P1:

1. Harden the 8 existing skills to the 15-dimension standard.
2. Add `contracts-check`, `claims-check`, `daily-maintenance`.
3. Add deterministic tools listed above.
4. Add pressure-test suites for each hardened/new skill.

## Verification Commands

```bash
find skills -maxdepth 2 -type f | sort
find commands -maxdepth 2 -type f | sort
find tools scripts tests -maxdepth 3 -type f | sort
find .claude-plugin .github .claude -maxdepth 4 -type f | sort
rg -n "review|rollup|contracts-check|claims-check|daily-maintenance|alpha-wiki:review|alpha-wiki:rollup" README.md docs .claude-plugin .github assets commands skills tools scripts tests pyproject.toml
find tests -path '*/__pycache__' -prune -o -type f -name 'test_*.py' -print | sort
```
