# Codex Subagent Orchestration Contract

Alpha-Wiki uses native Codex subagents. It does not implement a separate agent
runtime. This contract keeps parallel work bounded, evidence-first, and safe for
the repository memory layer.

## When To Delegate

Delegate only when a task has at least two independent, material scopes.
Read-heavy exploration, audit, source analysis, and summarization are the best
fits. Keep deterministic commands and tightly coupled writes in the controller.

- Default to two to four subagents.
- Use five or six only when the user requests it or the scopes are demonstrably
  independent.
- Do not create nested subagents unless the user explicitly requests nested
  delegation.
- Do not delegate `doctor`, `lint`, `status`, `render`, or `rollup` backends.

## Controller Preflight

Before fan-out, the controller must:

1. Read applicable `AGENTS.md`, `wiki/graph/context_brief.md`, and active scope.
2. Define each repository and scope.
3. Fetch remote metadata once when fresh remote evidence is required.
4. Record an immutable snapshot: repository, branch/ref, exact SHA, dirty state,
   and relevant review/pipeline identifiers when available.
5. State permissions, secret policy, network policy, and forbidden actions.
6. Assign non-overlapping read scopes or disjoint write ownership.

Subagents must not independently refresh a shared remote snapshot. If their
observed SHA differs from the controller snapshot, they return
`STALE_SNAPSHOT` instead of silently continuing.

For a dirty worktree, the SHA alone is not sufficient. The controller and every
verifying subagent must use the same canonical command:

```bash
uv run python -m tools.worktree_snapshot --root . --json-output
```

The tool hashes the base SHA, Git porcelain status, binary tracked diff, and
path/type/mode/content of every untracked non-ignored file. Symlinks are hashed
by link target, never by target contents. Record its
`<sha>+worktree:<digest>` snapshot ID and pause controller and agent writes for
the read-only evidence wave. Evidence from an uncommitted file uses
`path:line@snapshot:<digest>` rather than pretending it exists at the base SHA.
If a second tool run differs before synthesis, reject the evidence as
`STALE_SNAPSHOT`.

## Subagent Prompt Contract

Every delegated task must include:

1. **Role and scope** - one bounded responsibility plus explicit non-scope.
2. **Pinned snapshot** - exact repository SHA(s), plus a worktree digest when
   dirty, supplied by the controller.
3. **Context** - applicable `AGENTS.md`, Alpha-Wiki brief, active pages,
   contracts, and source-of-truth files.
4. **Permissions** - read-only or an exact write set.
5. **Forbidden actions** - no secret output, generated graph edits, scope
   expansion, nested delegation, or unapproved external side effects.
6. **Evidence rules** - cite file paths, symbols, wiki pages, commands, and
   exact SHAs. Separate observed evidence from inference.
7. **Output envelope** - concise findings, unknowns, decisions, and one terminal
   status.

## Result Envelope

Use this stable shape so the controller can consolidate results:

```text
Scope:
Snapshot:
Checks performed:
Findings:
Unknowns:
Owner decisions:
Status:
```

Each finding should have a stable local ID, severity, evidence status
(`PROVEN`, `INFERRED`, or `UNPROVEN`), and a precise reference such as
`path:line@SHA`.

Terminal statuses are:

- `GREEN` - requested evidence is complete and no blocking gap was found.
- `FIXES_REQUIRED` - actionable non-blocking or blocking gaps were proven.
- `BLOCKED` - access, dependency, or required evidence prevented completion.
- `UNPROVEN` - the scope was inspected but the available evidence cannot support
  a conclusion.
- `STALE_SNAPSHOT` - observed repository state does not match the pinned SHA.

Domain workflows may prefix these values, but the suffix and meaning stay
stable.

## Truth Precedence

- Runtime and tests at the pinned SHA prove what currently happens.
- Accepted ADRs and ratified contracts define what is intended or forbidden.
- Other wiki pages provide maintained memory and navigation, not automatic
  runtime proof.
- When runtime and a ratified contract disagree, classify the difference as
  runtime drift, stale documentation, or owner decision required. Do not
  silently choose one.
- Treat user-supplied starting points as hypotheses to confirm, refute, or mark
  `UNPROVEN`.

## Waves And Synthesis

Use staged execution when one scope depends on another:

1. Controller preflight and immutable snapshot.
2. Parallel evidence wave.
3. Result validation: all agents terminal, SHAs match, output envelope present.
4. Optional dependent analysis wave, such as contract alignment.
5. Controller synthesis: deduplicate evidence, preserve disagreements, and
   separate facts, inference, and owner decisions.
6. Optional writer proposal. Do not begin writes without approval.

If a subagent fails, allow at most one bounded retry with corrected context.
After all agents reach a terminal state, close their threads.

## Write Ownership

- Prefer read-only agents.
- For parallel writes, assign disjoint files or directories.
- A shared file has exactly one writer per wave.
- The controller integrates results and runs deterministic graph rebuild, lint,
  review, and tests after the final write.
- `raw/**` remains source evidence and `wiki/graph/**` remains generated.

## Alpha-Wiki Operation Policy

| Operation | Native Codex delegation |
|---|---|
| `init` | Optional read-only inventory by repository for large or multi-repo projects |
| `ingest` | Parallel source analysis, followed by one curator writer |
| `query` | Optional parallel research for broad cross-domain questions |
| `evolve` | Parallel schema-gap evidence, followed by one owner decision |
| `review` | Parallel structure, contract, and freshness/gap review |
| `audit-project` | Controller snapshot, parallel evidence scopes, synthesis |
| `spawn-agent` | Create a reusable profile or run bounded native subagents |
| `doctor`, `lint`, `status`, `render`, `rollup` | No fan-out; run deterministic backends |

## References

- OpenAI Codex subagents: https://developers.openai.com/codex/subagents/
- `skills/spawn-agent/SKILL.md`
- `docs/ADR-006-spawn-agent-boundary.md`
