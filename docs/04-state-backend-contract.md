# 04 — State backend contract

> Specification for the state backend abstraction. Defines path schema, detection logic, read/write contract, and the `wiki-backend-adapter` Tier 2 skill inside AgentOps.

References: `00-architecture.md` for boundaries, `02-agentops.md` for AgentOps Tier 1 skills, `01-alpha-wiki.md` for wiki ownership, `adr/ADR-001`, `adr/ADR-004`, `adr/ADR-006`.

---

## 1. Purpose

AgentOps writes operational state: 7 living state files, decisions, handoffs, CCRs, integration issues, reviews, plans, architecture canon, Domain Freeze artifacts, project-specific agent registrations.

This state must:

- Persist across sessions
- Be readable by future agent invocations
- Live in markdown (auditable, diffable, git-trackable)
- Not collide with Alpha-Wiki's root namespace when Alpha-Wiki is present
- Work identically regardless of whether Alpha-Wiki is present

The state backend abstraction routes state operations to the correct path based on Alpha-Wiki detection.

---

## 2. Path schema

### 2.1 State backend root

| Alpha-Wiki present? | State backend root |
|---|---|
| Yes | `wiki/` |
| No | `docs/` |

### 2.2 AgentOps subnamespace

AgentOps writes only under `<state-backend-root>/agentops/`. This subnamespace is constant regardless of which root is in use.

### 2.3 Full path layout

Identical structure under both backends:

```
<state-backend-root>/agentops/
├── state/
│   ├── project_state.md
│   ├── agent_backlog.md
│   ├── open_questions.md
│   ├── risk_register.md
│   ├── integration_status.md
│   └── release_readiness.md
├── reviews/
│   └── YYYY-WW-cto-review.md
├── handoffs/
│   └── YYYY-MM-DD-<agent>-<task>.md
├── decisions/
│   ├── ADR-NNN-<title>.md
│   └── decision_log.md
├── ccr/
│   └── CCR-NNN-<title>.md
├── integration-issues/
│   └── II-NNN-<title>.md
├── plans/
│   └── YYYY-MM-DD-<slug>.md
├── architecture/
│   ├── three-layer-architecture.md
│   ├── layer-boundaries.md
│   ├── ports-and-adapters.md
│   ├── infrastructure.md
│   ├── shared-kernel.md
│   ├── dependency-rules.md
│   ├── migration-plan.md
│   └── feature-placement-checklist.md
└── domain/
    ├── naming-glossary.md
    ├── status-model.md
    ├── event-names.md
    └── api-names.md
```

Plus, when Alpha-Wiki is absent (fallback only):

```
docs/agentops/
└── context_summary.md       # Replacement for wiki/graph/context_brief.md
```

When Alpha-Wiki is present, `wiki/graph/context_brief.md` is consumed directly and `context_summary.md` is not generated.

---

## 3. Hard prohibitions

AgentOps must not write to:

- `wiki/state/`
- `wiki/reviews/`
- `wiki/handoffs/`
- `wiki/decisions/`
- `wiki/risks/`
- `wiki/contracts/`
- Any other root-level wiki directory

These belong to Alpha-Wiki.

Crossing the namespace is a hard error. Detection mechanism:

- Pre-commit hook check: scan staged files; flag any AgentOps-owned content written outside `wiki/agentops/` or `docs/agentops/`.
- Integration test: assert no writes to forbidden paths during AgentOps Tier 1 skill execution.

---

## 4. The `wiki-backend-adapter` skill

Tier 2 skill inside AgentOps at `agentops/skills/_tier2_internal/wiki-backend-adapter/`. Invoked at the start of every Tier 1 skill that writes state.

### 4.1 Responsibilities

1. Detect Alpha-Wiki presence at session start (cached for session).
2. Resolve the state backend root: `wiki/` if Alpha-Wiki present, else `docs/`.
3. Provide path-resolution helpers: `resolve_path(category, filename)` → `<state-backend-root>/agentops/<category>/<filename>`.
4. Verify that no AgentOps-owned writes target paths outside the AgentOps subnamespace.
5. Surface integration capabilities when Alpha-Wiki is present (see §5).
6. Log backend choice to `decision_log.md`.

### 4.2 Detection

Mechanism (same as `superpowers-adapter` §3):

1. Plugin marker check via `~/.claude/plugins/`.
2. Skill availability check for `alpha-wiki:*` skills.
3. Cache result for session.

If either succeeds, Alpha-Wiki is considered available and `wiki/` is the state backend root.

### 4.3 Path resolution

Always:

```
resolve_path(category, filename) = <state-backend-root>/agentops/<category>/<filename>
```

Categories: `state`, `reviews`, `handoffs`, `decisions`, `ccr`, `integration-issues`, `plans`, `architecture`, `domain`.

The adapter never returns paths outside this namespace.

### 4.4 Logging

Backend choice logged at session start:

```markdown
## [2026-04-29 09:14] backend-choice | wiki-backend-adapter | alpha_wiki_available=true → state-backend=wiki/agentops/
```

---

## 5. Integration capabilities (when Alpha-Wiki present)

When Alpha-Wiki is detected, AgentOps gains these integration paths via the wiki-backend-adapter:

### 5.1 Ingest of raw materials

`init-project` Op 3 delegates raw ingestion to Alpha-Wiki `ingest`:

- AgentOps emits agent instruction: "Invoke `alpha-wiki:ingest` for each file in raw/."
- Alpha-Wiki creates wiki pages under appropriate `wiki/<entity-type>/`.
- AgentOps reads the resulting wiki pages for project-specific agent detection (Op 5) and Domain Freeze (Op 8).

