# 03 — Superpowers adapter

> Specification for the `superpowers-adapter` Tier 2 skill inside AgentOps. Process-level adapter only. No fork. No copy. No programmatic API.

References: `00-architecture.md` for boundaries, `02-agentops.md` for AgentOps Tier 1 skills, `adr/ADR-002`.

---

## 1. Purpose

The adapter integrates Superpowers as an optional execution discipline backend. When Superpowers is installed, AgentOps Tier 1 skills (`plan-slice`, `execute-slice`, `pre-integration-check`) instruct the agent to invoke Superpowers skills at the appropriate phase. When Superpowers is absent, AgentOps native fallback Tier 2 skills (`tdd-cycle`, `two-stage-review`, `verification-before-done`) provide equivalent discipline embedded directly in AgentOps.

The adapter does not call Superpowers programmatically. There is no API. The adapter only emits agent instructions.

---

## 2. Hard contract

The adapter must:

1. Detect whether Superpowers is available in the current agent environment.
2. Map AgentOps phases to Superpowers workflows.
3. Instruct the agent to use Superpowers discipline where available.
4. Fall back to native AgentOps discipline where unavailable.
5. Never assume a programmatic API call to Superpowers.
6. Never override project `CLAUDE.md`, `AGENTS.md`, Alpha-Wiki schema, AgentOps state, or user instructions.
7. Log every backend choice (Superpowers vs native) to `<state-backend>/agentops/state/decision_log.md`.

---

## 3. Detection

### 3.1 Mechanism

Adapter probes for Superpowers via:

1. **Plugin marker check**: `~/.claude/plugins/` enumeration looking for `superpowers` plugin directory.
2. **Skill availability check**: probe via Skill tool for skills with prefix `superpowers:` (e.g. `superpowers:brainstorming`, `superpowers:test-driven-development`).
3. **Cache**: detection result cached per session; re-probe at session start only.

If either check succeeds, Superpowers is considered available.

### 3.2 Detection failure

Detection failure is normal, not an error. The adapter logs `superpowers_available: false` and AgentOps Tier 1 skills route to native Tier 2 fallback.

---

## 4. Phase mapping

The adapter maps AgentOps Tier 1 phases to Superpowers skills. This mapping is the integration contract.

### 4.1 `/agentops:plan-slice` → Superpowers

When Superpowers detected, `plan-slice` instructs the agent:

| AgentOps phase | Instruction emitted to agent |
|---|---|
| Brainstorm (Workflow step 1 in `02-agentops.md` §3.3) | "Invoke `superpowers:brainstorming` to refine this feature with Socratic questioning." |
| Decompose (Workflow step 4) | "Invoke `superpowers:writing-plans` to break this into bite-sized tasks with file paths and verification steps." |

Output: AgentOps schema preserved. The plan document under `<state-backend>/agentops/plans/` follows AgentOps format regardless of which backend produced its content.

### 4.2 `/agentops:execute-slice` → Superpowers

When Superpowers detected, `execute-slice` instructs the agent:

| AgentOps phase | Instruction emitted to agent |
|---|---|
| Subagent dispatch (Workflow step 1 of per-task loop) | "Invoke `superpowers:subagent-driven-development` to dispatch this task as an isolated subagent with two-stage review." |
| TDD cycle (step 2) | "Invoke `superpowers:test-driven-development` for RED-GREEN-REFACTOR enforcement on this task." |
| Two-stage review (step 4) | "Invoke `superpowers:requesting-code-review` after implementation; review will pass spec compliance then code quality." |
| Verification (step 5) | "Invoke `superpowers:verification-before-completion` to confirm task is actually done with evidence." |

Output: AgentOps schema preserved. Handoffs under `<state-backend>/agentops/handoffs/` follow AgentOps format. Tests, code, and review evidence flow through Superpowers but are recorded in AgentOps state.

### 4.3 `/agentops:pre-integration-check` → Superpowers

When Superpowers detected, `pre-integration-check` instructs the agent:

| AgentOps phase | Instruction emitted to agent |
|---|---|
| Final verification before merge | "Invoke `superpowers:verification-before-completion` alongside AgentOps-specific contract checks." |

Note: AgentOps-specific contract checks (shared contracts, no local enums, API/event compatibility, security invariants) always run, with or without Superpowers. Superpowers handles the discipline overlay; AgentOps handles the contract-specific overlay.

### 4.4 `/agentops:cto-review` → Superpowers

`cto-review` does **not** delegate to Superpowers. The 7-question audit format and review schema are AgentOps-specific. Superpowers is execution discipline, not weekly audit discipline.

