# Alpha-Wiki AgentOps Control Layer v0.2

AgentOps is an optional repo-native execution-memory layer over Alpha-Wiki. It
does not create autonomous agents, a scheduler, or a second knowledge engine.

## Boundary

- Alpha-Wiki core owns project memory, contracts, graph, status, review, and
  rendering.
- The optional control layer owns master goal, tracks, backlog, execution-wave
  sessions, summarized handoffs, operational decisions, and project release
  evidence.
- State lives only under `wiki/agentops/`.
- Normal Alpha-Wiki init and the 15-minute first-run path do not create AgentOps
  state.
- Native Codex/Claude subagents execute roles. Alpha-Wiki stores declarations
  and summaries, not running agents.

## Entities

| Entity | Meaning |
|---|---|
| orchestrator | Controller-owned master goal, current objective, snapshot, governance, next prompt. |
| track | Independent execution scope with owner, role, dependencies, and acceptance criteria. |
| agent | Role declaration and permissions passed to a native platform agent. |
| session | One execution-wave summary: snapshot, files, contracts, decisions, risks, tests, result, next steps. |
| handoff | Summarized transfer between roles. Raw logs are forbidden. |
| decision | Durable execution decision linked to affected files/contracts and source session. |
| backlog_item | One-file task with owner, role, dependencies, acceptance, and evidence. |
| release | Project release verdict, blockers, and evidence. |

## Roles

The standard registry contains CTO, Architect, Backend, Frontend, DevOps, QA,
Documentation, and Release roles. These are ownership contracts, not global
agent profiles and not background processes.

## Delivery Cycle

```text
PLAN -> ARCHITECTURE -> IMPLEMENTATION -> TESTING -> REVIEW
     -> DOCUMENTATION UPDATE -> STAGING -> PRODUCTION -> POST-RELEASE ROLLUP
```

The controller may combine stages for small scopes. It must not skip acceptance
evidence, documentation synchronization, or unresolved blockers.

## Status Separation

- Backlog state: `TODO`, `PLANNED`, `IN_PROGRESS`, `BLOCKED`, `REVIEW`, `DONE`,
  `CANCELLED`.
- Governance: `GREEN`, `WARNING`, `BLOCKED`.
- Native subagent terminal state: `GREEN`, `FIXES_REQUIRED`, `BLOCKED`,
  `UNPROVEN`, `STALE_SNAPSHOT`.

These vocabularies serve different purposes and must not be collapsed.

## Explicit Exclusions

No RAG, embeddings, semantic search, SaaS UI, external orchestration platform,
daemon, autonomous master agent, raw-log archive, architecture canon ceremony,
custom TDD framework, or issue-tracker replacement.
