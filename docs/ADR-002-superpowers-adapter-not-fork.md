# ADR-002 — Superpowers as process-level adapter, not fork

**Status**: Accepted
**Date**: 2026-04-29

## Context

Superpowers (`obra/superpowers`) provides production-quality execution discipline: brainstorming, writing-plans, subagent-driven-development, TDD, code review, verification-before-completion. AgentOps benefits significantly from these disciplines but cannot mandate them, since users may not have Superpowers installed and the project must remain composable.

Three integration strategies were considered: fork Superpowers into AgentOps, copy Superpowers skills wholesale, or build an adapter that uses Superpowers when present.

## Decision

AgentOps integrates Superpowers via a **process-level adapter** named `superpowers-adapter`, located at `agentops/skills/_tier2_internal/superpowers-adapter/`.

The adapter:

1. Detects whether Superpowers is installed (via plugin presence marker or skill availability check).
2. When detected: instructs the agent to invoke `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:subagent-driven-development`, `superpowers:test-driven-development`, `superpowers:requesting-code-review`, `superpowers:verification-before-completion` at the appropriate AgentOps phase.
3. When not detected: AgentOps Tier 2 skills (`tdd-cycle`, `two-stage-review`, `verification-before-done`) provide native fallback discipline embedded directly in skill bodies.
4. Logs the chosen backend (Superpowers vs native) for every phase to `decision_log.md`.
5. Does not call Superpowers programmatically. There is no API. The adapter only emits instructions to the agent.
6. Never overrides project `CLAUDE.md`, `AGENTS.md`, Alpha-Wiki schema, AgentOps state, or user instructions.

## Reasoning

1. **Forking forces maintenance burden.** Superpowers evolves; a fork would diverge or require constant rebases. Adapter keeps Superpowers as an upstream that we benefit from passively.
2. **Copying is theft of complexity.** Superpowers skills are deep operational manuals. Copying them into AgentOps creates two sources of truth and licensing ambiguity.
3. **Hard runtime dependency excludes users.** Users of Codex, Gemini CLI, or Claude Code without Superpowers must still get a working AgentOps.
4. **Process-level adapter is what Superpowers itself uses.** Its skills are agent-instruction-driven, not API-driven. The adapter pattern matches Superpowers' own model.
5. **Native fallback ensures parity of capability.** The discipline patterns (TDD, two-stage review, verification) can be embedded in AgentOps Tier 2 skills natively. Superpowers, when present, replaces them with a more polished implementation.

## Alternatives rejected

- **Fork Superpowers into AgentOps.** Rejected: maintenance burden, divergence risk, licensing ambiguity.
- **Copy individual Superpowers skills into AgentOps.** Rejected: same problems on a per-skill basis.
- **Hard runtime dependency on Superpowers.** Rejected: would prevent AgentOps standalone use; would break for users on platforms without Superpowers.
- **Programmatic API to Superpowers.** Rejected: no such API exists; would require Superpowers cooperation; out of scope.

## Risks

- **Superpowers API changes** (skill names, slash commands, frontmatter conventions). Mitigation: adapter detection is defensive; on detection failure, falls back to native.
- **Drift between Superpowers backed mode and native fallback.** Mitigation: AgentOps acceptance tests run both modes and verify equivalent outcomes.
- **Confusion about which mode is active.** Mitigation: every backend choice is logged in `decision_log.md`.

## Validation

- AgentOps `plan-slice` works on a clean machine without Superpowers (native fallback).
- AgentOps `plan-slice` on a machine with Superpowers correctly emits instructions to invoke `superpowers:brainstorming` and `superpowers:writing-plans`.
- AgentOps `execute-slice` works in both modes.
- Adapter never reaches into Superpowers internals.
- `decision_log.md` records the backend choice for every Tier 1 skill invocation.
