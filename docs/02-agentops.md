# 02 — AgentOps

> Specification for the AgentOps plugin. Agent operating model layer. Standalone product. Optionally integrates with Alpha-Wiki (knowledge backend) and Superpowers (execution discipline) via process-level adapters.

References: `00-architecture.md` for boundaries, `_references.md` for source patterns, `03-superpowers-adapter.md`, `04-state-backend-contract.md`, `adr/ADR-001`, `adr/ADR-002`, `adr/ADR-004`, `adr/ADR-006`.

---

## 1. Slot in the ecosystem

AgentOps is the **agent operating model layer**. It owns:

- The 9 universal agent roles (always installed)
- N project-specific agent roles (detected during `init-project`)
- The 4 communication mechanisms: Handoff / CCR / ADR / Integration Issue
- The 9 review levels
- The 5 operating rhythms: execution / weekly / pre-integration / pre-release / audit-challenge
- The architecture canon templates (Clean + Hexagonal)
- The Domain Freeze ceremony
- 5 user-facing Tier 1 skills
- 17 internal Tier 2 sub-skills
- The state backend abstraction (`wiki/agentops/` or `docs/agentops/`)

It does not own:

- Wiki internals — Alpha-Wiki when present
- TDD / subagent dispatch / brainstorm enforcement — Superpowers when present, AgentOps native fallback otherwise

---

## 2. Repository

New repository, working name `agentops`. Owner TBD before Phase 1b kickoff.

```
agentops/
├── .claude-plugin/plugin.json
├── README.md
├── INSTALL.md
├── skills/
│   ├── _tier1/                       # User-facing
│   │   ├── init-project/SKILL.md
│   │   ├── onboard/SKILL.md
│   │   ├── plan-slice/SKILL.md
│   │   ├── execute-slice/SKILL.md
│   │   └── cto-review/SKILL.md
│   ├── _tier2_internal/              # Invoked by Tier 1 or other Tier 2
│   │   ├── canon-install/SKILL.md
│   │   ├── domain-freeze/SKILL.md
│   │   ├── contract-change-request/SKILL.md
│   │   ├── adr-write/SKILL.md
│   │   ├── dependency-rule-check/SKILL.md
│   │   ├── agent-handoff/SKILL.md
│   │   ├── integration-issue/SKILL.md
│   │   ├── state-files-update/SKILL.md
│   │   ├── agent-skills-bootstrap/SKILL.md
│   │   ├── pre-integration-check/SKILL.md
│   │   ├── tdd-cycle/SKILL.md
│   │   ├── two-stage-review/SKILL.md
│   │   ├── verification-before-done/SKILL.md
│   │   ├── release-readiness/SKILL.md
│   │   ├── audit-challenge/SKILL.md
│   │   ├── wiki-backend-adapter/SKILL.md
│   │   └── superpowers-adapter/SKILL.md
│   └── agents/                       # 9 universal agent skills
│       ├── cto-integration/SKILL.md
│       ├── product-business-analyst/SKILL.md
│       ├── domain-and-contracts/SKILL.md
│       ├── technical-analyst/SKILL.md
│       ├── security-architect/SKILL.md
│       ├── qa-integration/SKILL.md
│       ├── documentation/SKILL.md
│       ├── release-manager/SKILL.md
│       └── audit-challenge/SKILL.md
├── commands/                         # /agentops:* slash commands
├── templates/                        # Templates copied into projects
│   ├── communication/                #   handoff, ccr, adr, integration-issue
│   ├── state/                        #   7 living state files
│   ├── architecture/                 #   8 canon docs
│   ├── domain/                       #   4 freeze docs
│   ├── frontmatter/                  #   per-entity frontmatter schemas
│   ├── hooks/
│   ├── workflows/                    #   GitHub Actions
│   └── project-specific-agents/      #   templates for detected agents
├── tools/
│   ├── state_init.py
│   ├── classifier.py                 # Project-specific agent detection
│   ├── canon_install.py
│   ├── dependency_check.py
│   ├── contract_check.py
│   ├── audit_aggregator.py
│   └── _env.py
├── references/
│   ├── operating-model.md
│   ├── communication-protocol.md
│   ├── architecture-canon.md
│   ├── domain-freeze.md
│   ├── classifier-taxonomy.md
│   ├── review-levels.md
│   ├── rhythms.md
│   ├── agent-roles/
│   │   ├── universal/                # 9 files
│   │   └── project-specific/         # All possible templates
│   ├── hooks-design.md
│   └── examples/
├── docs/
└── tests/
```

