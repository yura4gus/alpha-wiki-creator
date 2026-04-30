# ADR-001 — Alpha-Wiki ↔ AgentOps boundary

**Status**: Accepted
**Date**: 2026-04-29

## Context

The ecosystem combines persistent memory (Alpha-Wiki) and disciplined agent team execution (AgentOps). Both products provide value independently and are sometimes used together. A clean boundary is required to prevent monolithic coupling, allow independent evolution, and support all combination cases (wiki only, agentops only, both).

## Decision

Alpha-Wiki and AgentOps ship as two separate Claude Code plugins with non-overlapping ownership.

**Alpha-Wiki owns**: the wiki memory layer — three-layer mutability, page lifecycle, frontmatter schema, schema evolution, cross-references, structural lint, graph artifacts, Obsidian/HTML rendering, the `wiki/` namespace at project root.

**AgentOps owns**: the agent operating model — agent team roles, communication mechanisms, process rhythms, review levels, architecture canon, Domain Freeze, 5 Tier 1 skills, 17 Tier 2 skills, the state backend abstraction, the `agentops/` subnamespace under the chosen state backend.

When both are installed, AgentOps stores its operational state under `wiki/agentops/` (not `wiki/state/`, `wiki/decisions/`, etc. at root). Alpha-Wiki's root-level wiki namespace remains untouched.

## Reasoning

1. **Different concerns, different lifecycles.** Wiki schema evolves on knowledge growth; agent operating model evolves on team practice. Coupling the two slows both.
2. **Different audiences.** A research project may use Alpha-Wiki without ever needing AgentOps. A small team may use AgentOps with Markdown fallback and never adopt Alpha-Wiki.
3. **Cleaner testing.** Each plugin has its own test suite, pressure scenarios, CI.
4. **Cleaner upgrades.** A breaking change in one plugin does not force users of the other to migrate.
5. **Composability.** Future third-party plugins can integrate with one without taking a transitive dependency on the other.

## Alternatives rejected

- **Single monolithic plugin.** Rejected: violates the constraint "do not merge Alpha-Wiki and AgentOps into one monolith". Forces users into a heavyweight install when one half suffices.
- **AgentOps depends on Alpha-Wiki.** Rejected: would prevent AgentOps standalone use with Markdown fallback.
- **Alpha-Wiki depends on AgentOps.** Rejected: would prevent solo wiki use cases (research, personal KB).

## Risks

- **Adapter drift.** The wiki-backend-adapter inside AgentOps must stay current with Alpha-Wiki path conventions. Mitigation: contract-tested at integration test boundary.
- **User confusion** about which plugin to install. Mitigation: documented combination matrix in `00-architecture.md` §3.1.
- **Naming overlap risk** if either plugin later adds a skill the other already has. Mitigation: namespaces `/alpha-wiki:*` and `/agentops:*` are non-overlapping by design.

## Validation

- AgentOps `init-project` runs end-to-end on a project with no Alpha-Wiki installed (Markdown fallback works).
- AgentOps `init-project` runs end-to-end on a project with Alpha-Wiki installed (state lands under `wiki/agentops/`).
- Alpha-Wiki `init` runs end-to-end on a project with no AgentOps installed.
- Integration test suite (Phase 2) covers all six combinations from `00-architecture.md` §3.1.
