# 01 — Alpha-Wiki

> Specification for the Alpha-Wiki plugin. Persistent memory layer. Standalone product. Does not import AgentOps. Does not import Superpowers.

References: `00-architecture.md` for boundaries, `_references.md` for source patterns, `adr/ADR-001`, `adr/ADR-003`, `adr/ADR-006`.

---

## 1. Slot in the ecosystem

Alpha-Wiki is the **memory and knowledge layer**. It owns the `wiki/` namespace at the project root.

What it provides:
- Three-layer mutability: `raw/` (read-only) → `wiki/` (LLM-mutable) → `CLAUDE.md` (gated schema)
- Typed entities with required frontmatter
- Bidirectional cross-references with lint enforcement
- Auto-generated graph artifacts: `wiki/graph/edges.jsonl`, `wiki/graph/context_brief.md`, `wiki/graph/open_questions.md`
- Schema evolution through ingest
- Wiki-scoped queries with citation
- Obsidian and static HTML rendering

What it does not provide:
- Agent team operating model (AgentOps owns this)
- Architecture canon templates (AgentOps owns this)
- TDD or code review discipline (Superpowers owns this when present, AgentOps native fallback otherwise)

---

## 2. Repository

`yura4gus/alpha-wiki-creator` (existing). Hardened in Phase 1a in place. No rename, no relocation.

```
alpha-wiki-creator/
├── .claude-plugin/plugin.json
├── README.md
├── skills/                          # 10 backed now + 3 planned Phase 1a skills (see §3)
├── commands/                        # /alpha-wiki:* slash commands
├── tools/
│   ├── lint.py                      # Pure-Python deterministic lint
│   ├── wiki_engine.py               # Pure-Python deterministic graph engine
│   └── (additional tools added during Phase 1a)
├── tests/                           # 45 existing + new pressure tests
├── references/                      # Skill-loaded reference material
├── scripts/
└── pyproject.toml                   # Python 3.12+, uv
```

---

## 3. Skill inventory

### 3.1 Confirmed / target skills (13)

10 backed user-facing/operational skills exist in this repo; 3 additional checks/maintenance skills remain new Phase 1a work.

| # | Skill | Status | Tier |
|---|---|---|---|
| 1 | `init` | Existing — hardened | User-facing |
| 2 | `ingest` | Existing — hardened | User-facing |
| 3 | `query` | Existing — hardened | User-facing |
| 4 | `lint` | Existing — hardened | Mostly automated |
| 5 | `status` | Existing — hardened | User-facing |
| 6 | `evolve` | Existing — hardened | User-facing |
| 7 | `spawn-agent` | Existing — hardened (boundary frozen per ADR-006) | User-facing |
| 8 | `render` | Existing — hardened | Operational |
| 9 | `review` | Backed minimal implementation; hardening remains P1 | User-facing / CI |
| 10 | `rollup` | Backed minimal implementation; hardening remains P1 | User-facing / CI |
| 11 | `contracts-check` | New | Automated |
| 12 | `claims-check` | New | Automated |
| 13 | `daily-maintenance` | New | Automated |

### 3.2 Previously contingent skills

| Skill | Decision basis |
|---|---|
| `review` | Resolved in Phase 1a P0: backed by `skills/review/SKILL.md`, `commands/review.md`, and `tools/review.py`. Full 15-dimension hardening remains P1. |
| `rollup` | Resolved in Phase 1a P0: backed by `skills/rollup/SKILL.md`, `commands/rollup.md`, and `tools/rollup.py`. Full 15-dimension hardening remains P1. |

### 3.3 Rejected proposals

| Proposal | Reason |
|---|---|
| `discover` | Generic browsing; `query` covers it |
| `classify` | Sub-step of `ingest`, not standalone |
| `edit` | Deferred — not blocker for MVP |
| `check` | Vague name; overlaps with `lint` |
| `source-audit` | Deferred to Phase 6 |
| `context-brief` | Hook-driven, no user invocation needed |
| `graph-rebuild` | Hook-driven; flag on `lint` if explicit invocation needed |
| `weekly-maintenance` | Folded into `review` |
| `import-github-repo` | Deferred to Phase 6 |
| `import-docs` | `ingest` accepts paths/URLs already |
| `import-transcript` | Same — folded into `ingest` |
| `wiki-health-report` | Folded into `status` |