Slash command namespace: `/agentops:*` (e.g. `/agentops:init-project`, `/agentops:plan-slice`).

---

## 3. Tier 1 skills (5 user-facing)

### 3.1 `/agentops:init-project`

| Dimension | Specification |
|---|---|
| Purpose | One-time bootstrap of AgentOps for a project. |
| Trigger description | Use when bootstrapping AgentOps for a new or existing project. Triggers: "init project", "set up agent team", "agentops bootstrap", "set up project operating model". |
| When NOT to trigger | AgentOps already initialized in this repo (use repair / update modes if available); only wiki bootstrap needed (use `alpha-wiki:init`). |
| Inputs | Repo root, optional `raw/` materials, plugin presence (Alpha-Wiki, Superpowers), interview answers. |
| Outputs | 9 universal agent skills installed in `.claude/skills/`; N project-specific agents detected and installed; state backend chosen and namespaced under `agentops/`; 8 architecture canon docs; Domain Freeze artifacts; ADR-001 (canon adoption), ADR-002 (Domain Freeze); first vertical slice plan; handoff report. |
| Files read | All `raw/*` if present; existing `CLAUDE.md`, `AGENTS.md`. |
| Files written | `.claude/skills/agent-*/SKILL.md` (9 + N); `<state-backend>/agentops/state/*` (7 living files); `<state-backend>/agentops/architecture/*` (8 canon docs); `<state-backend>/agentops/domain/*` (4 freeze docs); `<state-backend>/agentops/decisions/ADR-001.md` and `ADR-002.md`; `<state-backend>/agentops/plans/<date>-vertical-slice-1.md`; `CLAUDE.md` (created or appended); `.claude/settings.local.json`; optional `.claude/hooks/*`; optional `.github/workflows/agentops-*.yml`. State backend resolves to `wiki/` if Alpha-Wiki present, else `docs/`. |
| State updated | `project_state.md` (initialized), `agent_backlog.md` (initialized), `decision_log.md` (ADR-001, ADR-002), `release_readiness.md` (initialized). |
| Review gates | After interview (gate 1), after ingest + canon install (gate 2), after agent detection (gate 3), after Domain Freeze (gate 4). |
| Failure modes | Missing prerequisites; conflicting CLAUDE.md; raw/ unparseable; user rejects gate. |
| Rollback | State after each operation saved to `.claude/agentops-init-state.json`. On failure, skill resumes or rolls back via `git stash` of created files. |
| Tools | Reuses Alpha-Wiki `wiki_engine.py` if present (via wiki-backend-adapter); AgentOps `tools/state_init.py` for fallback; `tools/classifier.py` for project-specific agent detection. |
| Tests | Empty repo; repo with existing CLAUDE.md; repo with Alpha-Wiki only; repo with Alpha-Wiki + Superpowers; repo with Superpowers only; repo with neither. |
| Alpha-Wiki integration | wiki-backend-adapter detects Alpha-Wiki. If present: state under `wiki/agentops/`, ingest of raw via Alpha-Wiki `ingest`, agent registration via Alpha-Wiki `spawn-agent` (per ADR-006 — as helper only). |
| Fallback without Alpha-Wiki | State under `docs/agentops/`. Minimal context summary at `docs/agentops/context_summary.md`. |
| Superpowers integration | superpowers-adapter detects Superpowers; logs detection. No active integration in `init-project` itself (planning / execution skills use Superpowers, not init). |

#### 3.1.1 The 10 operations

