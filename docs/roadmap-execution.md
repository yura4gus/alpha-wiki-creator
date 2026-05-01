# Roadmap — Execution Plan

> Pure execution. Phases, tasks, acceptance criteria, gates. No reasoning. Reasoning lives in `design/`.
>
> Reference: `design/00-architecture.md` for architecture, `design/01-alpha-wiki.md` / `design/02-agentops.md` / `design/03-superpowers-adapter.md` / `design/04-state-backend-contract.md` for specs, `design/adr/ADR-001..006` for decisions.

---

## Phase status legend

| Status | Meaning |
|---|---|
| `done` | Completed, evidence recorded |
| `in-progress` | Started, not finished |
| `ready` | Dependencies met, can start |
| `blocked` | Dependency open |
| `deferred` | Out of current scope, scheduled later |

---

## Phase 0 — Close audit

Goal: zero P0 unknowns before Phase 1 starts.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends | Status |
|---|---|---|---|---|---|---|---|
| T0.1 | Inspect `alpha-wiki-creator` repo: enumerate `skills/`, `commands/`, `tools/`, `tests/`, `scripts/`, `references/`, `.claude-plugin/`, `.github/workflows/`. Produce verified inventory document. | `audit-verified-inventory.md` | Verified inventory recorded in `docs/audit-verified-inventory.md`. | User reviews verified inventory. | N/A (inspection only). | None | done |
| T0.2 | Verify whether `/alpha-wiki:review` and `/alpha-wiki:rollup` are full skills, commands-only, CI-only, or planned-only. | `audit-verified-inventory.md` | Initial audit found CI-template-only old-namespace artifacts; Phase 1a P0 now backs both with skills, commands, and deterministic tools. | User reviews. | N/A. | T0.1 | done |
| T0.3 | Approve ADRs 001–006 (already drafted in `design/adr/`). | `design/adr/ADR-001..006.md` | Each ADR marked Status: Accepted by user. | User approval. | N/A. | None | done (drafted Etap 2) |
| T0.4 | Marketplace topology decision. | `design/adr/ADR-005-marketplace-topology-deferred.md` | Recorded as deferred to Phase 5. | None — closed by ADR. | N/A. | None | done |
| T0.5 | spawn-agent boundary lock. | `design/adr/ADR-006-spawn-agent-boundary.md` | Frozen pre-Phase 1a per ADR-006. | None — closed by ADR. | N/A. | None | done |
| T0.6 | Skill content audit: revisit all 10 backed Alpha-Wiki skills by name and body, strengthening operational logic, teaching behavior, graph discipline, Obsidian color semantics, and Karpathy LLM-Wiki principles before Phase 1a implementation work. | `skills/*/SKILL.md` | All 10 backed skill bodies rewritten as richer operational manuals with mission, boundaries, workflow, graph/color discipline, safety gates, and done criteria. | User reviews skill bodies. | Existing test suite remains green. | T0.1, T0.2 | done |
| T0.7 | Human-readable command and graph/status clarity pass: make slash command descriptions understandable, lock Obsidian graph colors to repo/service/module/feature/document/contract semantics, and require a cross-cutting Gap Check in status. | `commands/*.md`, `skills/status/SKILL.md`, `skills/render/SKILL.md`, `assets/obsidian/*`, `tools/status.py`, `README.md` | Commands retain stable machine names but expose human meanings; Obsidian colors match red repos/services, green modules/domains, blue features/flows, black docs, orange contracts; status output always includes `Gap Check`. | User reviews command wording and graph legend. | Unit tests cover status gap output and Obsidian color contract. | T0.6 | done |
| T0.8 | Codex/OpenAI adapter pass: add Codex install instructions, prefixed Codex skill installation, and Claude/Codex command mapping. | `README.md`, `docs/codex-adapter.md`, `scripts/install_codex.py`, `tests/unit/test_install_codex.py` | User can install Claude Code plugin or Codex skills from README; Codex skill names are prefixed as `$alpha-wiki-*`; installer is tested. | User reviews install UX. | Unit tests cover Codex skill transform/install. | T0.7 | done |
| T0.9 | Best-practices gap scan: identify operator and AI ergonomics still missing before Phase 1a. | `docs/best-practices-gap-analysis-2026-04-30.md` | Added actionable gap list covering doctor checks, prompt cards, pressure fixtures, provenance scoring, graph QA snapshots, context budgets, and platform compatibility. | User reviews prioritization. | N/A. | T0.8 | done |
| T0.10 | Karpathy LLM-Wiki compliance audit: verify simple markdown memory, `ingest/query/lint`, `index.md`/`log.md`, no embeddings, and fast context orientation through `context_brief.md`. | `docs/karpathy-llm-wiki-compliance-audit-2026-05-01.md` | Audit records pass/partial/gap status with repo evidence and Phase 1a follow-ups. | User reviews audit verdict. | Existing test suite remains green. | T0.9 | done |

Phase 0 gate: T0.1 through T0.10 closed. → Phase 1a starts.

---

## Phase 1a — Alpha-Wiki hardening (in-place)

Goal: 10 backed skills upgraded to deep operational manuals; 3 new skills added.

Repo: `yura4gus/alpha-wiki-creator` (in place, no rename).

### Phase 1a.1 — Skill audit pass on backed 10