---

## 4. Skill specifications

Every skill complies with the 15-dimension operating-manual standard from `00-architecture.md` §5.2. Below: the spec contract per skill. Detailed SKILL.md bodies live in the repository; this section defines what each must contain.

### 4.1 `/alpha-wiki:init`

| Dimension | Specification |
|---|---|
| Purpose | Bootstrap wiki structure into a project. One-time ceremony. |
| Trigger description | Use when the user is starting wiki memory in a new repo or wants to add Alpha-Wiki to an existing project. |
| When NOT to trigger | Wiki already exists at full structure; user explicitly asks for re-init (route to migration mode). |
| Inputs | Repo root, optional `raw/` materials, user choices from interview (preset, overlay, automation level, Obsidian config, bilingual). |
| Outputs | `wiki/` tree, `CLAUDE.md`, `raw/` if missing, `.claude/hooks/`, `.obsidian/` if requested, `.github/workflows/` if requested, first commit. |
| Files read | Existing `CLAUDE.md`, `wiki/`, `raw/` if present. |
| Files written | All wiki tree, hooks, CI workflows, settings. Never touches `wiki/agentops/` or `docs/agentops/` (AgentOps namespace per ADR-004). |
| State updated | New `wiki/log.md` initialized; new `wiki/00_index.md`; new `wiki/graph/*` rebuilt. |
| Review gates | After interview (gate 1), after structure proposal (gate 2). |
| Failure modes | Conflicting `CLAUDE.md`, `raw/` unparseable, Python 3.12+ missing, git not initialized. |
| Rollback | Save state to `.claude/init-state.json` after each operation; on failure, skill resumes or rolls back via `git stash` of created files. |
| Tools | `wiki_engine.py`, `lint.py`, new `tools/init_audit.py` for existing-repo migration. |
| Tests | Pressure scenarios — empty repo, repo with existing wiki, repo with raw/ but no wiki, conflicting CLAUDE.md, hooks already installed. |
| Examples | (lives in skill body — positive: clean init; negative: re-init without migration mode) |
| Integrations | If raw/ present, hands off to `ingest` for first sources; if AgentOps installed, surfaces this fact (does not auto-init AgentOps). |

### 4.2 `/alpha-wiki:ingest`

| Dimension | Specification |
|---|---|
| Purpose | Convert raw artifact(s) into wiki page(s) with full provenance. |
| Trigger description | Use when raw materials need to enter the wiki — PDF, OpenAPI spec, ADR, transcript, meeting notes, etc. |
| When NOT to trigger | Source is generated wiki output (would create circular ingest); source is already-ingested artifact. |
| Inputs | Path(s) to source(s) under `raw/`, classification hints if user provides. |
| Outputs | New or updated wiki pages; `wiki/log.md` entry; rebuilt `wiki/graph/*`; handoff summary. |
| Files read | `raw/<path>`, existing wiki pages for cross-reference, `CLAUDE.md` for schema. |
| Files written | `wiki/<entity-type>/<slug>.md` (new or updated); `wiki/log.md` (append); `wiki/graph/*` (rebuild). Never writes to `raw/` (immutable). |
| State updated | log.md, graph artifacts, optionally `wiki/index/*` indexes. |
| Review gates | If schema-evolve triggered: gate before adding new entity type (per ADR for schema changes); else no gate. |
| Failure modes | Source unparseable; no slot fits and user rejects schema-evolve; cross-reference target missing; provenance metadata cannot be attached. |
| Rollback | Atomic per-page commit; failed ingest leaves `raw/` untouched and rolls back partial wiki writes. |
| Tools | `wiki_engine.py` for graph ops; new `tools/ingest_pipeline.py` for orchestration; new `tools/classifier.py` for category detection; new `tools/contradiction_detector.py` for stale-claim flagging. |
| Tests | PDF mixed content, OpenAPI YAML, transcript, ADR markdown, contradicting claim, oversized file, file with no parseable structure. |
| Pipeline | Source validation → provenance capture → classification (11 categories) → chunking → entity extraction → claim extraction → page create/update → frontmatter enforcement → cross-link insertion → backlink update → contradiction detection → stale-claim flagging → open-questions extraction → risk extraction → schema-evolve trigger if needed → context_brief rebuild → post-ingest lint → handoff summary. |
| Integrations | Triggers `evolve` if no slot fits. Updates `index/*` indexes. Writes log.md entry consumed by `status`. |

