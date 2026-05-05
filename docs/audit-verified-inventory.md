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
- `T0.6` skill content audit: closed; the original 10 backed skill bodies were expanded into richer operational manuals.

Phase 1a can start with confirmed repo facts, not assumptions.

## Verified Repository Surface

| Area | Verified state | Notes |
|---|---|---|
| Root package | Present | `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`. Package name is `alpha-wiki`, version `0.1.0`. |
| Plugin metadata | Present | `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. Marketplace lists one plugin: `alpha-wiki`. |
| GitHub workflows | Present | Repo CI has only `.github/workflows/plugin-ci.yml` for tests and coverage. Generated target-project workflow templates live under `assets/workflows/`. |
| Skills | 11 present | `init`, `doctor`, `ingest`, `query`, `lint`, `evolve`, `status`, `spawn-agent`, `render`, `review`, `rollup`. |
| Commands | 11 present | One command file per existing skill under `commands/`. |
| Deterministic tools | 20 Python modules | `_env.py`, `_models.py`, `claims_check.py`, `classify.py`, `contracts_check.py`, `contradiction_detector.py`, `doctor.py`, `ingest_pipeline.py`, `init_audit.py`, `lint.py`, `release_audit.py`, `release_smoke.py`, `render_dot.py`, `render_html.py`, `render_mermaid.py`, `status.py`, `wiki_engine.py`, `wiki_search.py`, `review.py`, `rollup.py`. |
| Scripts | 3 Python modules | `bootstrap.py`, `interview.py`, `add_entity_type.py`. |
| Tests | 49 test files | Unit + integration coverage exists for bootstrap, hooks/runtime assets, skill docs, lint, classify, init audit, doctor, graph exports, ingest pipeline, query helper, contracts/claims/contradictions, release audit, release smoke, status, review, rollup, wiki engine, and templates. |
| References | Present | Presets, overlays, classifier, schema evolution, hooks, cross-reference docs, examples. |
| Assets | Present | Frontmatter templates, hooks, workflows, Obsidian config, README/CLAUDE/pyproject templates. |

## Skills Inventory

| Skill | File | Status | Phase 1a action |
|---|---|---|---|
| `init` | `skills/init/SKILL.md` | Expanded operational manual | Full 15-dimension pressure testing remains Phase 1a. |
| `doctor` | `skills/doctor/SKILL.md` | Backed install/runtime verifier | Add final release smoke usage. |
| `ingest` | `skills/ingest/SKILL.md` | Backed by deterministic local-file ingest MVP | Add claim extraction and contradiction checks. |
| `query` | `skills/query/SKILL.md` | Backed by deterministic search/citation helper | Add contradiction-aware pressure tests after claims tooling. |
| `lint` | `skills/lint/SKILL.md` | Expanded operational manual backed by `tools/lint.py` | Expand severity/check model to target spec. |
| `evolve` | `skills/evolve/SKILL.md` | Expanded operational manual backed by `scripts/add_entity_type.py` | Add migration planning implementation for existing pages. |
| `status` | `skills/status/SKILL.md` | Expanded operational manual backed by `tools/status.py` | Add health score and suggested-next-actions implementation. |
| `spawn-agent` | `skills/spawn-agent/SKILL.md` | Expanded operational manual with ADR-006 boundary | Add boundary pressure tests. |
| `render` | `skills/render/SKILL.md` | Expanded operational manual; Mermaid/DOT/HTML exports backed by deterministic tools | Add visual polish only after dogfooding. |
| `review` | `skills/review/SKILL.md` | Expanded operational manual backed by `tools/review.py` | Full 15-dimension hardening remains Phase 1a. |
| `rollup` | `skills/rollup/SKILL.md` | Expanded operational manual backed by `tools/rollup.py` | Full 15-dimension hardening remains Phase 1a. |

Missing Phase 1a skills:

- `contracts-check`
- `claims-check`
- `daily-maintenance`

## Commands Inventory

| Command | File | Backing skill | Notes |
|---|---|---|---|
| `/alpha-wiki:init` | `commands/init.md` | `init` | Present. |
| `/alpha-wiki:doctor` | `commands/doctor.md` | `doctor` | Implemented with `tools/doctor.py`. |
| `/alpha-wiki:ingest` | `commands/ingest.md` | `ingest` | Present. |
| `/alpha-wiki:query` | `commands/query.md` | `query` | Present. |
| `/alpha-wiki:lint` | `commands/lint.md` | `lint` | Present. |
| `/alpha-wiki:evolve` | `commands/evolve.md` | `evolve` | Present. |
| `/alpha-wiki:status` | `commands/status.md` | `status` | Present. |
| `/alpha-wiki:spawn-agent` | `commands/spawn-agent.md` | `spawn-agent` | Present. |
| `/alpha-wiki:render` | `commands/render.md` | `render` | Present. |
| `/alpha-wiki:review` | `commands/review.md` | `review` | Implemented with `tools/review.py`. |
| `/alpha-wiki:rollup` | `commands/rollup.md` | `rollup` | Implemented with `tools/rollup.py`. |

## Tools Inventory

| Module | Verified responsibilities |
|---|---|
| `tools/wiki_engine.py` | Markdown/frontmatter parsing, wikilink extraction, edge rebuild, context brief rebuild, open questions rebuild, `add-edge` CLI. |
| `tools/contracts_check.py` | Contract trust checks: service owner, consumer reverse consistency, version/migration-note gaps. |
| `tools/claims_check.py` | Claim trust checks: provenance, freshness, explicit contradiction target validation. |
| `tools/contradiction_detector.py` | Deterministic contradiction detection from explicit links and opposing claim stances. |
| `tools/doctor.py` | Install/runtime lifecycle verification: Python, uv, imports, config, wiki dir, graph artifacts, lint, hooks, CI, platform hints. |
| `tools/ingest_pipeline.py` | Deterministic local-file ingest: page write, provenance, optional cluster link, log, graph rebuild, lint summary, resume state. |
| `tools/init_audit.py` | Existing-project init audit: discovers durable source files, proposes raw placement, wiki slots, and batched processing plans. |
| `tools/lint.py` | Broken wikilinks, missing reverse links, orphans, required frontmatter, duplicate slugs, dependency rules, safe missing-reverse fixes. |
| `tools/render_mermaid.py` | Mermaid graph export with typed service clusters and role colors. |
| `tools/render_dot.py` | Graphviz DOT graph export with typed service clusters and role colors. |
| `tools/render_html.py` | Static read-only HTML export for index, pages, and graph artifacts. |
| `tools/release_audit.py` | Deterministic final-release gate across command/skill surface, core tools, docs, packaging, trust depth, and platform support. |
| `tools/release_smoke.py` | Fresh-project release smoke covering bootstrap, Claude/Codex doctor, ingest, query, status, review, and exports. |
| `tools/wiki_search.py` | Deterministic markdown search and query report with citations, no embeddings. |
| `tools/status.py` | Basic wiki status report. |
| `tools/review.py` | Wiki-level structural review: status snapshot, lint findings, suggested next actions. |
| `tools/rollup.py` | Weekly/monthly activity rollup generation and optional write to `wiki/rollups/`. |
| `tools/classify.py` | Deterministic artifact classification plus LLM fallback stub. |
| `tools/_models.py` | `Page`, `Edge`, `LintFinding`, `LintSeverity`. |
| `tools/_env.py` | Minimal dotenv loading. |
| `scripts/bootstrap.py` | Renders target project scaffolding, copies assets/tools, initializes graph, writes merged config. |
| `scripts/interview.py` | `InterviewConfig`, auto-detection, answer-to-config conversion. |
| `scripts/add_entity_type.py` | Adds entity type schema/frontmatter and updates wiki metadata. |

Confirmed missing deterministic tools from Phase 1a target:

- `tools/status_report.py`

## Tests Inventory

Verified test files: 49.

Coverage areas:

- Bootstrap rendering and idempotency.
- Existing-codebase wiki-dir autodetect.
- Hook mode selection and runtime asset wiki-dir rendering.
- Skill frontmatter and operational-manual section guards.
- Greenfield software/research bootstrap paths.
- Upgrade preserving wiki pages.
- Lint checks and CLI.
- Wiki engine parsing, edges, context brief, open questions, CLI.
- Classifier and LLM fallback stub.
- Existing-project init audit and source-manifest generation.
- Contract, claim, and contradiction trust-depth checks.
- Release audit final gate and CLI exit behavior.
- Release smoke on a fresh temporary project.
- Status report.
- Review and rollup backend tools.
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
| Target CI templates include lint/review/rollup | `assets/workflows/wiki-lint.yml`, `wiki-review.yml`, `wiki-rollup.yml` | Templates exist and are now backed by skills/commands/tools. |
| Generated review/rollup templates use alpha namespace | `claude -p "/alpha-wiki:review"` and `claude -p "/alpha-wiki:rollup month --write"` | Old `/wiki-*` namespace mismatch resolved. |
| Generated workflow wiki dir | `scripts/bootstrap.py` rewrites `--wiki-dir wiki` to the configured `wiki_dir` | Closed for generated projects; source asset remains the default template. |
| Hook mode selection | `_hook_files_for_mode()` splits `session`, `git`, `all`, and `none` | Closed. |
| Generated hook wiki dir | `_render_runtime_asset()` rewrites `WIKI_DIR="${WIKI_DIR:-wiki}"` to the configured `wiki_dir` | Closed for generated projects. |
| `post-tool-use` graph rebuild | `assets/hooks/post-tool-use.sh` runs `rebuild-edges`, `rebuild-context-brief`, and `rebuild-open-questions` | Closed. |
| Upgrade graph initialization | `_initialize_graph(..., upgrade=True)` preserves existing graph artifacts | Closed. |
| Existing repo bootstrap protection | Protected writes preserve top-level files and record `.alpha-wiki/bootstrap-report.md` | Closed. |

## T0.2 Decision: review / rollup Status

| Capability | Full skill? | Command? | CI template? | Status | Decision |
|---|---:|---:|---:|---|---|
| `/alpha-wiki:review` | Yes | Yes | Yes | Backed minimal implementation | Full 15-dimension hardening remains P1. |
| `/alpha-wiki:rollup` | Yes | Yes | Yes | Backed minimal implementation | Full 15-dimension hardening remains P1. |

This resolves `T0.2`: `review` and `rollup` were CI-template-only old-namespace artifacts during audit; they are now backed by skills, commands, and deterministic tools.

## Phase 1a Entry Backlog

P0:

1. Add safe bootstrap mode for existing repos; prevent silent overwrites. Done: protected top-level files are preserved, dry-run reports conflicts, and `.alpha-wiki/bootstrap-report.md` records protected skips.
2. Propagate and honor `wiki_dir` across hooks and generated workflows. Done: generated hook scripts default to the configured wiki dir, `.claude/settings.local.json` uses the configured `path_glob`, and generated CI workflows use the configured wiki dir in lint/rollup paths.
3. Make upgrade graph initialization non-destructive. Done: upgrade mode preserves existing `edges.jsonl`, `context_brief.md`, and `open_questions.md`.
4. Honor hook selection mode (`session`, `git`, `all`, `none`). Done: `session` installs only Claude session/tool hooks plus settings, `git` installs only git hook helpers, `all` installs both, and `none` installs no hooks/settings.
5. Rebuild the full graph after wiki writes: edges, context brief, open questions. Done: `post-tool-use.sh` now runs `rebuild-edges`, `rebuild-context-brief`, and `rebuild-open-questions` together.
6. Resolve `review` / `rollup` mismatch: either implement backed skills/commands or remove generated workflows from default CI path. Done: backed `review` and `rollup` skills/commands/tools exist, and generated workflows now call `/alpha-wiki:review` and `/alpha-wiki:rollup month --write`.

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
