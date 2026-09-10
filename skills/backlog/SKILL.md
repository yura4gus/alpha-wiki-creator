---
name: backlog
description: "Create, filter, update, validate, and inspect dependency state for the optional AgentOps markdown backlog. Use for controlled multi-track delivery; do not replace a team's external issue tracker or use it for casual notes."
argument-hint: "<add | update | list | blocked | dependencies | validate>"
---

# wiki:backlog - lightweight execution backlog

## Mission

Keep execution commitments explicit and queryable without adding a database.
Each item is one Markdown file so hundreds of tasks remain reviewable and
parallel writers can own disjoint files.

## Name Contract

`backlog` means maintained execution commitments for the optional control
layer. It is not a replacement for an external issue tracker.

## Required Fields

`id`, `title`, `description`, `owner`, `agent_role`, `priority`, `status`,
`track`, `dependencies`, `contracts`, `files`, `acceptance_criteria`, `evidence`,
`created_at`, and `updated_at`.

Statuses are exactly: `TODO`, `PLANNED`, `IN_PROGRESS`, `BLOCKED`, `REVIEW`,
`DONE`, `CANCELLED`.

## Workflow

1. Ensure AgentOps was explicitly initialized.
2. For `add`, require a real owner, role, track, acceptance criteria, affected
   files/contracts, and dependencies.
3. Use `P0` through `P3` priority. Do not infer P0 from importance alone; P0
   blocks the active delivery objective.
4. Use the deterministic tool:

```bash
uv run python -m tools.backlog add --wiki-dir <wiki_dir> ...
uv run python -m tools.backlog update --wiki-dir <wiki_dir> <id> --status <status>
uv run python -m tools.backlog list --wiki-dir <wiki_dir> [filters]
uv run python -m tools.backlog blocked --wiki-dir <wiki_dir>
uv run python -m tools.backlog dependencies --wiki-dir <wiki_dir> [id]
uv run python -m tools.backlog validate --wiki-dir <wiki_dir>
```

5. `DONE` requires evidence. `BLOCKED` requires a reason. Dependency cycles and
   missing dependencies are errors.
6. Never mark work done from an agent narrative without test/file evidence.

## Codex Native Delegation

Backlog mutation stays in the controller. Read-only agents may propose items for
independent tracks, but one controller validates IDs, ownership, dependencies,
and final status transitions.

## Done Criteria

- Every item has a verifiable acceptance contract.
- Filters by status, track, owner, and role are deterministic.
- Blocked work and dependency gaps are visible.
- No task stores raw chat or execution logs.

## References

- `tools/backlog.py`
- `references/agentops-control-layer.md`
- `references/codex-subagent-orchestration.md`