### 4.3 `/alpha-wiki:query`

| Dimension | Specification |
|---|---|
| Purpose | Answer a question from the wiki with truth-status taxonomy and citations. |
| Trigger description | Use when the user asks a question that should be answered from project knowledge — "what did we decide about X", "what's our policy on Y", "is there research on Z". |
| When NOT to trigger | Question is about external world (use web_search); question requires wiki mutation (use `edit` or `ingest`). |
| Inputs | Question text. |
| Outputs | Answer with sections: accepted facts, assumptions, risks, open questions, stale claims. Citations as wiki paths (with line ranges where useful). Contradictions flagged explicitly. Optional synthesis page if requested by user. |
| Files read | `wiki/graph/context_brief.md` first, then `wiki/00_index.md`, then targeted page reads. |
| Files written | None by default. Synthesis page only on explicit request. No silent wiki mutation. |
| State updated | None. |
| Review gates | None for read-only query; if user requests synthesis page, normal `ingest` gates apply. |
| Failure modes | No relevant pages found; conflicting answers across pages; question too broad to answer. |
| Tools | New `tools/wiki_search.py` (BM25 over wiki/ if Phase 6 adds it; for MVP, file-grep + index lookup). |
| Tests | Question with conflicting evidence, question with stale answer, question with no answer, question requiring synthesis across 5+ pages. |
| Integrations | Reads context_brief produced by `wiki_engine.py`. Reads indexes produced by `ingest`. |

### 4.4 `/alpha-wiki:lint`

| Dimension | Specification |
|---|---|
| Purpose | Structural validation of wiki integrity. |
| Trigger description | Use when validating wiki consistency before commit, after ingest, in CI, or on user request. |
| Inputs | Optional path filter, mode flag (`--fix`, `--suggest`, `--dry-run`, `--ci`, `--pre-commit`). |
| Outputs | Severity-tagged list of issues: 🔴 errors, 🟡 warnings, 🟢 info. CI mode exits non-zero on 🔴. |
| Files read | All `wiki/**/*.md`, `CLAUDE.md` for schema. |
| Files written | None unless `--fix` mode; then safe corrections only (missing reverse links, frontmatter normalization, etc.). |
| Checks | Broken links, missing backlinks, orphan pages, missing frontmatter, invalid frontmatter, duplicate slugs, duplicate entities by alias, stale pages, contradiction markers, missing provenance, invalid entity types, schema drift, missing migration notes, unresolved open questions, dependency-rule violations from architectural overlay. |
| Modes | `--fix` (auto-safe corrections), `--suggest` (LLM-assisted manual fixes), `--dry-run` (report only), `--ci` (exit non-zero on 🔴), `--pre-commit` (block 🔴, allow 🟡). |
| Tools | `lint.py` — pure Python, deterministic, fully tested. Extended with per-check modules in `lint_checks/`. |
| Tests | Existing test suite preserved; new tests per added check. |
| Integrations | Invoked by pre-commit hook, session-end hook, CI workflow, `daily-maintenance`, `status`, `cto-review` (when AgentOps present). |

### 4.5 `/alpha-wiki:status`

