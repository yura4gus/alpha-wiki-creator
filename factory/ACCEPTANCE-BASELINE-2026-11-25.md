# Remote factory acceptance — baseline 2026-11-25

Status: **FAIL, 0/16 gates**. This is a read-only baseline, not an acceptance
run. No gate is claimed. The A6 deployment advanced during the baseline; the
latest snapshot is recorded below and the earlier all-`BLOCKED` snapshot is
retained only as context.

## Scope and method

- Worktree used: `.codex/worktrees/ratexai-factory-qa-20261124` (branch
  `codex/factory-remote-qa`). The requested path
  `ratexai-factory-remote-qa-20261124` does not exist; see blockers.
- Railway: read-only `railway list`, `railway status`, `railway service list`,
  `railway deployment list`, variable-key listing and service/domain inspection.
  No deploy, restart, link change, variable write or deletion was performed.
- Temporal: read-only `check_connection` and `get_task_queues` against the
  configured dev namespace. No workflow was started and no queue was modified.
- Local: no Temporal server is listening on `localhost:7233`; no factory worker,
  coordinator, console or OpenCode service is running locally.
- Evidence bundle: private, outside the repository. Only sanitized results are
  reproduced here.

## Gate baseline

Snapshot 1 (`2026-11-24T21:49:31Z`) was all `BLOCKED`: the Railway project had
no deployments and all three queues had zero pollers. Snapshot 2
(`2026-11-24T21:53:12Z`) is the latest and is the table below.

```text
# Remote factory acceptance

- Bundle schema: `agent-factory.remote-acceptance-bundle/1`
- Evidence generated: `2026-11-24T21:53:12Z`
- Source commit: `not recorded`
- Environment: `remote-baseline`
- Overall: **FAIL** (0/16 gates)

| Gate | Track | Status | Evidence or blocker |
|---|---|---|---|
| `RAILWAY_FACTORY_DEPLOYED` | A6 | **BLOCKED** | deployment exists, but no tested source SHA and no health observation |
| `RAILWAY_OPENCODE_READY` | A6 | **BLOCKED** | no evidence section for this gate |
| `TEMPORAL_POLLERS_ACTIVE` | A6/A2 | **FAIL** | queues without pollers: bsc-batch |
| `ITSPLAN_TASK_BINDING_PASS` | ITSPLAN | **BLOCKED** | no evidence section for this gate |
| `REMOTE_CODING_E2E_PASS` | remote-coding | **BLOCKED** | no evidence section for this gate |
| `EXTERNAL_BATCH_WORKER_PASS` | A2/A3/A1 | **BLOCKED** | no evidence section for this gate |
| `RESTART_RECOVERY_PASS` | A6/A2 | **BLOCKED** | no evidence section for this gate |
| `MAC_INDEPENDENCE_PASS` | A6/A5 | **BLOCKED** | no evidence section for this gate |
| `REMOTE_FACTORY_READY` | A6 | **BLOCKED** | no evidence section for this gate |
| `REMOTE_OPENCODE_PASS` | A6 | **BLOCKED** | no evidence section for this gate |
| `DETERMINISTIC_BATCH_PASS` | A2 | **BLOCKED** | no evidence section for this gate |
| `BSC_0029_CANARY_PASS` | A3/A2 | **BLOCKED** | no evidence section for this gate |
| `CHECKPOINT_RESUME_PASS` | A2 | **BLOCKED** | no evidence section for this gate |
| `DQ_READBACK_PASS` | A3/A2 | **BLOCKED** | no evidence section for this gate |
| `ZERO_DUPLICATE_EFFECTS` | A5 | **BLOCKED** | no evidence section for this gate |
| `TELEMETRY_VERIFIED` | A4 | **BLOCKED** | no evidence section for this gate |
```

## Observed blockers

