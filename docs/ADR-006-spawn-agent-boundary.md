# ADR-006 — spawn-agent boundary frozen

**Status**: Accepted
**Date**: 2026-04-29

## Context

Alpha-Wiki ships a skill `/alpha-wiki:spawn-agent` that generates wiki-aware Claude Code subagents respecting the wiki mutability matrix.

AgentOps ships a Tier 2 skill `agent-skills-bootstrap` that creates 9 universal team agents and N project-specific execution agents during `init-project`.

The names overlap conceptually. Without an explicit boundary, drift is likely: AgentOps could call into `spawn-agent` for team roles, or `spawn-agent` could grow team-role logic. Both directions create coupling we must prevent.

## Decision

The boundary is frozen as follows.

**Alpha-Wiki `spawn-agent`**:
- Wiki-scoped only. Generates subagents that read and write wiki content according to the wiki mutability matrix.
- Does not know about agent team roles, hierarchy, communication mechanisms, or operating model.
- Does not know that AgentOps exists. Operates identically whether AgentOps is installed or not.
- May be used standalone (Alpha-Wiki without AgentOps) or as a registration helper called by AgentOps.

**AgentOps `agent-skills-bootstrap`**:
- Owns all team-role logic. Creates the 9 universal agents (CTO Integration, Domain, Security Architect, QA, Documentation, Release Manager, Backend, Frontend, Audit-Challenge) with full operating-model context.
- Creates N project-specific agents based on detection of project signals from raw materials.
- When Alpha-Wiki is installed, may invoke `spawn-agent` as a registration helper to create wiki-aware subagent files. The team-role definition stays in AgentOps; `spawn-agent` adds wiki awareness.
- When Alpha-Wiki is not installed, creates agent skill files directly under `.claude/skills/` without wiki integration.

**Hard constraint**: `spawn-agent` must not become the team bootstrapper. Any logic that knows about CTO Integration, Domain Agent, Security Architect, etc. lives in AgentOps. `spawn-agent` is a generic wiki-aware subagent generator and stays that way.

## Reasoning

1. **Single source of truth for team roles.** Team operating model is AgentOps' core competency. Splitting it across two plugins creates drift.
2. **Single source of truth for wiki awareness.** Wiki mutability is Alpha-Wiki's core competency. AgentOps cannot reimplement it without coupling.
3. **Composition direction.** AgentOps optionally depends on Alpha-Wiki; the reverse must never be true. Therefore `agent-skills-bootstrap` knows about `spawn-agent`, but `spawn-agent` does not know about `agent-skills-bootstrap`.
4. **Standalone use cases preserved.** A user with only Alpha-Wiki can still use `spawn-agent` for any wiki-aware subagent need — research, documentation, etc.

## Alternatives rejected

- **`spawn-agent` becomes the AgentOps team bootstrapper.** Rejected: violates plugin boundary, mixes concerns, makes Alpha-Wiki accidentally aware of agent operating model.
- **AgentOps reimplements wiki awareness in `agent-skills-bootstrap`.** Rejected: duplicates Alpha-Wiki logic, creates drift, violates ADR-001 boundary.
- **Merge both into one skill in one of the plugins.** Rejected: forces a runtime coupling between the plugins that ADR-001 explicitly prevents.

## Risks

- **Future feature requests** to make `spawn-agent` "smarter" about team roles. Mitigation: this ADR is the definitive boundary. New requests are evaluated against it.
- **Path overlap** if `agent-skills-bootstrap` writes agent files where `spawn-agent` would. Mitigation: integration tests verify each owns its outputs.

## Validation

- Alpha-Wiki `spawn-agent` source contains zero references to AgentOps team roles (CTO Integration, Domain Agent, etc.).
- AgentOps `agent-skills-bootstrap` source uses `spawn-agent` only as a registration helper, with team-role context passed in as parameters.
- Standalone Alpha-Wiki usage: `spawn-agent` works without AgentOps installed.
- Combined usage: `agent-skills-bootstrap` produces wiki-aware team agents by composing `spawn-agent` invocations with team-role payload.
- Removal of either plugin does not break the other's `spawn-agent` / `agent-skills-bootstrap` independent flows.