`init-project` runs 10 operations in order, with gates after specified operations. State persists between operations for resumability.

| Op | Operation | Gate after? |
|---|---|---|
| 1 | Interview (8 questions, one at a time) | Yes |
| 2 | wiki-bootstrap (delegated to Alpha-Wiki if present, native skeleton otherwise) | No |
| 3 | Ingest raw materials (delegated to Alpha-Wiki `ingest` if present) | Yes |
| 4 | Bootstrap 9 universal agent skills | No |
| 5 | Detect and bootstrap project-specific agents | Yes |
| 6 | Initialize templates and state files | No |
| 7 | Install Architecture canon (8 docs, ADR-001 created) | No |
| 8 | Domain Freeze ceremony (4 docs, ADR-002 created) | Yes |
| 9 | Install hooks, indexes, graph artifacts; initial git commit | No |
| 10 | Generate first vertical slice plan; output handoff report | No |

#### 3.1.2 The 8 interview questions

Multiple choice where possible. One question at a time.

1. Type of project (software / DeFi / research / internal / other)
2. Architecture canon mode (strict / lenient / off)
3. Schema-evolve mode (gated / auto)
4. Subagent dispatch mode (subagent / inline)
5. Automation level (full / hooks-only / minimal)
6. CI platform (GitHub Actions / GitLab CI / skip)
7. Obsidian view (yes / no)
8. Existing raw materials (process all / select / skip)

Answers saved to `.claude/agentops-init-config.json` for repeatable replay.

### 3.2 `/agentops:onboard`

| Dimension | Specification |
|---|---|
| Purpose | Load compressed project context at session start. |
| Trigger description | Use when starting a new session on an AgentOps-initialized project, or when user asks "where are we", "what's the state", "load context". |
| When NOT to trigger | Project is not AgentOps-initialized (suggest `init-project`). |
| Inputs | State backend path (auto-detected). |
| Outputs | ≤500-word summary: current phase, active workstreams, open blockers, my assigned tasks (if owner identified), recent decisions, recent risks. |
| Files read | `<state-backend>/agentops/state/project_state.md`, `agent_backlog.md`, `open_questions.md`, `decision_log.md` (last 10), `risk_register.md` (open). If Alpha-Wiki present: `wiki/graph/context_brief.md`. |
| Files written | None. |
| State updated | None. |
| Tools | None — pure read + LLM synthesis. |
| Tests | Empty backlog; backlog with 50 items; backlog with conflicting priorities. |
| Integrations | Optionally invoked by session-start hook automatically. |

### 3.3 `/agentops:plan-slice`

| Dimension | Specification |
|---|---|
| Purpose | Turn a goal into a reviewed, decomposed implementation slice with TDD steps and owner assignment. |
| Trigger description | Use when planning a new feature, bugfix, or vertical slice. Triggers: "plan slice", "plan feature", "decompose this". |
| When NOT to trigger | Plan already exists; user wants to execute (use `execute-slice`). |
| Inputs | Feature description, optional constraints. |
| Outputs | Plan document at `<state-backend>/agentops/plans/<date>-<slug>.md` with file structure, decomposed tasks, TDD steps per task, owner per task, verification commands per task. |
| Files read | State files, contracts, Domain Freeze artifacts, architecture canon. If Alpha-Wiki present: `wiki/graph/context_brief.md` and relevant wiki pages. |
| Files written | Plan document. |
| State updated | `agent_backlog.md` (new tasks added with status TODO). |
| Workflow | (1) Brainstorm (Socratic, one-question-at-a-time, with gate). (2) Architecture review (Domain + Security gate — review levels 1). (3) Plan review (CTO gate — review level 2). (4) Decompose into tasks with TDD steps, owner, files, verification. (5) Map file structure (Superpowers writing-plans pattern). (6) Lint plan: scope check, file structure check, dependency-rule pre-check. |
| Review gates | 3 gates: design approved (level 1), plan approved (level 2), scope check passed. |
| Tools | `dependency_check.py` for canon compliance pre-check. |
| Tests | Trivial slice; multi-subsystem slice (must trigger scope-check warning); slice that requires schema-evolve. |
| Alpha-Wiki integration | If present: plan stored as wiki page with frontmatter; cross-linked to entities, contracts, decisions; lint runs over plan. |
| Superpowers integration | Process-level adapter only (per ADR-002). If Superpowers detected: instruct the agent to invoke `superpowers:brainstorming` and `superpowers:writing-plans` as separate skill calls. AgentOps does not call Superpowers programmatically. Output written in AgentOps schema regardless. |
| Fallback without Superpowers | Native AgentOps brainstorm + decomposition discipline embedded in skill body. |

