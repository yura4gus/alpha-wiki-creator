# Codex Parallel Audit Prompt

Use this card for a large read-only audit with independent scopes. Replace the
example repositories and scopes. Do not copy domain-specific claims from another
project.

## Controller Preflight

```text
Run a read-only parallel audit. Do not implement or edit files.

Before spawning agents:

1. Read all applicable AGENTS.md files and wiki/graph/context_brief.md.
2. Identify the repositories and active scope.
3. Fetch required remote metadata once in the controller.
4. Record a pinned snapshot. For a dirty worktree include a stable digest of
   tracked and untracked non-ignored content and pause writes during the
   evidence wave:

   uv run python -m tools.worktree_snapshot --root . --json-output

| Repository | Branch/ref | Exact SHA | Dirty state/digest | Review/pipeline |

5. State network, secret, external-side-effect, and file-write restrictions.
6. Treat every starting assumption as a hypothesis to CONFIRM, REFUTE, or mark
   UNPROVEN.
```

## Parallel Evidence Wave

```text
Spawn one read-only subagent per independent scope below. Use the controller's
pinned snapshot; subagents must not fetch shared refs independently.

For every agent provide:

- role and exact scope;
- explicit non-scope;
- required context and source-of-truth paths;
- forbidden actions;
- expected checks;
- stable finding IDs;
- result envelope and terminal status.

Each agent returns:

Scope:
Snapshot:
Checks performed:
Findings:
Unknowns:
Owner decisions:
Status: GREEN | FIXES_REQUIRED | BLOCKED | UNPROVEN | STALE_SNAPSHOT

Every finding includes severity, PROVEN/INFERRED/UNPROVEN, and
`path:line@SHA` evidence for committed content or
`path:line@snapshot:<digest>` for dirty-worktree content.

Do not create nested subagents. Do not expose secret values. Do not write files.
```

Example independent scopes:

```text
Agent 1: repository and migration ownership
Agent 2: historical test evidence
Agent 3: runtime execution and recovery
Agent 4: external acceptance boundaries
Agent 5: signer/security boundaries
```

## Dependent Contract Wave

Run this after the evidence wave when contract alignment depends on runtime
findings:

```text
Spawn one read-only contract-alignment agent. Give it the pinned snapshot,
ratified ADR/contracts, and validated evidence summaries from the first wave.

Classify each difference:

- BOTH_ALIGNED
- RUNTIME_CORRECT_DOC_STALE
- DOC_CORRECT_RUNTIME_GAP
- OWNER_DECISION_REQUIRED

Runtime proves current behavior. Accepted contracts define intended behavior.
Do not silently choose one when they disagree.
```

## Controller Synthesis

```text
Wait for every agent to reach a terminal state. Do not synthesize partial
results as complete.

1. Re-run `tools.worktree_snapshot` and verify every reported SHA and worktree
   digest match the pinned snapshot.
2. Allow at most one bounded retry for a failed or malformed result.
3. Reject STALE_SNAPSHOT evidence.
4. Deduplicate findings by evidence and ownership, not wording.
5. Separate proven facts, inference, unknowns, and owner decisions.
6. Return one consolidated report.
7. Close completed agent threads.
8. Do not implement.

If proposing a writer wave, use no more than two writers, assign disjoint files,
give every shared file one owner, and require explicit approval.
```

See `references/codex-subagent-orchestration.md` for the normative contract.