| Dimension | Specification |
|---|---|
| Purpose | Operational dashboard: wiki health and suggested next actions. |
| Trigger description | Use when the user asks "what's the state of the wiki", "is anything broken", "what should I do next", or wants a periodic health check. |
| Inputs | Optional period (default: last 7 days). |
| Outputs | Sections: recent changes, health score, stale pages, open questions, risks, schema changes, broken links, pages-by-entity-type, high-degree nodes, isolated nodes, last ingest, last review, pending reviews, suggested next actions, integration status (only if AgentOps detected). |
| Files read | `wiki/log.md`, `wiki/graph/*`, lint output, indexes. |
| Files written | None. |
| Health score formula | (defined in `tools/status_report.py`; weighted combination of: orphan ratio, stale ratio, broken-link count, missing-frontmatter count, lint 🔴 count). |
| Suggested-next-actions logic | Priority-ranked list derived from severity-weighted issues. Top 5 surfaced. |
| Tools | New `tools/status_report.py`. |
| Tests | Empty wiki, one-page wiki, 100-page wiki with stale pages, wiki with broken links. |
| Integrations | Reads outputs from `lint`, `wiki_engine.py`. If AgentOps detected, includes section pointing to `<state-backend>/agentops/state/project_state.md`. |

### 4.6 `/alpha-wiki:evolve`

| Dimension | Specification |
|---|---|
| Purpose | Add a new entity type to the wiki schema. |
| Trigger description | Use when ingest finds an artifact that fits no existing entity type, or when the user explicitly requests a new type. |
| Inputs | Proposed type name, target frontmatter, target section template, link rules, optional generated child skill. |
| Outputs | Updated `CLAUDE.md`, new frontmatter template, schema-change log entry, optional generated child skill (e.g. `/alpha-wiki:ingest-<type>`), migration plan for existing pages affected by schema change. |
| Files read | `CLAUDE.md`, all wiki pages of any potentially-affected types. |
| Files written | `CLAUDE.md` (updated section), `wiki/<new-type>/.frontmatter-template.yaml`, `wiki/log.md` (schema-change entry). |
| State updated | Schema (gated). Migration plan written to `wiki/migrations/<date>-<type>.md` if migrations needed. |
| Review gates | Always gated by default (schema-evolve mode `gated`). User confirms before schema change is applied. Mode `auto` allows automatic with rollback path via git. |
| Failure modes | Type name conflict with existing slug; schema change breaks cross-ref rules; migration plan unsafe. |
| Rollback | Schema changes are git-tracked; revert via standard git operations. Migration plan execution is separate and gated independently. |
| Tools | `wiki_engine.py` schema operations. |
| Tests | Add type that conflicts with existing slug, add type that breaks cross-ref rules, add type and verify CLAUDE.md update is correct. |
| Integrations | Triggered by `ingest` when no slot fits; user-invokable directly. |

### 4.7 `/alpha-wiki:spawn-agent`

| Dimension | Specification |
|---|---|
| Purpose | Generate a wiki-aware Claude Code subagent. Wiki-scoped only — does not own team-role logic (per ADR-006). |
| Trigger description | Use when the user wants a custom subagent that respects wiki mutability rules. Use as registration helper when called by AgentOps `agent-skills-bootstrap`. |
| When NOT to trigger | User wants AgentOps team agents — those are owned by AgentOps `agent-skills-bootstrap`. This skill never bootstraps team roles. |
| Inputs | Subagent role name, readable paths, writable paths, handoff format, optional team-role payload (when called by AgentOps). |
| Outputs | `<.claude/agents/<name>.md` or skill at `.claude/skills/agent-<name>/SKILL.md`. |
| Files read | `CLAUDE.md` for mutability matrix, `wiki/02_agent_hierarchy.md` if exists. |
| Files written | New agent file. Updates `wiki/02_agent_hierarchy.md` to register the new agent. |
| Hard constraint | Source contains zero references to AgentOps universal agent names (CTO Integration, Domain Agent, etc.). Team-role logic stays in AgentOps. |
| Failure modes | Mutability matrix conflict; agent name collision. |
| Tools | `wiki_engine.py` for hierarchy update. |
| Tests | Standalone use without AgentOps; use as helper called by AgentOps with team-role payload; ensure no team-role logic leaks in. |
| Integrations | Standalone path: user invokes directly. Helper path: AgentOps `agent-skills-bootstrap` calls with team-role context as parameters. |