### 3.4 `/agentops:execute-slice`

| Dimension | Specification |
|---|---|
| Purpose | Execute an approved slice with discipline, handoffs, and review. |
| Trigger description | Use when an approved plan exists and the user is ready to implement. Triggers: "execute", "go", "ship the plan". |
| When NOT to trigger | Plan not approved; pre-conditions not met. |
| Inputs | Plan path. |
| Outputs | Implemented code; handoffs in `<state-backend>/agentops/handoffs/`; updated state files; test evidence; optionally CCRs / Integration Issues if surfaced. |
| Files read | Plan, state files, contracts, code under implementation. |
| Files written | Code files (per plan); handoffs; CCR / II if triggered; state file updates. |
| State updated | After each task: `agent_backlog.md` (status), `open_questions.md` (if new question), `risk_register.md` (if new risk), `decision_log.md` (if decision made). |
| Workflow | For each task in plan: (1) dispatch fresh subagent (if subagent platform). (2) TDD cycle (RED/GREEN/REFACTOR). (3) Implement. (4) Two-stage review: spec compliance → code quality (review level 3). (5) Verification-before-done (run verification commands; attach evidence). (6) Write handoff. (7) Atomic state update. (8) If contract change attempted → `contract-change-request` + Domain dispatch. (9) If security risk → `integration-issue` + Security dispatch. (10) Continue to next task. Stop only on blockers. |
| Review gates | Per task: spec compliance (level 3a), code quality (level 3b), verification evidence (verification-before-done). Per slice: integration review (QA + relevant adapters — review level 4). Pre-merge: domain drift (level 5), security invariants (level 6). |
| Failure modes | TDD reveals wrong design → escalate to `/plan-slice`; verification fails → block, fix, retry; CCR rejected → block, replan. |
| Tools | TDD via Superpowers when present (adapter); native fallback otherwise. |
| Tests | Single-task slice; 10-task slice; slice that triggers mid-execution CCR; slice that triggers Integration Issue; slice where TDD reveals wrong design. |
| Alpha-Wiki integration | Handoffs written as wiki pages (under `wiki/agentops/handoffs/`). State updates trigger context_brief rebuild via Alpha-Wiki post-tool-use hook. |
| Superpowers integration | Process-level adapter only. If Superpowers detected: instruct the agent to invoke `superpowers:subagent-driven-development` for subagent dispatch + TDD + review. AgentOps does not call programmatically. Backend choice logged in `decision_log.md`. |
| Fallback without Superpowers | Native discipline: `tdd-cycle`, `two-stage-review`, `verification-before-done` Tier 2 skills embedded. |

### 3.5 `/agentops:cto-review`

