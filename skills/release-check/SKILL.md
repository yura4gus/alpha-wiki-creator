---
name: release-check
description: "Evaluate a project's AgentOps release readiness from backlog state, summarized sessions, handoffs, evidence, and Alpha-Wiki lint. Use before staging or production; do not confuse it with the Alpha-Wiki package release_audit."
---

# wiki:release-check - project delivery gate

## Mission

Produce an honest `GREEN`, `WARNING`, or `BLOCKED` project release verdict from
repo-native evidence.

## Name Contract

`release-check` evaluates the target project's delivery evidence. It is distinct
from `tools.release_audit`, which validates the Alpha-Wiki package itself.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

1. Identify the requested release and its existing requirements. Use this
   AgentOps workflow only when the target project already uses that layer;
   do not initialize it merely to publish the Alpha-Wiki package.
2. Check unfinished, blocked, or review-stage release work.
3. Verify completed work has evidence and execution waves have session
   summaries.
4. Run Alpha-Wiki structural lint when config is available.
5. Generate the report:

```bash
python3 .alpha-wiki/run.py -m tools.release_check \
  --wiki-dir <wiki_dir> \
  --version <target> \
  --config .alpha-wiki/config.yaml
```

6. Add `--write` only when a persisted release record is requested. Preserve
   the backend verdict and name its target and evidence scope.
7. For each claimed blocker, cite the requirement, observed failure, affected
   required step, and smallest fix. Keep unverified, failed, access-blocked,
   and optional findings distinct. Do not invent secrets, signing, or approvals.
8. Apply owner decisions and production requirements only when the task or
   existing project policy requires them. Package publication and Pages
   deployment have separate outcomes unless an existing rule connects them.

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
