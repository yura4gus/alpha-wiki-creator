---
name: release-check
description: "Evaluate a project's AgentOps release readiness from backlog state, summarized sessions, handoffs, evidence, and Alpha-Wiki lint. Use before staging or production; do not confuse it with the Alpha-Wiki package release_audit."
argument-hint: "--version <target> [--write]"
---

# wiki:release-check - project delivery gate

## Mission

Produce an honest `GREEN`, `WARNING`, or `BLOCKED` project release verdict from
repo-native evidence.

## Name Contract

`release-check` evaluates the target project's delivery evidence. It is distinct
from `tools.release_audit`, which validates the Alpha-Wiki package itself.

## Workflow

1. Run deterministic backlog and handoff validation.
2. Check unfinished, blocked, or review-stage release work.
3. Verify completed work has evidence and execution waves have session
   summaries.
4. Run Alpha-Wiki structural lint when config is available.
5. Generate the report:

```bash
uv run python -m tools.release_check \
  --wiki-dir <wiki_dir> \
  --version <target> \
  --config .alpha-wiki/config.yaml \
  --write
```

6. A Release Agent may interpret deployment-specific evidence, but it must not
   turn a deterministic blocker into a green narrative.
7. `WARNING` requires an owner and next action before production approval.

## Verdicts

- `GREEN`: no deterministic blocker or unresolved warning.
- `WARNING`: evidence is incomplete or work remains in review.
- `BLOCKED`: blocked/incomplete release work or invalid operational state.

## Codex Native Delegation

Run the deterministic backend once in the controller. A read-only Release Agent
may inspect staging/deployment evidence afterward; the controller owns the final
report and does not run competing release checks.

## Done Criteria

- Verdict cites concrete backlog/session/lint evidence.
- Deployment-specific unknowns remain visible.
- The report is stored under `<wiki_dir>/agentops/releases/` when `--write` is
  requested.

## References

- `tools/release_check.py`
- `tools/release_audit.py`
- `references/agentops-control-layer.md`
- `references/codex-subagent-orchestration.md`