Each task follows the same shape: build on the Phase 0 skill-content audit, bring SKILL.md to full 15-dimension standard from `design/00-architecture.md` §5.2, reformulate trigger description to trigger conditions only, and add pressure tests.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1a.1 | Skill audit on `init`. Add migration mode for existing repos. Add rollback plan. Enforce "first lint + first graph + first status" checklist. | `skills/init/SKILL.md`, `skills/init/references/*`, `tools/init_audit.py` (new) | All 15 dimensions documented; trigger description ≤2 sentences, conditions only; 5 pressure scenarios pass. | User skim of SKILL.md. | `tests/skills/test_init_pressure.py` (5 scenarios). | T0 closed |
| T1a.2 | Skill audit on `ingest`. Add claim extraction with provenance, contradiction detection against existing claims, risk extraction, stale-claim auto-flag. | `skills/ingest/SKILL.md`, `tools/ingest_pipeline.py` (new), `tools/classifier.py` (new), `tools/contradiction_detector.py` (new) | 15 dimensions; pipeline matches `01-alpha-wiki.md` §4.2; 7 pressure scenarios pass. | User skim. | `tests/skills/test_ingest_pressure.py` (7 scenarios: PDF, OpenAPI, transcript, ADR, contradicting claim, oversized, unparseable). | T1a.1 |
| T1a.3 | Skill audit on `query`. Add truth-status taxonomy in output (accepted / assumption / risk / open / stale). Add contradiction surfacing. Define citation policy (file path + line range). | `skills/query/SKILL.md`, `tools/wiki_search.py` (new) | 15 dimensions; output sections explicit; citation policy documented; 4 pressure scenarios pass. | User skim. | `tests/skills/test_query_pressure.py` (4 scenarios). | T1a.1 |
| T1a.4 | Skill audit on `lint`. Formalize severity model (🔴/🟡/🟢) as data. Add `--suggest` LLM-assisted mode. Verify all 15 checks from `01-alpha-wiki.md` §4.4 are present. | `skills/lint/SKILL.md`, `tools/lint.py`, `tools/lint_checks/*.py` | All 15 checks present; 5 modes work (`--fix`, `--suggest`, `--dry-run`, `--ci`, `--pre-commit`); 45 existing tests pass; new tests for added checks pass. | User skim. | Existing 45 + new per check (≥10 added). | T1a.1 |
| T1a.5 | Skill audit on `evolve`. Add migration plan generation for existing pages on schema change. Add optional generated child skill. | `skills/evolve/SKILL.md`, `tools/wiki_engine.py` (extend) | 15 dimensions; migration plan written when schema change affects existing entity type; 3 pressure scenarios pass. | User skim. | `tests/skills/test_evolve_pressure.py` (3 scenarios). | T1a.1 |
| T1a.6 | Skill audit on `status`. Add health score formula. Add suggested-next-actions logic. Add integration-status section (only when AgentOps detected). | `skills/status/SKILL.md`, `tools/status_report.py` (new) | 15 dimensions; output matches `01-alpha-wiki.md` §4.5; 4 pressure scenarios pass (empty, 1-page, 100-page, broken-links). | User skim. | `tests/skills/test_status_pressure.py` (4). | T1a.1, T1a.4 |
| T1a.7 | Skill audit on `spawn-agent`. Implement ADR-006 boundary: zero references to AgentOps team-role names; detect AgentOps presence informationally only. | `skills/spawn-agent/SKILL.md` | 15 dimensions; source contains zero AgentOps team-role references; standalone path and helper-path both pass. | User skim + grep check. | `tests/skills/test_spawn_agent_boundary.py` (2 scenarios: standalone, helper-mode with payload). | T1a.1 |
| T1a.8 | Skill audit on `render`. Add Mermaid output. Add static HTML export. | `skills/render/SKILL.md`, `tools/render_html.py` (new), `tools/render_mermaid.py` (new) | 15 dimensions; 4 modes work (`obsidian`, `html`, `mermaid`, `dot`); snapshot tests pass. | User skim. | `tests/skills/test_render_snapshots.py` (4 modes × sample wiki). | T1a.1 |

### Phase 1a.2 — New skills

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1a.9 | Implement `contracts-check` skill: contract page has service owner, consumers bidirectionally consistent, version bumps have migration notes. | `skills/contracts-check/SKILL.md`, `tools/contracts_check.py` (new) | 15 dimensions; 3 detection cases work (no consumer, version-bump-no-migration, overlapping definition). | User skim. | `tests/skills/test_contracts_check.py` (3). | T1a.4 |
| T1a.10 | Implement `claims-check` skill: detect contradicting claims, stale claims by frontmatter date, claims missing provenance. | `skills/claims-check/SKILL.md`, `tools/claims_check.py` (new) | 15 dimensions; 3 detection cases work. | User skim. | `tests/skills/test_claims_check.py` (3). | T1a.2 |
| T1a.11 | Implement `daily-maintenance` skill: idempotent bundle (lint --fix + context_brief rebuild + log append + stale surface). | `skills/daily-maintenance/SKILL.md` | 15 dimensions; idempotent (run twice → identical state on second run); failure non-destructive. | User skim. | `tests/skills/test_daily_maintenance_idempotency.py` (1). | T1a.4, T1a.6 |