### 4.8 `/alpha-wiki:render`

| Dimension | Specification |
|---|---|
| Purpose | Refresh Obsidian config or generate static HTML / Mermaid graphs. |
| Trigger description | Use when the user wants to refresh the Obsidian view, generate static HTML for sharing, or export the wiki graph. |
| Inputs | Mode flag (`obsidian` | `html` | `mermaid` | `dot`). |
| Outputs | Mode-dependent: refreshed `.obsidian/`, static HTML at `wiki/render/html/` when implemented, Mermaid at `wiki/graph/graph.mmd`, DOT at `wiki/graph/graph.dot`. |
| Files read | All wiki pages and `wiki/graph/*`. |
| Files written | Render output paths. Never touches wiki source pages. |
| Color mapping | Red = repos/services, green = modules/domains/components/adapters, blue = features/functions/flows/application, black = documents/evidence, orange = contracts, light grey = people/tasks. Full path-based rules live in `.obsidian/COLOR-LEGEND.md`. |
| Tools | New `tools/render_html.py` planned; `tools/render_mermaid.py` and `tools/render_dot.py` implemented. |
| Tests | Snapshot tests: sample wiki → expected Mermaid / DOT output. |
| Integrations | Triggered by user; not part of automated hooks. |

### 4.9 `/alpha-wiki:contracts-check`

| Dimension | Specification |
|---|---|
| Purpose | Wiki-level contract integrity check — distinct from generic `lint`. |
| Trigger description | Use when validating contract pages: every contract has a service owner, consumers list is bidirectionally consistent, version bumps have migration notes. |
| When NOT to trigger | Generic structural validation — use `lint`. |
| Inputs | Optional path filter to specific contract types. |
| Outputs | Severity-tagged list: contracts without service, consumers missing, version-bump-without-migration, contract pages overlapping by definition. |
| Files read | `wiki/contracts/**/*.md`, `wiki/modules/**/*.md`. |
| Files written | None unless `--fix`. |
| Tools | New `tools/contracts_check.py`. |
| Tests | Contract with no consumers when modules reference it; contract version bump without migration notes; new contract overlapping existing. |
| Integrations | Invoked by pre-commit hook for contract changes; called by `cto-review` when AgentOps present. |

### 4.10 `/alpha-wiki:claims-check`

| Dimension | Specification |
|---|---|
| Purpose | Detect contradictions and stale claims across the wiki. |
| Trigger description | Use when validating claim consistency — finding pages that contradict each other, claims past their freshness window, claims missing provenance. |
| Inputs | Optional period filter (e.g. only claims older than 90 days). |
| Outputs | Contradicting claim pairs with citations; stale claims by frontmatter date; claims missing provenance metadata. |
| Files read | All pages with claim-bearing frontmatter or content. |
| Files written | None unless `--fix` adds `stale: true` markers. |
| Tools | New `tools/claims_check.py`. |
| Tests | Contradicting claims across pages; claim referenced as stale via frontmatter; claim with no provenance. |
| Integrations | Called by `cto-review` when AgentOps present; user-invokable. |

### 4.11 `/alpha-wiki:daily-maintenance`