| Dimension | Specification |
|---|---|
| Purpose | Weekly or on-demand team-level audit producing a review document. |
| Trigger description | Use when running scheduled weekly review or user invokes audit. Triggers: "cto review", "weekly review", "audit". Auto-invoked by GitHub Actions cron when enabled. |
| Inputs | State backend, period (default: last 7 days). |
| Outputs | Review document at `<state-backend>/agentops/reviews/YYYY-WW-cto-review.md`. |
| Files read | All handoffs in period; all state files; all contracts; all decisions in period; all risks. |
| Files written | Review document; updated `decision_log.md` with resolutions; possibly new ADRs. |
| State updated | `project_state.md` (current phase recap), `decision_log.md` (week resolutions), `release_readiness.md` (updated). |
| Workflow | (1) Aggregate handoffs over period. (2) Documentation Agent updates indexes. (3) Domain Agent contract drift report. (4) Security Agent risk register update. (5) QA coverage update. (6) Release Manager readiness update. (7) CTO 7-question audit. (8) Resolutions → ADR(s). (9) Atomic state update. |
| Review gates | None internally — this skill is itself a review (level 7). |
| Tools | `audit_aggregator.py`. If Alpha-Wiki present: `alpha-wiki:contracts-check` and `alpha-wiki:claims-check`. |
| Tests | Empty period (no handoffs); period with conflicting decisions; period that surfaces new release-blocker. |

#### 3.5.1 The 7 CTO questions

Asked in this exact order at every weekly review:

1. What became source of truth this week?
2. Which decisions are now stale?
3. Where did duplicate terms appear?
4. Which agents are blocked?
5. Which risks became release blockers?
6. Which tests don't cover critical invariants?
7. What needs to be deleted, frozen, or deferred?

Answers persist in the review document. Pattern: weekly answers reveal trends across reviews.

---

## 4. Tier 2 skills (17 internal)

Each invoked by Tier 1 or by other Tier 2. Never called directly by user. Each follows the 15-dimension operating-manual standard. Below: spec contract.

### 4.1 Architecture & contracts (5 skills)

| Skill | Purpose | Invoked by |
|---|---|---|
| `canon-install` | Generate 8 architecture canon docs adapted to project (Clean + Hexagonal). | `init-project` Op 7 |
| `domain-freeze` | Naming glossary, status model, event names, API names + packages skeleton. | `init-project` Op 8 |
| `contract-change-request` | Detect attempted shared-contract change, create CCR file, dispatch Domain Agent. | `execute-slice` when contract change attempted |
| `adr-write` | Standardized ADR creation with required sections (Context / Decision / Reasoning / Alternatives Rejected / Risks / Validation). | `init-project`, `plan-slice`, `execute-slice`, `cto-review` |
| `dependency-rule-check` | Lint code against Clean+Hexagonal dependency rules. | `plan-slice` (pre-check), `execute-slice` (per task), pre-commit hook |

### 4.2 Process & coordination (4 skills)

| Skill | Purpose | Invoked by |
|---|---|---|
| `agent-handoff` | Write handoff after task completion. | `execute-slice` after each task |
| `integration-issue` | Create Integration Issue file when modules don't fit. | `execute-slice`, manual |
| `state-files-update` | Atomic update of 7 living state files. | After every Tier 1 skill operation |
| `agent-skills-bootstrap` | Create 9 universal + N project-specific agent skill files. Uses Alpha-Wiki `spawn-agent` as registration helper when present. | `init-project` Ops 4–5 |

### 4.3 Discipline (3 skills, with Superpowers fallback)

| Skill | Purpose | Native or delegated |
|---|---|---|
| `tdd-cycle` | RED/GREEN/REFACTOR enforcement. | Native if Superpowers absent; instructs agent to invoke `superpowers:test-driven-development` if present |
| `two-stage-review` | Spec compliance pass → code quality pass. | Native if Superpowers absent; instructs agent to invoke `superpowers:requesting-code-review` if present |
| `verification-before-done` | Run verification commands; attach evidence to handoff. | Native if Superpowers absent; instructs agent to invoke `superpowers:verification-before-completion` if present |

### 4.4 Lifecycle (3 skills)

| Skill | Purpose | Invoked by |
|---|---|---|
| `pre-integration-check` | Before merge: shared contracts, no local enums, API/event compat, security invariants, integration tests, status update. | Pre-merge git hook, manual |
| `release-readiness` | 9-step release readiness check. | `release-manager` agent at pre-release |
| `audit-challenge` | Devil's advocate review. | After major change, on user request |

### 4.5 Adapters (2 skills)

