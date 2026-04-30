# ADR-004 — State backend abstraction

**Status**: Accepted
**Date**: 2026-04-29

## Context

AgentOps writes operational state: 7 living state files, decisions, handoffs, CCRs, integration issues, reviews, plans, architecture canon, Domain Freeze artifacts. This state must persist across sessions and be readable by future agent invocations.

When Alpha-Wiki is installed, the natural location is inside the wiki. When Alpha-Wiki is not installed, AgentOps must still work, with state living in plain `docs/`.

Two questions: where does AgentOps write, and how does it avoid colliding with Alpha-Wiki's root namespace.

## Decision

AgentOps writes operational state under a single namespaced subdirectory of the chosen state backend root.

| Alpha-Wiki present? | State backend root | AgentOps subdirectory |
|---|---|---|
| Yes | `wiki/` | `wiki/agentops/` |
| No | `docs/` | `docs/agentops/` |

Inside the AgentOps subdirectory, the structure is identical regardless of backend:

```
<state-backend>/agentops/
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
│   └── (8 canon docs)
└── domain/
    └── (4 freeze docs)
```

AgentOps must not write to:

- `wiki/state/`, `wiki/reviews/`, `wiki/handoffs/`, `wiki/decisions/`, `wiki/risks/`, `wiki/contracts/`, or any other root-level wiki directory.

These belong to Alpha-Wiki. Crossing the namespace is a hard error caught by integration tests.

## Reasoning

1. **Single ownership of `wiki/` root.** Alpha-Wiki owns the wiki namespace. AgentOps is a tenant, not a co-owner.
2. **Identical structure under both backends.** A user transitioning from Markdown fallback to Alpha-Wiki gets the same paths, just rerooted. No migration needed for content.
3. **Clear blast radius.** Removing AgentOps means deleting one subdirectory. No archeology.
4. **Detection logic stays simple.** AgentOps probes for Alpha-Wiki and resolves the backend root. The subpath is constant.

## Alternatives rejected

- **AgentOps writes to root-level `wiki/state/`, `wiki/decisions/`.** Rejected: pollutes the wiki namespace, conflicts with Alpha-Wiki's own state and decision concepts (wiki has its own `decisions/` for ADRs about wiki schema; AgentOps has its own ADRs about project decisions).
- **AgentOps uses `.agentops/` hidden directory.** Rejected: hides state from the user, breaks the principle that state is auditable markdown.
- **Different structure per backend.** Rejected: complicates skill code and migration.

## Risks

- **User confusion** about why state is under `agentops/` rather than at wiki root. Mitigation: README and `init-project` output clearly explain the layout.
- **Path conflicts** if a future Alpha-Wiki version adds an entity type named `agentops`. Mitigation: reserved namespace documented; Alpha-Wiki schema evolution must check.

## Validation

- AgentOps lint includes a check that no AgentOps writes happened outside `<state-backend>/agentops/`.
- Integration tests verify the path resolution: with Alpha-Wiki installed, paths resolve to `wiki/agentops/...`; without, to `docs/agentops/...`.
- Switching from Markdown fallback to Alpha-Wiki preserves all state by moving `docs/agentops/` to `wiki/agentops/` (single directory rename, no content rewrite).