### 5.2 Agent registration via spawn-agent

Per ADR-006: `agent-skills-bootstrap` (AgentOps Tier 2) uses Alpha-Wiki `spawn-agent` as a registration helper:

- AgentOps owns team-role definitions (the 9 universal roles, project-specific role payloads).
- AgentOps emits agent instruction: "Invoke `alpha-wiki:spawn-agent` with this team-role payload to create a wiki-aware agent skill."
- Alpha-Wiki `spawn-agent` produces the SKILL.md at `.claude/skills/agent-<name>/`, with wiki mutability matrix attached.

### 5.3 Wiki-level lints in cto-review

`cto-review` Workflow steps 3 (contract drift) and content checks delegate to Alpha-Wiki:

- AgentOps emits agent instructions to invoke `alpha-wiki:contracts-check` and `alpha-wiki:claims-check`.
- Results appear in the review document under AgentOps schema.

### 5.4 Context consumption

AgentOps `onboard` reads `wiki/graph/context_brief.md` directly when Alpha-Wiki is present. When absent, AgentOps generates `docs/agentops/context_summary.md` itself with a simpler aggregation logic.

### 5.5 Lint enforcement at pre-commit

Pre-commit hook chains:
- `alpha-wiki:lint --pre-commit` (if Alpha-Wiki present, lints wiki structure)
- `agentops:dependency-rule-check` (always, lints Architecture canon compliance)
- `agentops:pre-integration-check` (always, when applicable)

Each layer lints what it owns.

---

## 6. Fallback (when Alpha-Wiki absent)

AgentOps works standalone with Markdown fallback. The state backend root resolves to `docs/`. All paths resolve identically to `docs/agentops/<category>/<filename>`.

Specifically:

| Capability | Alpha-Wiki present | Alpha-Wiki absent |
|---|---|---|
| Raw ingestion | `alpha-wiki:ingest` | Native AgentOps minimal ingest: copies raw files into `docs/agentops/raw-summaries/` with a brief LLM summary header |
| Agent registration | `alpha-wiki:spawn-agent` as helper | Direct write to `.claude/skills/agent-<name>/SKILL.md` from template |
| Contract lint | `alpha-wiki:contracts-check` | Native check in `agentops:contract-change-request` skill |
| Claim freshness | `alpha-wiki:claims-check` | Not available in fallback (deferred to Phase 6 if usage justifies) |
| Context summary | `wiki/graph/context_brief.md` | `docs/agentops/context_summary.md` regenerated by AgentOps `onboard` |
| Pre-commit wiki lint | `alpha-wiki:lint` | Skipped (no wiki to lint) |

The fallback is functionally sufficient. Users can adopt Alpha-Wiki later; the migration is a single directory rename plus `alpha-wiki:init` against the existing project.

---

## 7. Migration: Markdown fallback → Alpha-Wiki

When a user starts with AgentOps standalone and later adds Alpha-Wiki:

1. User installs Alpha-Wiki plugin.
2. User runs `alpha-wiki:init` in the project. Alpha-Wiki bootstraps `wiki/` and `CLAUDE.md` without touching `docs/agentops/`.
3. User runs migration helper (provided as part of `wiki-backend-adapter`): `agentops:migrate-to-wiki`. This script:
   - Verifies all AgentOps state under `docs/agentops/`.
   - Moves `docs/agentops/` to `wiki/agentops/` as a single directory rename.
   - Updates any path references in state files (none expected, paths are relative within `agentops/`).
   - Regenerates `wiki/graph/*` via Alpha-Wiki `wiki_engine.py rebuild-all`.
   - Logs the migration to `decision_log.md`.
4. Subsequent sessions detect Alpha-Wiki, route state to `wiki/agentops/`, gain integration capabilities (§5).

The reverse migration (Alpha-Wiki → Markdown fallback) is supported via `agentops:migrate-to-fallback` but discouraged: users typically add Alpha-Wiki, rarely remove it.

---

## 8. Validation

The state backend contract is verified by:

1. **Path-resolution test**: `resolve_path("state", "project_state.md")` returns the expected path under both backends.
2. **Hard-prohibition test**: integration test asserts no writes to `wiki/state/`, `wiki/decisions/`, etc. during any AgentOps Tier 1 invocation.
3. **Standalone test**: AgentOps `init-project` runs end-to-end without Alpha-Wiki; all state lands under `docs/agentops/`.
4. **Integrated test**: AgentOps `init-project` runs end-to-end with Alpha-Wiki; all state lands under `wiki/agentops/`; root-level wiki paths untouched.
5. **Migration test**: state under `docs/agentops/` after `agentops:migrate-to-wiki` ends up under `wiki/agentops/` with no content changes.
6. **Logging completeness test**: every session start produces a backend-choice entry in `decision_log.md`.

---

## 9. What is NOT in this contract

For clarity:

- No automatic install of Alpha-Wiki if absent. AgentOps detects, it does not install.
- No write to Alpha-Wiki root namespace (`wiki/state/`, etc.). Hard prohibition (§3).
- No leakage of AgentOps schema into Alpha-Wiki schema. Wiki entity types remain Alpha-Wiki-defined; AgentOps state files use AgentOps frontmatter.
- No silent backend switch mid-session. Detection cached at session start (per ADR-002 same principle).
- No bidirectional dependency. Alpha-Wiki does not detect AgentOps; only the reverse.