### Phase 1a.3 — Contingent skills (resolve per T0.2)

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1a.12 | Resolve `review` status. If exists: harden to 15-dimension standard. If absent: write SKILL.md from scratch covering wiki-level review (stale, link rot, schema drift, gaps). | `skills/review/SKILL.md`, `commands/review.md`, `tools/review.py` | Backed minimal implementation exists; full 15-dimension hardening remains P1. Clearly distinguished from AgentOps `cto-review`. | User skim. | `tests/unit/test_review_rollup.py`. | T0.2 |
| T1a.13 | Resolve `rollup` status. Same treatment. | `skills/rollup/SKILL.md`, `commands/rollup.md`, `tools/rollup.py` | Backed minimal implementation exists; full 15-dimension hardening remains P1. Writes idempotent period rollup. | User skim. | `tests/unit/test_review_rollup.py`. | T0.2 |

### Phase 1a.4 — Release prep

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1a.14 | Update README with hardened skill list, new skills, removed ambiguities. | `README.md` | README accurate; all skills listed match repo. | User skim. | N/A. | T1a.1 – T1a.13 |
| T1a.15 | Update CHANGELOG. Bump semver minor. Tag release. | `CHANGELOG.md`, git tag | Tag pushed; release notes describe hardening + new skills. | User approval. | N/A. | T1a.14 |
| T1a.16 | Smoke test on a real project (Seldon-CRM raw materials). | N/A | `init` + `ingest` + `query` + `lint` + `status` end-to-end works on Seldon-CRM PRD + AUDIT_TASKS without errors. | User runs and confirms. | Manual run, output captured. | T1a.15 |

Phase 1a gate: all tests green; CI passes; smoke test on Seldon-CRM passes; semver bump tagged.

---

## Phase 1b — AgentOps MVP (new repo)

Goal: AgentOps installable as separate plugin; standalone (Markdown fallback) functional. Sequential after Phase 1a.

Repo: new (working name `agentops`, owner TBD before kickoff).

### Phase 1b.1 — Plugin scaffold

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.1 | Create new repo. Initialize plugin scaffold per `design/02-agentops.md` §2. | Whole `agentops/` repo | `claude plugins marketplace add <owner>/agentops && claude plugins install agentops` works. Plugin loads. | User runs plugin add. | N/A. | T1a closed |
| T1b.2 | Set up Python 3.12+ + uv. Mirror `pyproject.toml` style from alpha-wiki-creator. | `pyproject.toml`, `uv.lock` | `uv sync --dev` succeeds. | None. | N/A. | T1b.1 |
| T1b.3 | Set up CI (GitHub Actions) for lint + tests. | `.github/workflows/ci.yml` | CI green on empty test run. | None. | N/A. | T1b.2 |

### Phase 1b.2 — Tier 1 skill: `init-project`

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.4 | Implement `init-project` SKILL.md per `design/02-agentops.md` §3.1, all 10 operations. | `skills/_tier1/init-project/SKILL.md`, `skills/_tier1/init-project/references/*`, `skills/_tier1/init-project/scripts/*` | 15 dimensions; 10 ops enumerated; 4 gates implemented; 8 interview questions wired; resumability via `.claude/agentops-init-state.json`. | User skim. | `tests/skills/test_init_project_pressure.py` (6 scenarios per §3.1 tests row). | T1b.3 |
| T1b.5 | Implement `tools/state_init.py` for state file initialization. | `tools/state_init.py` | Initializes 7 living state files + 2 ADR + first plan template. | None. | `tests/tools/test_state_init.py`. | T1b.4 |
| T1b.6 | Implement `tools/classifier.py` for project-specific agent detection. | `tools/classifier.py` | Detects 13 signals from `design/02-agentops.md` §6.1 with confidence scoring. | None. | `tests/tools/test_classifier.py` (per signal). | T1b.4 |

### Phase 1b.3 — Tier 1 skills: remaining 4

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.7 | Implement `onboard` SKILL.md. | `skills/_tier1/onboard/SKILL.md` | 15 dimensions; ≤500-word summary on test project; 3 pressure scenarios pass. | User skim. | `tests/skills/test_onboard.py`. | T1b.4 |
| T1b.8 | Implement `plan-slice` SKILL.md with 3 gates and native brainstorm + decomposition fallback. | `skills/_tier1/plan-slice/SKILL.md` | 15 dimensions; native brainstorm works without Superpowers; 3 pressure scenarios pass. | User skim. | `tests/skills/test_plan_slice.py`. | T1b.4 |
| T1b.9 | Implement `execute-slice` SKILL.md with native discipline (TDD, two-stage review, verification-before-done embedded). | `skills/_tier1/execute-slice/SKILL.md` | 15 dimensions; runs end-to-end without Superpowers; 5 pressure scenarios pass. | User skim. | `tests/skills/test_execute_slice.py`. | T1b.8 |
| T1b.10 | Implement `cto-review` SKILL.md with 7-question audit. | `skills/_tier1/cto-review/SKILL.md` | 15 dimensions; produces review document at correct path; 3 pressure scenarios pass. | User skim. | `tests/skills/test_cto_review.py`. | T1b.4, T1b.7 |

