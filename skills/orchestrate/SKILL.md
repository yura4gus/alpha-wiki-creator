---
name: orchestrate
description: "Plan and execute an optional Alpha-Wiki AgentOps wave with native Codex/Claude agents, explicit tracks, pinned context, session evidence, conflict resolution, and one next master prompt. Use for substantial multi-track delivery; do not use for a small single-agent task."
---

# wiki:orchestrate - controlled execution waves

## Mission

Coordinate substantial engineering work without creating an autonomous agent
runtime. The main task remains the controller. Native platform agents execute
bounded tracks; Alpha-Wiki stores only durable summaries and evidence.

## Name Contract

`orchestrate` means plan, fan out, collect, and close one controlled execution
wave. It does not mean autonomous scheduling or background execution.

## Opt-In Boundary

- Do not initialize AgentOps during normal `$alpha-wiki:init`.
- Use AgentOps only after an explicit user request for coordinated execution.
- Keep all state under `<wiki_dir>/agentops/`.
- Do not install role-specific agents globally or put role logic in
  `$alpha-wiki:spawn-agent`.
- Do not use this workflow for one small task or one tightly coupled change.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

Choose one mode below. The controller always owns the snapshot, track
dependencies, shared-file integration, deterministic checks, and final
synthesis.

## Modes

### `init`

Initialize the optional control layer and eight role declarations:

```bash
python3 .alpha-wiki/run.py -m tools.orchestrate init \
  --wiki-dir <wiki_dir> \
  --goal "<master goal>" \
  --objective "<current objective>"
```

### `plan`

1. Read Alpha-Wiki context, contracts, accepted decisions, risks, and backlog.
2. Define the master goal and one current objective.
3. Split only independent work into tracks.
4. Assign one owner and one agent role per track.
5. Persist tracks with `tools.orchestrate add-track`.
6. Add executable backlog items with `$alpha-wiki:backlog`.
7. Present the proposed wave before implementation when it changes scope or
   shared contracts.

### `run` / `resume`

1. Run `tools.worktree_snapshot` once in the controller.
2. Select only dependency-ready tracks that benefit from delegation; one
   remaining track is valid. Use more agents only for material independent work.
3. Start one summarized session for every delegated agent execution, not for
   individual tool calls.
4. Spawn native Codex/Claude agents with bounded, disjoint scopes.
5. Give every agent the context brief, pinned snapshot, permissions, files,
   contracts, acceptance criteria, and stable output envelope.
6. Do not allow nested delegation or independent shared-ref refresh.
7. Continue independent controller work while agents run. Wait when their
   evidence is needed; obtain all required terminal results before synthesis.
   Reject stale snapshots and allow one bounded retry for failed evidence.
8. Resolve conflicts in the controller. Accepted contracts define intended
   behavior; runtime and tests prove current behavior.
9. Integrate one write owner per shared file, run deterministic tests/lint, and
   complete the session with evidence.
10. Update backlog, decisions, risks, Alpha-Wiki pages, and next master prompt.

### `close`

Close the wave only after all agents are terminal and session evidence has been
written. Create a handoff only when responsibility or unfinished work actually
moves to another role. Run status, lint, review, and release-check as needed.

### `status`

```bash
python3 .alpha-wiki/run.py -m tools.orchestrate status --wiki-dir <wiki_dir>
```

## Role Registry

- CTO: direction, tradeoffs, architecture decisions, roadmap.
- Architect: boundaries and API/code/integration contracts.
- Backend: APIs, database, migrations, backend implementation.
- Frontend: UI, flows, and frontend contracts.
- DevOps: CI/CD, environments, deployment, secrets/configuration.
- QA: unit/integration/e2e/regression and release evidence.
- Documentation: wiki freshness, consolidation, gaps, provenance.
- Release: staging/production readiness, deployment and rollback evidence.

Roles are context declarations, not persistent autonomous processes.

## Codex Native Delegation

Use the native Codex subagent workflow defined in
`references/codex-subagent-orchestration.md`. The main task remains the
controller, records one pinned snapshot, and chooses only useful independent
tracks for delegation. Do not create idle tracks to fill a default count.
Subagents cannot create nested agents or own shared deterministic checks.

## Session Contract

Every execution wave records: session ID, role, goal, scope, pinned snapshot,
files changed, contracts changed, decisions, risks, tests, result, and next
steps. Raw logs are never copied into the wiki.

## Done Criteria

- Ownership and write scopes are unambiguous.
- Every agent reaches a terminal status.
- Backlog and session evidence reflect actual results.
- Contracts and durable wiki pages are synchronized.
- The orchestrator stores one clear next master prompt.

## References

- `references/agentops-control-layer.md`
- `references/codex-subagent-orchestration.md`
- `tools/orchestrate.py`
- `tools/backlog.py`