### 4.5 `/agentops:onboard` and `/agentops:init-project` → not delegated

These skills are AgentOps-specific. No Superpowers mapping.

---

## 5. Native fallback

When Superpowers is absent, AgentOps Tier 2 skills provide equivalent discipline natively.

| Superpowers skill | AgentOps native fallback |
|---|---|
| `superpowers:brainstorming` | Native brainstorm logic embedded in `plan-slice` skill body (Socratic, one-question-at-a-time, gate before progressing). |
| `superpowers:writing-plans` | Native decomposition logic embedded in `plan-slice` skill body (file structure mapping, scope check, task list with verification commands). |
| `superpowers:subagent-driven-development` | Native subagent dispatch in `execute-slice` (when subagent platform available). When subagent dispatch unavailable, falls back to inline mode per `subagent_dispatch_mode` setting. |
| `superpowers:test-driven-development` | `tdd-cycle` Tier 2 skill: enforces RED (test fails before code), GREEN (minimal code passes test), REFACTOR (clean up); deletes code written without test and starts over. |
| `superpowers:requesting-code-review` | `two-stage-review` Tier 2 skill: pass 1 spec compliance, pass 2 code quality; critical issues block progress. |
| `superpowers:verification-before-completion` | `verification-before-done` Tier 2 skill: run verification commands; attach output to handoff; no "done" without evidence. |

The native fallback is functionally equivalent at the discipline level, though Superpowers provides more polished implementations (more pressure-tested edge cases, richer instructions, more nuanced gates).

---

## 6. Logging

Every backend choice logged to `<state-backend>/agentops/state/decision_log.md`:

```markdown
## [2026-04-29 14:32] backend-choice | execute-slice | superpowers_available=true → using superpowers:subagent-driven-development
## [2026-04-29 14:35] backend-choice | tdd-cycle | superpowers_available=true → using superpowers:test-driven-development
## [2026-04-29 16:08] backend-choice | plan-slice | superpowers_available=false → using native brainstorm
```

This log is consumed by `cto-review` to surface which discipline backend was active during the period.

---

## 7. Hard guarantees

The adapter enforces these regardless of detection state:

1. **No programmatic API call to Superpowers.** The adapter only emits agent instructions.
2. **No override of project rules.** Project `CLAUDE.md`, `AGENTS.md`, user instructions take precedence over any Superpowers behavior.
3. **No override of Alpha-Wiki schema.** Wiki mutability rules win over any execution-discipline rule.
4. **No override of AgentOps state.** State files remain AgentOps-owned regardless of which backend produced their content.
5. **No silent backend switch mid-slice.** Detection result is fixed for the session; switching backends mid-slice would corrupt logging.

---

## 8. Failure modes

| Mode | Behavior |
|---|---|
| Superpowers detected but skill invocation fails | Log failure to decision_log; fall through to native fallback for that operation. |
| Superpowers behavior conflicts with AgentOps state schema | Project rules win. AgentOps schema preserved. Conflict logged as integration issue if material. |
| Superpowers updated mid-session, behavior changed | Detection cached at session start; new behavior takes effect next session. |
| User explicitly requests "no Superpowers, use native" | Honored via setting override; logged. |

---

## 9. Validation

The adapter's correctness is verified by:

1. **Standalone test**: AgentOps `plan-slice` runs end-to-end on a machine without Superpowers. Native fallback produces a valid plan.
2. **Integrated test**: AgentOps `plan-slice` on a machine with Superpowers correctly emits instructions to invoke `superpowers:brainstorming` and `superpowers:writing-plans`.
3. **Non-interference test**: Adapter never reaches into Superpowers internals (no file reads of Superpowers skills, no parameter inspection).
4. **State preservation test**: Plans produced via Superpowers and via native fallback both conform to AgentOps schema.
5. **Logging completeness test**: Every Tier 1 skill invocation produces a backend-choice entry in `decision_log.md`.

---

## 10. What is NOT in the adapter

For clarity:

- No fork of Superpowers.
- No copy of any Superpowers skill into AgentOps.
- No API endpoint or RPC to Superpowers.
- No state shared with Superpowers beyond what the agent passes between skill invocations.
- No translation of Superpowers output into a non-AgentOps format. AgentOps schema is canonical.
- No detection of platforms that don't support Superpowers (Codex, Gemini CLI). Cross-platform compatibility is a separate concern handled in Phase 5.
- No automatic install of Superpowers if missing. The adapter detects, it does not install.