### Phase 1b.4 — Tier 2 skills (P0 subset)

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.11 | Implement `canon-install` Tier 2 skill: generate 8 architecture canon docs (Clean + Hexagonal). | `skills/_tier2_internal/canon-install/SKILL.md`, `tools/canon_install.py`, `templates/architecture/*.md.tmpl` | 15 dimensions; 8 docs generated with project-specific placeholder substitution. | User skim. | `tests/skills/test_canon_install.py`. | T1b.4 |
| T1b.12 | Implement `domain-freeze` Tier 2 skill: 4 freeze docs + packages skeleton. | `skills/_tier2_internal/domain-freeze/SKILL.md`, `templates/domain/*.md.tmpl` | 15 dimensions; 4 docs generated; ADR-002 created. | User skim. | `tests/skills/test_domain_freeze.py`. | T1b.4 |
| T1b.13 | Implement `adr-write` Tier 2 skill: standardized ADR with 6 required sections. | `skills/_tier2_internal/adr-write/SKILL.md`, `templates/communication/adr.md.tmpl` | 15 dimensions; ADR template enforced. | User skim. | `tests/skills/test_adr_write.py`. | T1b.4 |
| T1b.14 | Implement `agent-handoff` Tier 2 skill. | `skills/_tier2_internal/agent-handoff/SKILL.md`, `templates/communication/handoff.md.tmpl` | 15 dimensions; handoff frontmatter + 6 sections enforced. | User skim. | `tests/skills/test_agent_handoff.py`. | T1b.9 |
| T1b.15 | Implement `state-files-update` Tier 2 skill: atomic update of 7 living state files. | `skills/_tier2_internal/state-files-update/SKILL.md` | 15 dimensions; atomic (all-or-nothing) update; concurrency-safe. | User skim. | `tests/skills/test_state_files_update.py`. | T1b.4 |
| T1b.16 | Implement `agent-skills-bootstrap` Tier 2 skill: 9 universal + N project-specific. Native path (no spawn-agent helper for now). | `skills/_tier2_internal/agent-skills-bootstrap/SKILL.md` | 15 dimensions; 9 universal agents written to `.claude/skills/agent-*/SKILL.md`; project-specific agents detected via `tools/classifier.py`. | User skim. | `tests/skills/test_agent_skills_bootstrap.py`. | T1b.6 |
| T1b.17 | Implement `wiki-backend-adapter` Tier 2 skill (initial: detection only, paths resolve to `docs/agentops/` always — full wiki integration in Phase 2). | `skills/_tier2_internal/wiki-backend-adapter/SKILL.md` | 15 dimensions; detection works; paths resolve correctly with no-Alpha-Wiki fallback only. | User skim. | `tests/skills/test_wiki_backend_adapter_detection.py`. | T1b.4 |

### Phase 1b.5 — Tier 2 skills (P1, native only)

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.18 | Implement `tdd-cycle` Tier 2 skill (native, RED-GREEN-REFACTOR). | `skills/_tier2_internal/tdd-cycle/SKILL.md` | 15 dimensions; deletes code written without test; enforces gate. | User skim. | `tests/skills/test_tdd_cycle.py`. | T1b.9 |
| T1b.19 | Implement `two-stage-review` Tier 2 skill (native). | `skills/_tier2_internal/two-stage-review/SKILL.md` | 15 dimensions; 2 passes; critical issues block. | User skim. | `tests/skills/test_two_stage_review.py`. | T1b.9 |
| T1b.20 | Implement `verification-before-done` Tier 2 skill (native). | `skills/_tier2_internal/verification-before-done/SKILL.md` | 15 dimensions; verification commands run; output attached to handoff. | User skim. | `tests/skills/test_verification_before_done.py`. | T1b.9 |
| T1b.21 | Implement `dependency-rule-check` Tier 2 skill. | `skills/_tier2_internal/dependency-rule-check/SKILL.md`, `tools/dependency_check.py` | 15 dimensions; detects Clean+Hexagonal violations; respects strict/lenient/off modes. | User skim. | `tests/skills/test_dependency_rule_check.py` (per violation type). | T1b.11 |
| T1b.22 | Implement `contract-change-request` Tier 2 skill. | `skills/_tier2_internal/contract-change-request/SKILL.md`, `templates/communication/ccr.md.tmpl` | 15 dimensions; CCR file created; Domain Agent dispatched. | User skim. | `tests/skills/test_contract_change_request.py`. | T1b.12 |
| T1b.23 | Implement `integration-issue` Tier 2 skill. | `skills/_tier2_internal/integration-issue/SKILL.md`, `templates/communication/integration-issue.md.tmpl` | 15 dimensions; II file created. | User skim. | `tests/skills/test_integration_issue.py`. | T1b.4 |
| T1b.24 | Implement `pre-integration-check` Tier 2 skill. | `skills/_tier2_internal/pre-integration-check/SKILL.md` | 15 dimensions; 7 checks per `02-agentops.md` §9.3; blocks merge if 🔴. | User skim. | `tests/skills/test_pre_integration_check.py`. | T1b.21, T1b.12 |