| Skill | Purpose | Detail |
|---|---|---|
| `wiki-backend-adapter` | Detect Alpha-Wiki presence; route state operations. | See `04-state-backend-contract.md` |
| `superpowers-adapter` | Detect Superpowers presence; instruct agent to use Superpowers skills when available; embed native fallback. | See `03-superpowers-adapter.md` |

---

## 5. Universal agents (9, always installed)

Each agent ships as a SKILL.md file copied into `.claude/skills/` during `init-project`. Each adapts to the project via placeholder substitution from `01_product_canon.md`.

Per agent, the SKILL.md defines: role, trigger, inputs, outputs, state files read, state files written, review responsibility, allowed tools, workflow, constraints. (15-dimension operating manual.)

| # | Agent | Owns |
|---|---|---|
| 1 | **CTO Integration** | Cross-system coherence, roadmap, architecture alignment, final plan review, weekly 7-question audit. |
| 2 | **Product / Business Analyst** | Product requirements, business value, customer impact, scope decisions. |
| 3 | **Domain & Contracts** | Domain model, contracts, naming, enums, schema. Gatekeeper for CCRs. |
| 4 | **Technical Analyst** | Tech research, alternative evaluation, ADR drafting. |
| 5 | **Security Architect** | Security invariants, threat model, auth, sensitive paths, pre-merge security checks (review level 6). |
| 6 | **QA / Integration** | Tests, coverage, integration, verification evidence. Pre-slice integration review (review level 4). |
| 7 | **Documentation** | Docs, indexes, handoff consistency, state summaries. |
| 8 | **Release Manager** | Release readiness, changelog, rollback, scope freeze. Pre-release review (review level 8). |
| 9 | **Audit / Challenge** | Devil's-advocate review, contradiction detection, risky-assumption flagging, overengineering detection (review level 9). |

The full SKILL.md per agent lives in `references/agent-roles/universal/`.

---

## 6. Project-specific agents (N detected)

Created during `init-project` Op 5 by `tools/classifier.py` analyzing wiki content from Op 3 (or raw materials when wiki absent).

### 6.1 Detection signals

| Signal | Triggers agent |
|---|---|
| UI / React / Vue / frontend mentions | Frontend Agent |
| API / REST / GraphQL / backend service mentions | Backend Agent |
| Order / execution / trade mentions | Execution Agent + Strategy Agent |
| Venue / exchange / DEX / CEX mentions | Venue Adapter Agent |
| Wallet / token / blockchain / on-chain mentions | Kernel Agent + Funding Agent |
| Ledger / fee / accounting mentions | Business / Ledger Agent |
| Position / PnL / portfolio mentions | Portfolio Agent |
| Metrics / monitoring / observability mentions | Observability Agent |
| Load / performance / throughput mentions | Stress / Load Agent |
| ML / model / training / inference mentions | ML Engineer Agent |
| Mobile / iOS / Android / native mentions | Mobile Agent |
| Data pipeline / ETL / warehouse mentions | Data Engineer Agent |
| DevOps / k8s / terraform / infrastructure mentions | DevOps Agent |

### 6.2 Confidence-based behavior

- **High confidence** (multiple strong signals): create automatically, notify user.
- **Medium confidence**: propose to user, wait for confirmation.
- **Low confidence**: skip; user can add manually via `agent-skills-bootstrap` later.

### 6.3 Templates

`templates/project-specific-agents/<name>.md.tmpl` per supported agent. Adapted via placeholder substitution to the specific project (entities, modules, contracts).

---

## 7. The 4 communication mechanisms

The only legitimate ways agents share information. Free-form chat between agents is not used.

### 7.1 Handoff

After every task, the executing agent writes a handoff to `<state-backend>/agentops/handoffs/YYYY-MM-DD-<agent>-<task>.md`.

Frontmatter:
```yaml
---
agent: backend-agent
task: implement-wallet-record
date: 2026-04-29
status: completed  # completed | blocked | escalated
---
```

Required sections: What was done, Files changed, Contracts used, Risks found, Tests added, Next agent needs.

### 7.2 Contract Change Request (CCR)