1. **Railway deployment exists but provenance and health are not proven.** One
   control-plane project with two services and two environments exists. During
   the baseline both pilot services reached `SUCCESS` deployments; the earlier
   deployment list was empty. The deployments carry an image digest but no
   40-hex source commit, no health result and no OpenCode readiness evidence.
   The production environment remains empty. This is not a deployment gate pass
   until the tested commit and health are recorded.
2. **One Temporal queue has no pollers.** The configured dev namespace is
   reachable over TLS. `factory-code` and `factory-coordinator` now report one
   workflow and one activity poller each. `bsc-batch` still reports zero pollers
   and zero backlog, so `TEMPORAL_POLLERS_ACTIVE` is `FAIL`; the external batch
   worker has not registered after the external-host rollback. A read-only
   recheck at `2026-11-24T22:14:30Z` was unchanged.
3. **No A6 OpenCode readiness evidence.** No single-instance, auth, model,
   private-endpoint or health artifact exists. A container being deployed is not
   the same as a verified OpenCode instance.
4. **No A4 remote coding or ITSPLAN evidence.** No remote task receipt, review
   session, PR, issue binding, planner output or zero-write audit exists in this
   worktree.
5. **No external batch evidence.** No `bsc-batch` worker, BSC-0029 manifest,
   BSC receipt, checkpoint, DQ report or readback exists. A2 code is present only
   in its own worktree; it is not merged into this QA branch.
6. **No A4 telemetry evidence.** The telemetry module is present only in its own
   worktree; this QA branch has no agent-step or review telemetry artifact and no
   receipt carrying telemetry.
7. **No restart or independence evidence.** There is no deployed control plane or
   external worker to restart, and no workflow history to prove that local
   shutdown leaves remote work running.

## Offline checks (not gates)

| Check | Result | Note |
|---|---|---|
| `pytest tests/test_acceptance.py` | 22 passed | Gate evaluator tests |
| `pytest tests/test_remote_acceptance.py` | 16 passed, 2 skipped | Live remote and A2-manifest tests are opt-in in this branch |
| Offline factory suite excluding `tests/test_workflows.py` | 99 passed, 16 skipped, 1 failed | Live suites skip by design; the failure is the harness workflow-task timeout below |
| A2 worktree `tests/test_batch_units.py` | 23 passed | Implementation test only; no remote evidence |
| A4 worktree `tests/test_telemetry.py tests/test_review_telemetry.py` | 22 passed | Implementation test only; no remote evidence |
| `tools.document_worker check` | PASS | Canonical document governance |
| `tools.lint --dry-run` | 0 errors, 0 warnings | Wiki structure |
| `tests/test_harness_integration.py::test_coordinator_is_a_durable_typed_surface_over_task_workflow` | flaky | Failed once with `Workflow task duration exceeded 5 seconds` (15.7 s and 16.7 s attempts, 230 KB history); passed on isolated rerun. Host-load/timing sensitive, unrelated to the acceptance changes. |
| `tests/test_workflows.py::test_three_concurrent_tasks_with_disjoint_ownership` | flaky | Failed once at 12.0 s against a 9 s wall-clock bound; passed on rerun. The bound is timing-sensitive and unrelated to the acceptance changes. |

## Environment blockers for this QA session

- The requested worktree path `/Users/.../ratexai-factory-remote-qa-20261124`
  is absent. Work was done in the sibling
  `/Users/.../ratexai-factory-qa-20261124` worktree, whose branch is
  `codex/factory-remote-qa`.
- Git metadata points at a path this session cannot read, so `git status`,
  `git diff` and commits fail with `Operation not permitted`. The parent must
  commit the changes and correct the worktree path if a different checkout is
  required.
- No private value is reproduced in this document. Raw baseline evidence stays
  in the private temp path used for the run.

## Exit condition

A gate moves from `BLOCKED` to `PASS` only after the matching private evidence is
produced, hashed, and evaluated by `agent_factory.acceptance`. A Railway project
with an unproven deployment, or a reachable Temporal namespace with a missing
queue poller, is not readiness.