### Phase 1b.6 — Tier 2 skills (P2, deferred to end of 1b)

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.25 | Implement `release-readiness` Tier 2 skill: 9-step check. | `skills/_tier2_internal/release-readiness/SKILL.md` | 15 dimensions; readiness report generated. | User skim. | `tests/skills/test_release_readiness.py`. | T1b.10 |
| T1b.26 | Implement `audit-challenge` Tier 2 skill (devil's advocate). | `skills/_tier2_internal/audit-challenge/SKILL.md` | 15 dimensions; produces challenge doc. | User skim. | `tests/skills/test_audit_challenge.py`. | T1b.10 |
| T1b.27 | Implement `superpowers-adapter` Tier 2 skill (initial: detection only, no phase mapping yet — full mapping in Phase 3). | `skills/_tier2_internal/superpowers-adapter/SKILL.md` | 15 dimensions; detection works; logs result; no active mapping yet. | User skim. | `tests/skills/test_superpowers_adapter_detection.py`. | T1b.4 |

### Phase 1b.7 — Universal agents (9)

Each task: write the SKILL.md per `design/02-agentops.md` §5 with 15 dimensions and the role's specific bounded context, communication mechanisms, allowed tools.

| ID | Agent | File | Acceptance | Tests | Depends |
|---|---|---|---|---|---|
| T1b.28 | CTO Integration | `skills/agents/cto-integration/SKILL.md` | 15 dimensions; weekly 7-question audit responsibility documented. | `tests/agents/test_cto_integration.py`. | T1b.10 |
| T1b.29 | Product / Business Analyst | `skills/agents/product-business-analyst/SKILL.md` | 15 dimensions. | `tests/agents/test_product.py`. | T1b.4 |
| T1b.30 | Domain & Contracts | `skills/agents/domain-and-contracts/SKILL.md` | 15 dimensions; CCR gatekeeper logic. | `tests/agents/test_domain.py`. | T1b.22 |
| T1b.31 | Technical Analyst | `skills/agents/technical-analyst/SKILL.md` | 15 dimensions. | `tests/agents/test_tech_analyst.py`. | T1b.13 |
| T1b.32 | Security Architect | `skills/agents/security-architect/SKILL.md` | 15 dimensions; pre-merge security check (level 6). | `tests/agents/test_security.py`. | T1b.24 |
| T1b.33 | QA / Integration | `skills/agents/qa-integration/SKILL.md` | 15 dimensions; pre-slice integration review (level 4). | `tests/agents/test_qa.py`. | T1b.24 |
| T1b.34 | Documentation | `skills/agents/documentation/SKILL.md` | 15 dimensions. | `tests/agents/test_documentation.py`. | T1b.4 |
| T1b.35 | Release Manager | `skills/agents/release-manager/SKILL.md` | 15 dimensions; release readiness (level 8). | `tests/agents/test_release.py`. | T1b.25 |
| T1b.36 | Audit / Challenge | `skills/agents/audit-challenge/SKILL.md` | 15 dimensions. | `tests/agents/test_audit_challenge_agent.py`. | T1b.26 |

### Phase 1b.8 — Project-specific agent templates

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.37 | Write 13 project-specific agent templates per `design/02-agentops.md` §6.1. | `templates/project-specific-agents/*.md.tmpl` (13 files) | All 13 templates exist; placeholder substitution works. | User skim. | `tests/templates/test_project_specific_agents.py`. | T1b.6 |

### Phase 1b.9 — Tools

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.38 | Implement `tools/canon_install.py`. | `tools/canon_install.py` | Generates 8 canon docs from templates. | None. | `tests/tools/test_canon_install.py`. | T1b.11 |
| T1b.39 | Implement `tools/dependency_check.py`. | `tools/dependency_check.py` | Detects Clean+Hexagonal violations on test fixtures. | None. | `tests/tools/test_dependency_check.py`. | T1b.21 |
| T1b.40 | Implement `tools/contract_check.py`. | `tools/contract_check.py` | Native AgentOps contract check (used when Alpha-Wiki absent). | None. | `tests/tools/test_contract_check.py`. | T1b.22 |
| T1b.41 | Implement `tools/audit_aggregator.py`. | `tools/audit_aggregator.py` | Aggregates handoffs over period for `cto-review`. | None. | `tests/tools/test_audit_aggregator.py`. | T1b.10 |

### Phase 1b.10 — Templates

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.42 | Write 7 living state file templates. | `templates/state/*.md.tmpl` (7 files) | Template syntax valid; placeholder substitution works. | User skim. | N/A. | T1b.5 |
| T1b.43 | Write 4 communication templates (handoff, ccr, adr, integration-issue). | `templates/communication/*.md.tmpl` (4 files) | Frontmatter + sections per `02-agentops.md` §7. | User skim. | N/A. | T1b.13, T1b.14, T1b.22, T1b.23 |
| T1b.44 | Write 8 architecture canon templates. | `templates/architecture/*.md.tmpl` (8 files) | Project-placeholder substitution; reflects Clean+Hexagonal docs from `_references.md`. | User skim. | N/A. | T1b.11 |
| T1b.45 | Write 4 domain freeze templates. | `templates/domain/*.md.tmpl` (4 files) | Templates per `02-agentops.md` §3.1.1 Op 8. | User skim. | N/A. | T1b.12 |
| T1b.46 | Write frontmatter schemas for 10 entity types. | `templates/frontmatter/*.yaml` (10 files) | Schemas valid YAML; each entity type covered. | User skim. | N/A. | T1b.4 |

### Phase 1b.11 — References

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.47 | Write `references/operating-model.md`. | `references/operating-model.md` | Full operating model from `design/02-agentops.md` §§3–9. | User skim. | N/A. | All Phase 1b done |
| T1b.48 | Write `references/communication-protocol.md`. | `references/communication-protocol.md` | Detailed 4 mechanisms with examples. | User skim. | N/A. | T1b.43 |
| T1b.49 | Write `references/architecture-canon.md`. | `references/architecture-canon.md` | Clean+Hexagonal patterns, dependency matrix, anti-patterns. | User skim. | N/A. | T1b.44 |
| T1b.50 | Write `references/classifier-taxonomy.md`. | `references/classifier-taxonomy.md` | 11 raw artifact categories + detection signals. | User skim. | N/A. | T1b.6 |
| T1b.51 | Write `references/review-levels.md` and `references/rhythms.md`. | `references/review-levels.md`, `references/rhythms.md` | 9 review levels + 5 rhythms documented. | User skim. | N/A. | None |

### Phase 1b.12 — Smoke test and release

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T1b.52 | Smoke test on Seldon-CRM: standalone AgentOps `init-project` end-to-end without Alpha-Wiki. | N/A | All 10 operations complete; 9 universal agents installed; project-specific agents detected; first slice plan generated; handoff report output. | User runs and confirms. | Manual run, output captured. | All Phase 1b skills done |
| T1b.53 | Write README, INSTALL, CHANGELOG. Tag v0.1.0. | `README.md`, `INSTALL.md`, `CHANGELOG.md` | README + INSTALL accurate; v0.1.0 tagged. | User approval. | N/A. | T1b.52 |

Phase 1b gate: AgentOps standalone init runs end-to-end on a clean project without Alpha-Wiki, without Superpowers; v0.1.0 tagged.

---

## Phase 2 — Alpha-Wiki ↔ AgentOps integration

Goal: AgentOps uses Alpha-Wiki as backend cleanly when both installed.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T2.1 | Extend `wiki-backend-adapter` with full detection + path routing to `wiki/agentops/`. | `agentops/skills/_tier2_internal/wiki-backend-adapter/SKILL.md` | Detection + routing per `design/04-state-backend-contract.md` §4. | User skim. | `tests/integration/test_wiki_backend_routing.py`. | T1b done |
| T2.2 | Implement integration: AgentOps `init-project` Op 3 delegates to Alpha-Wiki `ingest`. | `agentops/skills/_tier1/init-project/SKILL.md` (update) | When Alpha-Wiki present, raw materials ingested via `alpha-wiki:ingest`. | User skim. | `tests/integration/test_init_with_alpha_wiki.py`. | T2.1 |
| T2.3 | Implement integration: AgentOps `agent-skills-bootstrap` uses Alpha-Wiki `spawn-agent` as helper (per ADR-006). | `agentops/skills/_tier2_internal/agent-skills-bootstrap/SKILL.md` (update) | When Alpha-Wiki present, agent registration goes through `spawn-agent` with team-role payload. | User skim. | `tests/integration/test_spawn_agent_helper.py`. | T2.1, T1a.7 |
| T2.4 | Implement integration: AgentOps `cto-review` invokes Alpha-Wiki `contracts-check` and `claims-check`. | `agentops/skills/_tier1/cto-review/SKILL.md` (update) | When Alpha-Wiki present, both checks run; results in review doc. | User skim. | `tests/integration/test_cto_review_with_alpha_wiki.py`. | T2.1, T1a.9, T1a.10 |
| T2.5 | Implement integration: AgentOps `onboard` reads `wiki/graph/context_brief.md` directly when Alpha-Wiki present. | `agentops/skills/_tier1/onboard/SKILL.md` (update) | Context loaded from Alpha-Wiki when present. | User skim. | `tests/integration/test_onboard_with_alpha_wiki.py`. | T2.1 |
| T2.6 | Implement migration helper: `agentops:migrate-to-wiki`. | `agentops/skills/_tier2_internal/wiki-backend-adapter/migrate.py` | Moves `docs/agentops/` to `wiki/agentops/` cleanly. | User runs and confirms. | `tests/integration/test_migration_to_wiki.py`. | T2.1 |
| T2.7 | Update Alpha-Wiki `status` to surface AgentOps integration status section when AgentOps detected. | `alpha-wiki-creator/skills/status/SKILL.md` (update) | Section appears when AgentOps installed; informational only. | User skim. | `tests/skills/test_status_with_agentops.py`. | T2.1, T1a.6 |
| T2.8 | Integration test suite covering all 6 plugin combinations from `design/00-architecture.md` §3.1. | `agentops/tests/integration/test_combinations.py` | All 6 combinations verified. | User reviews. | The test itself. | T2.1 – T2.7 |
| T2.9 | Smoke test on Seldon-CRM: AgentOps + Alpha-Wiki combined mode end-to-end. | N/A | Combined mode init produces correct paths, integration capabilities work. | User runs and confirms. | Manual run, output captured. | T2.8 |

Phase 2 gate: T2.8 + T2.9 pass; both plugins versioned with combined-mode notes in CHANGELOG.

---

## Phase 3 — Superpowers integration

Goal: AgentOps uses Superpowers when present via process-level adapter.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T3.1 | Extend `superpowers-adapter` with full detection per `design/03-superpowers-adapter.md` §3. | `agentops/skills/_tier2_internal/superpowers-adapter/SKILL.md` | Detection works for plugin marker + skill availability. | User skim. | `tests/integration/test_superpowers_detection.py`. | T1b done |
| T3.2 | Implement phase mapping for `plan-slice`: instruct invocation of `superpowers:brainstorming` + `superpowers:writing-plans`. | `agentops/skills/_tier1/plan-slice/SKILL.md` (update) | When Superpowers present, instructions emitted; native fallback when absent. | User skim. | `tests/integration/test_plan_slice_with_superpowers.py`. | T3.1 |
| T3.3 | Implement phase mapping for `execute-slice`: instruct invocation of `superpowers:subagent-driven-development` + `superpowers:test-driven-development` + `superpowers:requesting-code-review`. | `agentops/skills/_tier1/execute-slice/SKILL.md` (update) | When Superpowers present, instructions emitted at each phase. | User skim. | `tests/integration/test_execute_slice_with_superpowers.py`. | T3.1 |
| T3.4 | Implement phase mapping for `pre-integration-check`: instruct invocation of `superpowers:verification-before-completion` alongside AgentOps contract checks. | `agentops/skills/_tier2_internal/pre-integration-check/SKILL.md` (update) | When Superpowers present, both run. | User skim. | `tests/integration/test_pre_integration_with_superpowers.py`. | T3.1 |
| T3.5 | Implement backend-choice logging to `decision_log.md`. | `agentops/tools/_logging.py` | Every Tier 1 invocation logs backend choice. | None. | `tests/tools/test_backend_logging.py`. | T3.1 |
| T3.6 | Verify hard guarantees: no programmatic API call, no override of project rules, no override of Alpha-Wiki schema. | `agentops/tests/integration/test_superpowers_guarantees.py` | All 5 guarantees from `03-superpowers-adapter.md` §7 enforced. | User reviews. | The test itself. | T3.1 – T3.5 |
| T3.7 | Smoke test on Seldon-CRM: full mode (AgentOps + Alpha-Wiki + Superpowers) end-to-end. | N/A | Full mode produces backend-choice logs; Superpowers used at correct phases. | User runs and confirms. | Manual run, output captured. | T3.6 |

Phase 3 gate: T3.6 + T3.7 pass; AgentOps works identically with and without Superpowers, just slower/less polished without.

---

## Phase 4 — Automation and CI

Goal: All hooks and CI workflows reliable.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T4.1 | Implement `init-project` hooks installation: session-start, pre-tool-use, post-tool-use, session-end. | `agentops/templates/hooks/*.sh` | Hooks installed when `automation_level=full`; functional. | User skim. | `tests/integration/test_hooks_installed.py`. | T2 done |
| T4.2 | Implement pre-commit hook chain: alpha-wiki lint + agentops dependency-rule-check + pre-integration-check. | `agentops/templates/hooks/pre-commit.sh` | Chain runs; blocks 🔴; respects mode settings. | User runs commit. | `tests/integration/test_pre_commit_chain.py`. | T4.1 |
| T4.3 | Implement GitHub Actions workflow: `agentops-lint.yml` (on push/PR). | `agentops/templates/workflows/agentops-lint.yml` | Lint runs in CI; fails build on 🔴 in strict mode. | User reviews CI run. | The workflow itself. | T4.2 |
| T4.4 | Implement GitHub Actions workflow: `agentops-review.yml` (weekly cron). | `agentops/templates/workflows/agentops-review.yml` | Weekly cron triggers `cto-review`; result posted as issue. | User reviews CI run. | The workflow itself. | T4.3 |
| T4.5 | Implement Alpha-Wiki CI workflows hardening: `wiki-lint.yml`, `wiki-review.yml`, `wiki-rollup.yml`. | `alpha-wiki-creator/.github/workflows/*` | Workflows match Phase 1a hardened skills. | User reviews CI run. | Workflows themselves. | T1a done, T1a.12, T1a.13 |
| T4.6 | Health report generation skill / cron. | `agentops/skills/_tier2_internal/release-readiness/SKILL.md` (extend) or new | Report generated on demand and weekly; published to `<state-backend>/agentops/state/health-report.md`. | User skim. | `tests/integration/test_health_report.py`. | T4.4 |
| T4.7 | Mock-project test: full automation chain runs green on a synthetic project. | `agentops/tests/integration/test_automation_e2e.py` | All hooks + CI green. | User reviews. | The test itself. | T4.1 – T4.6 |

Phase 4 gate: T4.7 passes; documentation describes automation in detail.

---

## Phase 5 — Packaging and marketplace

Goal: Distributable plugins; users can install and follow quickstart.

| ID | Objective | Files | Acceptance | Gate | Tests | Depends |
|---|---|---|---|---|---|---|
| T5.1 | Finalize `plugin.json` for Alpha-Wiki (existing — verify Phase 1a additions reflected). | `alpha-wiki-creator/.claude-plugin/plugin.json` | All hardened + new skills listed; version current. | User skim. | N/A. | T1a done |
| T5.2 | Finalize `plugin.json` for AgentOps. | `agentops/.claude-plugin/plugin.json` | All Tier 1 + Tier 2 + agent skills listed; version 1.0.0. | User skim. | N/A. | T3 done, T4 done |
| T5.3 | Decide marketplace topology (revisit ADR-005). | `design/adr/ADR-005-marketplace-topology-deferred.md` (update or supersede) | Decision recorded with criteria evaluated. | User approval. | N/A. | T5.1, T5.2 |
| T5.4 | If umbrella decided: create marketplace repo and manifest. | `<umbrella-repo>/` | Marketplace lists both plugins; users install via single marketplace add. | User runs full install flow. | `tests/integration/test_marketplace_install.py`. | T5.3 (only if Yes) |
| T5.5 | Write INSTALL docs per platform (Claude Code primary; Codex / Gemini CLI compatibility notes). | `agentops/INSTALL.md`, `alpha-wiki-creator/INSTALL.md` (update) | Per-platform install instructions; known limitations documented. | User skim. | N/A. | T5.2 |
| T5.6 | Write compatibility matrix doc: which AgentOps capabilities work on which platforms. | `agentops/docs/compatibility.md` | Matrix accurate per release. | User skim. | N/A. | T5.5 |
| T5.7 | Write migration guide for existing alpha-wiki-creator users. | `alpha-wiki-creator/docs/migration-from-v0.x.md` | Guide covers any breaking changes from Phase 1a. | User skim. | N/A. | T1a.15 |
| T5.8 | Write examples directory with at least 3 example projects demonstrating different combinations. | `agentops/examples/`, `alpha-wiki-creator/examples/` | Examples cover: Alpha-Wiki only, AgentOps only, both combined. | User runs each example. | Manual run. | T5.6 |
| T5.9 | Versioning policy + release notes. | `agentops/CHANGELOG.md`, `alpha-wiki-creator/CHANGELOG.md` (update) | Semver discipline documented; release notes complete for v1.0.0. | User approval. | N/A. | T5.8 |
| T5.10 | Public release: tag v1.0.0 for AgentOps; tag v1.x.0 for Alpha-Wiki. | Tags + release notes | Both plugins installable from tagged release. | User runs install on a fresh machine. | Manual install. | T5.9 |

Phase 5 gate: External user installs from public release, follows quickstart, succeeds.

---

## Phase 6 — Advanced (deferred items)

Goal: Add only after MVP proves stable in real usage.

Items below are placeholders — each becomes a full Phase 6.x task list when prioritized.

| ID | Item | Triggered by |
|---|---|---|
| P6.A | Claim confidence levels (high / medium / low + provenance grade) | Real usage shows ambiguity in claim status |
| P6.B | Source confidence (primary / secondary / tertiary) | Real usage shows source-quality conflicts |
| P6.C | Supersession model (claim formally supersedes another) | Real usage shows claim evolution patterns |
| P6.D | Contradiction graph | Real usage shows persistent unresolved contradictions |
| P6.E | Multi-project memory | User has multiple `<framework>` projects and wants cross-project recall |
| P6.F | Static web UI | Obsidian + GitHub web view insufficient for some users |
| P6.G | Richer Obsidian graph customization | User feedback on graph view |
| P6.H | Repo import skill (`import-github-repo`) | Use case validated |
| P6.I | Transcript import structured pipeline | Use case validated |
| P6.J | Structured research agents | OmegaWiki-like research workflows requested |
| P6.K | BM25 backend | File search proves insufficient at scale |
| P6.L | Vector / embedding backend | BM25 proves insufficient at scale (very high bar; revisit ADR-003) |
| P6.M | Cross-project agent memory | Use case validated |
| P6.N | Cross-platform tool name mapping (Read → read_file etc.) for Codex / Gemini | User demand |

Phase 6 has no fixed gate. Each item is independently triaged based on real-usage signals and prioritized into a future phase.

---

## Cross-cutting acceptance criteria

These apply to **every** task across all phases. A task is not complete unless these hold:

1. SKILL.md (if applicable) follows the 15-dimension operating-manual standard from `design/00-architecture.md` §5.2.
2. Skill description is trigger conditions only, not workflow summary.
3. Tests written and passing (pressure scenarios, not gameshow quizzes).
4. No "done" claim without verification evidence (command output, test pass, explicit user approval).
5. No deterministic work uses LLM where pure Python would suffice.
6. No hidden coupling: layer ownership respected per `design/00-architecture.md` §2.
7. No writes outside the layer's namespace (Alpha-Wiki: `wiki/`; AgentOps: `<state-backend>/agentops/`).
8. Backend choice logged to `decision_log.md` for any conditional behavior.
9. Pressure scenarios cover the failure modes documented in the spec.
10. Documentation updated alongside code; no "docs later".

A task that passes acceptance but violates a cross-cutting criterion is reopened.

---

## What is not in this document

- Reasoning / rationale → `design/`
- Architecture diagrams → `design/00-architecture.md`
- Spec details (15 dimensions per skill) → `design/01..04-*.md`
- Decisions and alternatives → `design/adr/ADR-001..006`
- Pattern extraction (Karpathy / OmegaWiki / Superpowers) → `design/_references.md`
- Boundary discussions → all closed in design + ADRs
- Open questions about scope → escalate before next gate

This document is execution. Reasoning belongs upstream.
