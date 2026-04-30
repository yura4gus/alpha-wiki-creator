# References — Karpathy, OmegaWiki, Superpowers

> Pattern extraction. What we adopted from each source, what we rejected, and why. Read once. Skill bodies cite this document by section number.

---

## 1. Karpathy LLM-Wiki

Source: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>

### 1.1 Adopted patterns (all six)

| Pattern | Where applied |
|---|---|
| Three layers: raw / wiki / schema | Alpha-Wiki core architecture |
| Three operations: ingest / query / lint | Alpha-Wiki Tier 1 skills |
| `index.md` as content-oriented YAML catalog | Alpha-Wiki templates |
| `log.md` as append-only chronology | Alpha-Wiki write contract |
| Wiki compounds week-over-week, not one-shot RAG | Foundational principle, no embeddings |
| No embeddings, no vector store | Locked in ADR-003 |

### 1.2 Rejected patterns

None. Karpathy's sketch is fully adopted at the conceptual level.

---

## 2. OmegaWiki

Source: <https://github.com/skyllwt/OmegaWiki>

### 2.1 Adopted patterns

| Pattern | Where applied |
|---|---|
| Typed entities with required frontmatter | Alpha-Wiki entity schema |
| Typed graph edges (extends/contradicts/supports/etc.) | Alpha-Wiki `wiki_engine.py` |
| Bidirectional link enforcement via lint | Alpha-Wiki `lint.py` |
| Schema evolution log | Alpha-Wiki `evolve` skill |
| Auto-generated `context_brief.md` for agent consumption | Alpha-Wiki session-start hook |
| Anti-repetition memory (failed ideas with `failure_reason`) | New: `wiki/lessons/` entity type, added during Phase 1a hardening |
| Research review / rebuttal workflows | Folded into wiki-level review (status TBD per inspection T0.2) |

### 2.2 Rejected patterns

| Pattern | Why rejected |
|---|---|
| Research-domain fixation (papers / claims / experiments as primary entities) | Alpha-Wiki must serve broader domains: software, product, personal KB. Research is one of five presets, not the canonical case. |
| Daily automation specific to research (e.g. arxiv ingest cron) | Domain-specific; Alpha-Wiki provides generic `daily-maintenance` instead |
| MCP cross-model review | Out of MVP scope; deferred to Phase 6 if justified |
| 20 slash commands surface | Cognitive overhead too high. Alpha-Wiki targets 11–13 skills. AgentOps targets 5 Tier 1. |

---

## 3. Superpowers

Source: <https://github.com/obra/superpowers>

### 3.1 Adopted patterns

| Pattern | Where applied |
|---|---|
| Skill description = trigger conditions only, not workflow summary | Cross-cutting principle, every skill in every layer |
| Brainstorm → Plan → Execute three-phase workflow with gates | AgentOps `plan-slice` (brainstorm + plan with gates) and `execute-slice` (execute) |
| Subagent-driven-development (fresh subagent per task) | AgentOps `execute-slice` via Superpowers adapter; native fallback when absent |
| Two-stage review (spec compliance → code quality) | AgentOps `two-stage-review` Tier 2 skill |
| TDD enforced: RED-GREEN-REFACTOR | AgentOps `tdd-cycle` Tier 2 skill; delegates to Superpowers when present |
| Verification-before-completion | AgentOps `verification-before-done` Tier 2 skill |
| Writing-skills as TDD applied to documentation | Internal practice during Phase 1a hardening and AgentOps skill authoring |
| Continuous execution (no "stop every 3 tasks") | AgentOps `execute-slice` runs continuously, stops only on blockers |

### 3.2 Rejected patterns

| Pattern | Why rejected |
|---|---|
| Forced bootstrap via `<EXTREMELY_IMPORTANT>` injected prompt | We respect user autonomy via opt-in plugin install. Session-start hook is the equivalent, opt-in. |
| Forking Superpowers wholesale | Per ADR-002: integrate via process-level adapter only |
| Programmatic API to Superpowers | No API exists. Adapter instructs the agent to invoke `superpowers:*` skills as separate skill calls. |
| `using-git-worktrees` as core requirement | Optional; available via Superpowers when present, no native fallback required |

### 3.3 Deferred patterns

| Pattern | Reason for deferral |
|---|---|
| Cross-platform tool name mapping (Read→read_file etc.) | Claude Code first; Codex/Gemini compatibility in Phase 5 |

---

## 4. Synthesis: cross-cutting principles

The following principles emerge from all three sources combined and apply to every skill in the ecosystem. They are normative, not aspirational.

| # | Principle | Source |
|---|---|---|
| 1 | Skill description = trigger conditions, not workflow summary | Superpowers |
| 2 | Operating-manual depth: every skill defines all 15 dimensions (see `00-architecture.md` §5.2) | Superpowers + audit |
| 3 | Pressure-test skills with subagents before deploying | Superpowers writing-skills |
| 4 | Evidence over claims: no completion without verification output | Superpowers verification-before-completion |
| 5 | Deterministic tools where possible; LLM only for fuzzy work | Karpathy + OmegaWiki tooling |
| 6 | Bidirectional state: every change traceable, auditable, reversible | OmegaWiki bidirectional links |
| 7 | No hidden coupling; cross-layer interaction goes through adapters | New, from boundary discipline |

---

## 5. Anti-patterns (do not adopt)

Explicit list of patterns we have considered and rejected:

- Embedding-based retrieval over markdown wiki (rejected per Karpathy guidance and ADR-003)
- Monolithic single-plugin packaging of memory + agents + discipline (rejected per ADR-001)
- Hard runtime dependency on Superpowers (rejected per ADR-002 and Amendment B)
- Implicit state writes to user-defined directories (rejected per ADR-004 and Amendment A)
- Skills with workflow-summary descriptions (rejected per principle 1)
- Skills without pressure tests (rejected per principle 3)
- "Done" without evidence (rejected per principle 4)
