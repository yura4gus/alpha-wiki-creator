# ADR-007 - Optional AgentOps Control Layer

- Status: Accepted
- Date: 2026-09-08
- Supersedes: the packaging and ownership direction in ADR-001 and ADR-004/04-state-backend-contract for the lightweight v0.2 scope
- Preserves: ADR-006 generic `spawn-agent` boundary

## Context

The original design separated a large standalone AgentOps product with its own
plugin, fallback backend, architecture canon, ceremonies, and internal skill
hierarchy. Current product needs are narrower: controlled multi-track execution
that keeps ownership, backlog, sessions, handoffs, and release evidence next to
Alpha-Wiki memory.

## Decision

Alpha-Wiki may provide an optional AgentOps control layer under
`wiki/agentops/`. It consists of Markdown state, deterministic tools, four
user-facing workflows, and native Codex/Claude subagents.

The layer is opt-in and does not run during ordinary Alpha-Wiki initialization.
It does not import or emulate an external agent runtime. Role declarations are
passed to native agents by the controller. `spawn-agent` remains generic and
contains no team-role registry.

The Alpha-Wiki package version remains independent from AgentOps schema version
`0.2`.

## Consequences

- Small projects keep the existing simple workflow.
- Large projects can coordinate two to four independent tracks with durable
  summarized evidence.
- All operational state has one removable namespace.
- The previous standalone AgentOps design remains historical reference, not the
  active implementation plan.

## Rejected Scope

- Standalone AgentOps plugin or `docs/agentops/` fallback.
- Mandatory role installation or background agents.
- RAG, embeddings, SaaS UI, scheduler, enterprise workflow, or raw-log storage.
- Duplicating Alpha-Wiki status, review, graph, or release-package audit.
