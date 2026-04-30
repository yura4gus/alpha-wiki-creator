# 00 — Architecture

> Foundation document. Defines the three-layer ecosystem, ownership boundaries, integration model, and plugin topology. All other design documents reference this one.

---

## 1. The three layers

The ecosystem consists of three independently-installable, independently-useful layers.

| Layer | Product | Purpose |
|---|---|---|
| **Memory / Knowledge** | Alpha-Wiki | Persistent project memory. Raw sources → maintained wiki → schema. Markdown-first, no embeddings, no vector store. |
| **Agent Operating Model** | AgentOps | Disciplined agent team execution. Roles, communication protocol, planning, handoffs, review, release. |
| **Execution Discipline** | Superpowers | Optional. Brainstorming, TDD, subagent-driven development, code review, verification-before-done. |

Each layer has a single owner, a single ownership scope, and ships as a separate Claude Code plugin.

---

## 2. Ownership boundaries

### 2.1 Alpha-Wiki owns

- Three-layer mutability (raw / wiki / schema)
- Wiki page lifecycle: create, update, migrate, deprecate
- Frontmatter schema and entity types
- Schema evolution mechanics
- Cross-references and bidirectional link enforcement
- Wiki structural lint (broken links, orphans, missing frontmatter, stale)
- Auto-generated graph artifacts: `edges.jsonl`, `context_brief.md`, `open_questions.md`
- Obsidian and static HTML rendering
- Wiki-scoped queries
- The `wiki/` namespace at the root of the project

### 2.2 Alpha-Wiki does not own

- Agent team roles or hierarchy
- Process rhythms (execution / weekly / pre-integration / pre-release)
- Architectural canon (Clean / Hexagonal) — recorded *in* the wiki, but enforcement and templates belong to AgentOps
- Domain Freeze ceremony — recorded *in* the wiki, owned by AgentOps
- Code review, TDD, contract change requests, integration issues — all AgentOps
- TDD / subagent dispatch — Superpowers when present, AgentOps native fallback otherwise

### 2.3 AgentOps owns

- Agent team definition: 9 universal roles + N project-specific roles
- 4 communication mechanisms: Handoff / Contract Change Request / ADR / Integration Issue
- Process rhythms: execution, weekly, pre-integration, pre-release, audit/challenge
- 9 review levels
- Architecture canon templates (Clean + Hexagonal)
- Domain Freeze ceremony
- 5 user-facing skills (Tier 1)
- 17 internal sub-skills (Tier 2)
- State backend abstraction: routes to `wiki/agentops/` when Alpha-Wiki present, else to `docs/agentops/`
- The `agentops/` subnamespace under the chosen state backend root

### 2.4 AgentOps does not own

- Wiki internals — delegated to Alpha-Wiki when present
- Wiki-level operations (ingest, classify, evolve, lint, render) — delegated to Alpha-Wiki when present
- TDD / subagent dispatch / brainstorm enforcement — delegated to Superpowers when present, native fallback otherwise
- Generic editor or IDE concerns

### 2.5 Superpowers owns (when installed)

- Brainstorming discipline
- Writing-plans discipline (file structure, scope check, task decomposition)
- Subagent-driven-development
- Test-driven-development (RED-GREEN-REFACTOR enforcement)
- Code review (`requesting-code-review`)
- Verification-before-completion
- Worktree workflow

### 2.6 Hard boundary constraints

- Alpha-Wiki must run alone. No imports of AgentOps. No imports of Superpowers.
- AgentOps must run alone. Markdown fallback state under `docs/agentops/`. Optional detection of Alpha-Wiki and Superpowers.
- Superpowers integration is optional and never mandatory. AgentOps must not fork Superpowers, copy Superpowers wholesale, or call Superpowers programmatically. Process-level adapter only.
- No layer overrides project `CLAUDE.md`, `AGENTS.md`, project contracts, or user instructions.

---

## 3. Integration model