The only legitimate way to modify a frozen shared contract. Created at `<state-backend>/agentops/ccr/CCR-NNN-<title>.md`.

Frontmatter:
```yaml
---
ccr_id: CCR-007
proposer: backend-agent
target_contract: '[[contract-wallet-events]]'
status: pending  # pending | approved | rejected | applied
date_proposed: 2026-04-29
date_resolved: null
---
```

Required sections: Current state, Proposed change, Reason, Affected modules, Migration plan, Domain Agent decision (filled by Domain Agent).

### 7.3 ADR (Architecture Decision Record)

For architectural decisions. Created at `<state-backend>/agentops/decisions/ADR-NNN-<title>.md`.

Required sections: Context, Decision, Reasoning, Alternatives rejected, Risks, Validation.

### 7.4 Integration Issue

When modules don't fit. Created at `<state-backend>/agentops/integration-issues/II-NNN-<title>.md`.

Required sections: Conflict description, Owner module A, Owner module B, Blocker for, Required fix, Resolution.

---

## 8. The 9 review levels

Cross-cutting axis. Every level produces an artifact. No review without evidence.

| # | Level | Phase | Type | Owner | Trigger | Output |
|---|---|---|---|---|---|---|
| 1 | Design review | plan-slice | Architecture review | Domain + Security | Before plan approval | Approval comment in plan doc |
| 2 | Plan review | plan-slice | Decomposition review | CTO Integration | Before backlog approval | Approval; scope check pass |
| 3 | Per-task review | execute-slice | Spec compliance + code quality (two-stage) | Owner agent + peer | After each task | Review entry attached to handoff |
| 4 | Per-slice integration | execute-slice | Integration | QA + adapters | Before merge | Integration report; updates `integration_status.md` |
| 5 | Pre-merge domain drift | merge | Drift check | Domain | Before each merge | Drift report; blocks if 🔴 |
| 6 | Pre-merge security | merge | Security check | Security Architect | Before each merge | Security report; blocks if 🔴 |
| 7 | Weekly CTO audit | weekly | 7-question audit | CTO Integration | Weekly cron or manual | `<state-backend>/agentops/reviews/YYYY-WW-cto-review.md` |
| 8 | Pre-release readiness | pre-release | Readiness gate | Release Manager + QA | Before release | Readiness report; release blocked if not READY |
| 9 | Audit / challenge | on-demand | Devil's advocate | Audit-Challenge | On request or after major change | Challenge doc |

---

## 9. The 5 operating rhythms

Explicit workflows, not vague rituals. Each has a sub-skill or skill that owns it.

### 9.1 Execution rhythm

Owner: `execute-slice` skill. Frequency: many times per day, per task.

```
1. Agent reads agent_backlog.md
2. Agent reads current contracts and state
3. Agent performs task
4. Agent writes handoff
5. Agent updates open_questions.md if new question raised
6. Agent updates risk_register.md if new risk discovered
7. Agent updates decision_log.md if decision made (or creates ADR)
8. Owner agent reviews handoff (Review level 3)
9. State files updated atomically
10. Verification evidence attached to handoff
```

### 9.2 Weekly rhythm

Owner: `cto-review` skill. Frequency: weekly cron or manual.

```
1. CTO Agent gathers handoffs over period
2. Documentation Agent updates indexes / state summaries
3. Domain Agent runs contract drift check
4. Security Agent updates risk register
5. QA Agent updates coverage
6. Release Manager updates readiness
7. CTO runs 7-question audit (see §3.5.1)
8. Resolutions go to decision_log.md (or new ADRs)
9. Review doc created at <state-backend>/agentops/reviews/YYYY-WW-cto-review.md
```

### 9.3 Pre-integration rhythm

Owner: `pre-integration-check` skill. Frequency: before every merge.

```
1. Check shared contracts (no breakage)
2. Check no duplicated local enums
3. Check API/event compatibility
4. Check security invariants
5. Run integration tests
6. Update integration_status.md
7. Block merge if any critical issue exists
```