| Dimension | Specification |
|---|---|
| Purpose | Daily housekeeping bundle: lint --fix, context_brief rebuild, log append, stale-page surface. |
| Trigger description | Use as part of session-end hook or as manual occasional run. |
| Inputs | None. |
| Outputs | Idempotent maintenance results: lint output, rebuilt context_brief, log entry, stale pages list. |
| Files read | All wiki + log. |
| Files written | log.md (append), graph/* (rebuild), lint --fix corrections. |
| Idempotency | Safe to run repeatedly; failures non-destructive. |
| Tools | Composes existing skills. |
| Tests | Run twice in succession produces identical state on second run. |
| Integrations | Invoked by session-end hook; user-invokable. |

---

## 5. Tooling

Pure-Python, deterministic, no LLM. Tested fully.

| Tool | Purpose |
|---|---|
| `tools/lint.py` (existing) | Structural lint engine. |
| `tools/wiki_engine.py` (existing) | Graph rebuild, edges, context_brief, open_questions. |
| `tools/init_audit.py` (new) | Existing-repo audit for `init` migration mode. |
| `tools/ingest_pipeline.py` (new) | Ingest orchestration (validation, classification, page-write, lint). |
| `tools/classifier.py` (new) | Category detection (11 raw artifact categories). |
| `tools/contradiction_detector.py` (new) | Stale-claim and contradiction detection. |
| `tools/wiki_search.py` (new) | Wiki search (file-grep + index lookup; BM25 only if Phase 6). |
| `tools/status_report.py` (new) | Health score, suggested next actions. |
| `tools/contracts_check.py` (new) | Contract-specific lint. |
| `tools/claims_check.py` (new) | Claim consistency. |
| `tools/render_html.py` (new) | Static HTML output. |
| `tools/render_mermaid.py` (implemented) | Mermaid output with typed clusters and role colors. |
| `tools/render_dot.py` (implemented) | DOT output with typed clusters and role colors. |

All new tools follow the existing `lint.py` / `wiki_engine.py` style: pure Python, deterministic, single-responsibility, fully unit-tested.

---

## 6. Hooks and CI

Same set as already shipped, with extensions where Phase 1a hardens.

| Hook | When | Action |
|---|---|---|
| session-start | Session start | `cat wiki/graph/context_brief.md` |
| post-tool-use | After write to `wiki/` | `tools/wiki_engine.py rebuild-edges`, `rebuild-context-brief`, `rebuild-open-questions` |
| session-end | Session end | `lint --suggest`; append `log.md` entry; surface stale pages |
| pre-commit | Before git commit | `lint --fix --pre-commit` (block 🔴) |
| CI: `wiki-lint.yml` | On push / PR | Full lint, fail if 🔴 |
| CI: `wiki-review.yml` | Weekly cron | Backed wiki-level review via `/alpha-wiki:review` |
| CI: `wiki-rollup.yml` | Monthly cron | Backed wiki-level rollup via `/alpha-wiki:rollup month --write` |

---

## 7. Detection of optional layers

Alpha-Wiki **never imports** AgentOps or Superpowers. It does, however, surface their presence in `status` output as informational only:

- If AgentOps detected: `status` adds a section "AgentOps state backend: `wiki/agentops/`" pointing to current phase.
- If Superpowers detected: no special handling at Alpha-Wiki level (Superpowers is consumed by AgentOps, not Alpha-Wiki).

Detection mechanism: read `~/.claude/plugins/` or check for skill availability. Cached per session.

---

## 8. Backwards compatibility

Phase 1a preserves all existing behaviors:

- All 8 existing skills remain at their current slash command paths.
- All 45 existing tests must continue to pass.
- Plugin manifest remains compatible with current marketplace add command.
- Wiki structure produced by current `init` remains valid; Phase 1a only adds capabilities, not breaking changes.
- Schema evolution remains gated by default with `auto` opt-in unchanged.

Breaking changes, if discovered necessary during hardening, require explicit ADR and migration tooling.

---

## 9. What is NOT in Alpha-Wiki

For clarity:

- No agent team roles, hierarchy, or operating model.
- No `init-project`, `onboard`, `plan-slice`, `execute-slice`, `cto-review`, or anything similar.
- No 9 universal agents, no project-specific agent detection.
- No 4 communication mechanisms (Handoff / CCR / ADR / Integration Issue) at the AgentOps level — though wiki pages of these types may live in the wiki, owned by AgentOps.
- No architecture canon templates (Clean / Hexagonal docs).
- No Domain Freeze ceremony.
- No TDD enforcement.
- No subagent dispatch.
- No two-stage review.
- No verification-before-done workflow.
- No release readiness checks.
- No integration with Superpowers (AgentOps owns the adapter).

All of these belong to AgentOps. See `02-agentops.md`.