```
                   ┌────────────────────────────────────────┐
                   │           Target Project               │
                   └────────────────────────────────────────┘
                        ▲              ▲              ▲
                        │              │              │
              ┌─────────┴──┐  ┌────────┴─────┐  ┌─────┴──────┐
              │ Alpha-Wiki │  │   AgentOps   │  │Superpowers │
              │ (optional) │  │  (optional)  │  │ (optional) │
              └────────────┘  └──────┬───────┘  └────────────┘
                       ▲             │ optional   ▲
                       │             │ adapter    │
                       │             ├────────────┘
                       │ optional    │
                       │ adapter     │
                       └─────────────┘
```

### 3.1 Plugin combination matrix

| Plugins present | Behavior |
|---|---|
| Alpha-Wiki only | Wiki memory; no agent execution layer |
| AgentOps only | Agent team with Markdown state fallback in `docs/agentops/` |
| Alpha-Wiki + AgentOps | AgentOps stores state under `wiki/agentops/`, consumes `wiki/graph/context_brief.md`, registers project-specific agents into wiki via Alpha-Wiki `spawn-agent` skill |
| AgentOps + Superpowers | AgentOps instructs the agent to use Superpowers skills for planning / TDD / review; native fallback otherwise |
| Alpha-Wiki + AgentOps + Superpowers | Full mode; all three integrate via process-level adapters |
| Alpha-Wiki + Superpowers (no AgentOps) | Wiki memory + skill-quality discipline; no agent team |

### 3.2 Detection mechanism

AgentOps detects optional layers via plugin presence markers (Claude Code plugin registry, marker files in `~/.claude/plugins/`, or skill availability checks). The detected combination is logged in `decision_log.md` (or `docs/agentops/decisions/` fallback) at every `init-project` and `cto-review`.

Detection is one-way: AgentOps detects Alpha-Wiki and Superpowers. Alpha-Wiki and Superpowers do not detect AgentOps.

### 3.3 Adapter contracts (summary)

Two adapters, both inside AgentOps. Detailed specs in companion documents.

- **wiki-backend-adapter** (`02-agentops.md`, `04-state-backend-contract.md`): routes state operations to Alpha-Wiki paths or Markdown fallback paths.
- **superpowers-adapter** (`03-superpowers-adapter.md`): instructs the agent to invoke `superpowers:*` skills when present; never calls programmatically; embeds native fallback discipline.

---

## 4. Plugin topology

### 4.1 Phase 1 stance

Two independent plugins, two independent repositories. No umbrella marketplace until Phase 5.

```
yura4gus/alpha-wiki-creator/         # EXISTING — hardened in place in Phase 1a
└── (existing structure preserved)

<owner>/agentops/                    # NEW — created in Phase 1b
└── (full structure in 02-agentops.md §1)
```

Rationale: published plugins are not restructured before architecture is stable. Existing alpha-wiki-creator users are not disrupted.

### 4.2 Phase 5 stance

After both plugins reach stable releases, evaluate creating an umbrella marketplace listing both. Decision deferred to Phase 5. Until then, users install each plugin independently. See ADR-005.

### 4.3 Slash command namespaces

| Plugin | Namespace | Example |
|---|---|---|
| Alpha-Wiki | `/alpha-wiki:*` | `/alpha-wiki:ingest`, `/alpha-wiki:lint` |
| AgentOps | `/agentops:*` | `/agentops:init-project`, `/agentops:plan-slice` |
| Superpowers | `/superpowers:*` | `/superpowers:brainstorming` (external) |

Namespaces are non-overlapping by design.

---

## 5. Cross-cutting principles

These apply to every skill in every layer.

### 5.1 Skill description discipline

Skill `description` frontmatter contains trigger conditions only. It does not summarize workflow. The agent reads triggers to decide whether to invoke the skill, and reads the skill body to perform the work.

Bad: `Use for TDD - write test first, watch it fail, write minimal code, refactor`.
Good: `Use when implementing any feature or bugfix, before writing implementation code`.

### 5.2 Operating manual depth

Every skill defines, at minimum:

1. Purpose
2. When to trigger
3. When NOT to trigger
4. Inputs
5. Outputs
6. Files read
7. Files written
8. State updated
9. Review gates
10. Failure modes
11. Rollback behavior
12. Deterministic tools used
13. Tests (pressure scenarios, not gameshow quizzes)
14. Examples (positive and negative)
15. Integration with other skills

Skills lacking any of these dimensions are shallow and require hardening before release.

### 5.3 Evidence over claims

No skill claims completion without verification evidence. Every "done" status requires command output, test result, or explicit human approval recorded in the corresponding state file.

### 5.4 Deterministic tools where possible

Pure Python (or other deterministic) tools handle anything that can be expressed as a function. LLM is reserved for genuinely fuzzy work (synthesis, classification, drafting). The split is enforced by review gates: if a skill uses LLM where deterministic tooling would suffice, the review flags it.

### 5.5 Bidirectional state

Every change to project state is traceable, auditable, reversible. State files are append-only or git-tracked. Schema changes are gated and logged. Wiki mutations leave provenance in `wiki/log.md`.

### 5.6 No hidden coupling

No layer imports another at runtime. No layer assumes the presence of another. Every cross-layer interaction goes through an adapter that detects, routes, and falls back.

---

## 6. Key terms (glossary)

Used consistently across all design documents and skill bodies.

| Term | Definition |
|---|---|
| **State backend** | The directory tree where AgentOps writes operational state. Resolves to `wiki/agentops/` if Alpha-Wiki is installed, else `docs/agentops/`. See `04-state-backend-contract.md`. |
| **Domain Freeze** | A one-time AgentOps ceremony that locks naming, status models, event names, API names. Performed during `init-project`. After Domain Freeze, contract changes require a Contract Change Request. |
| **Handoff** | A markdown artifact created by an agent after completing a task. Records what was done, files changed, contracts used, risks found, tests added, what the next agent needs. |
| **CCR** | Contract Change Request. The only legitimate way to modify a frozen shared contract. Reviewed by Domain Agent. |
| **ADR** | Architecture Decision Record. Captures architectural decisions with context, decision, reasoning, alternatives rejected, risks, validation. |
| **Integration Issue** | A markdown artifact recording a module-to-module conflict that blocks integration. |
| **Vertical slice** | A minimal end-to-end implementation that touches every architectural layer involved. The first slice in a project is part of `init-project` output. |
| **Owner agent** | The agent role responsible for a given task, file path, or contract. Defined in `02_agent_hierarchy.md`. |
| **Subagent** | A fresh instance of the agent dispatched to execute a single task in isolation. Used by `execute-slice` when subagent platform support is available. |
| **Tier 1 skill** | A user-facing AgentOps skill. Five total: `init-project`, `onboard`, `plan-slice`, `execute-slice`, `cto-review`. |
| **Tier 2 skill** | An internal AgentOps sub-skill. Invoked by Tier 1 or by other Tier 2 skills. Never called directly by the user. |
| **Universal agent** | An AgentOps agent role installed on every project. 9 total: CTO Integration, Domain, Security Architect, QA, Documentation, Release Manager, Backend, Frontend, Audit-Challenge. |
| **Project-specific agent** | An AgentOps agent role created during `init-project` based on detection of project signals (e.g. Execution, Strategy, Venue Adapter for trading projects). |

---

## 7. Companion documents

This document is the foundation. Detailed specifications live in:

- `_references.md` — Karpathy, OmegaWiki, Superpowers patterns and the adopt/reject matrix
- `01-alpha-wiki.md` — Alpha-Wiki specification
- `02-agentops.md` — AgentOps specification (5 Tier 1, 17 Tier 2, 9 agents, operating model)
- `03-superpowers-adapter.md` — Superpowers process-level adapter specification
- `04-state-backend-contract.md` — State backend path schema, detection, read/write contract
- `adr/` — Architecture Decision Records (ADR-001 through ADR-006)

Roadmap and execution plan: `roadmap-execution.md` (separate document, not part of design).