### 9.4 Pre-release rhythm

Owner: `release-readiness` skill. Frequency: before each release.

```
1. Check planned scope (no creep)
2. Check open blockers (zero or accepted)
3. Check risks (no unmitigated 🔴)
4. Check tests (no regressions; coverage met)
5. Check docs (changelog, migration notes, API docs current)
6. Check migration notes (DB, contract, breaking changes)
7. Check rollback plan (documented and tested)
8. Check known limitations (documented)
9. Produce release readiness report
```

### 9.5 Audit / challenge rhythm

Owner: `audit-challenge` skill. Frequency: on request or after major change.

Devil's advocate pass. Output: challenge doc with surfaced assumptions, contradictions, alternative paths considered.

---

## 10. Mode settings

Configured via `.claude/settings.local.json` per project. Defaults shown.

```json
{
  "agentops": {
    "architecture_canon_mode": "strict",
    "schema_evolve_mode": "gated",
    "subagent_dispatch_mode": "subagent",
    "automation_level": "full",
    "ci_platform": "github-actions",
    "obsidian": false,
    "language": "en"
  }
}
```

| Setting | Values | Default | Effect |
|---|---|---|---|
| `architecture_canon_mode` | strict / lenient / off | strict | strict: violations = 🔴 block commit and `execute-slice`. lenient: violations = 🟡 warnings. off: canon as docs only. |
| `schema_evolve_mode` | gated / auto | gated | gated: every new entity type requires user confirmation. auto: created automatically, rollback via `git revert`. |
| `subagent_dispatch_mode` | subagent / inline | subagent | subagent: fresh subagent per task in `execute-slice`. inline: all tasks in one session (for non-subagent platforms). |
| `automation_level` | full / hooks-only / minimal | full | full: session hooks + git hooks + GitHub Actions. hooks-only: session and git hooks. minimal: no hooks. |

---

## 11. Hooks

| Hook | When | Action |
|---|---|---|
| session-start (optional) | Session start | Auto-invoke `/agentops:onboard` |
| pre-tool-use | Before code-write tools | `dependency-rule-check` (if strict mode) |
| post-tool-use | After state file write | `state-files-update` triggered re-aggregation |
| session-end | Session end | Surface state changes; suggest next actions |
| pre-commit (git) | Before git commit | `dependency-rule-check`, `pre-integration-check` (if applicable) |
| CI: `agentops-lint.yml` | On push / PR | Full canon compliance check |
| CI: `agentops-review.yml` | Weekly cron | `/agentops:cto-review` automated run |

---

## 12. Detection of optional layers

AgentOps probes for Alpha-Wiki and Superpowers at the start of every Tier 1 skill invocation. Detection is cached for the session.

Mechanism:
- Plugin presence marker via `~/.claude/plugins/` enumeration.
- Skill availability check via Skill tool.
- Backend choice logged in `decision_log.md`.

Detection results affect:
- State backend root (Alpha-Wiki present → `wiki/agentops/`; absent → `docs/agentops/`)
- Discipline backend (Superpowers present → instruct invocation; absent → native fallback)
- Agent registration mechanism (Alpha-Wiki present → use `spawn-agent` as helper per ADR-006)
- Wiki integration (Alpha-Wiki present → `ingest`, `lint`, `contracts-check`, `claims-check` available)

---

## 13. What is NOT in AgentOps

For clarity:

- No wiki page lifecycle, frontmatter schema, schema evolution mechanics, structural lint, graph engine. Owned by Alpha-Wiki.
- No `wiki/state/`, `wiki/decisions/`, `wiki/handoffs/` at root. AgentOps writes only under `wiki/agentops/` (per ADR-004).
- No team-role logic in `spawn-agent`. AgentOps owns team roles; `spawn-agent` is a registration helper only (per ADR-006).
- No fork or copy of Superpowers (per ADR-002).
- No programmatic API call to Superpowers (per ADR-002).
- No vector store or embeddings (per ADR-003).
- No umbrella marketplace (per ADR-005, deferred to Phase 5).
