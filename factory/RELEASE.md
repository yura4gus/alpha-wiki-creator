# Agent Factory V1 — release record

Status: **RELEASED IN v0.8.2**. PRs #4, #5, #6 and #3 are merged; hosted CI is
green. The optional Harness layer is live-E2E verified: three real OpenCode tasks
ran through the coordinator with live review, durable approval, worker/session
restart and no duplicate workflows. See
[Harness coordination layer](#harness-coordination-layer).

Factory code: `c51e1a355f08a1a917711d93b8a64634f9a964f7` (PR #6). Release
source: the `v0.8.2` tag on `main`.

## Scope

Optional `factory/` package only. No plugin manifest, skill, hook, wiki schema or
production runtime is changed by enabling it. Temporal Core plus the existing
thin CLI adapter remain the executor; the Temporal Agent Harness spike decision in
`spikes/harness/FINDINGS.md` is unchanged.

## Acceptance evidence (2026-11-16, macOS, Temporal CLI 1.10.1, OpenCode 2.1.4)

| Gate | Result | Evidence |
|---|---|---|
| Offline factory suite | PASS | `uv run pytest`; live suites skip by default |
| Real OpenCode CLI task | PASS | `tests/test_live_cli.py::test_live_cli_success_edits_tests_commits_review` (52.9 s); two real edits, real unittest run, two pushed checkpoints, live DeepSeek review, `PR_OPEN` |
| SUCCESS | PASS | same test; receipt validates, one PR |
| CRASH | PASS | `test_live_cli_crash_recovers_from_checkpoint` (41.5 s); worker killed during step 1, fresh work root, step 0 reused, no duplicate commits, replay passes |
| APPROVAL | PASS | `tests/test_launcher_e2e.py`; workflow waits, launcher applies explicit `--approve-by owner`, receipt records it |
| REPLAY | PASS | fake-agent replay tests plus `Replayer` assertions in live crash test |
| Three concurrent isolated tasks | PASS | `test_live_cli_three_concurrent_tasks_stay_isolated` (15.8 s); three real CLI calls, disjoint diffs/branches/PR numbers |
| Idempotent post-push retry | PASS | `test_live_cli_step_reuses_pushed_commit` (15.6 s); wrapper proves one model call, one commit |
| Live independent review | PASS | `tests/test_review_live.py` (4 passed); paid DeepSeek model, scope creep rejected, APPROVE requires findings |
| Review failure handling | PASS | nonzero exit with plausible APPROVE → `BLOCKED_REVIEW`, no PR; hashes retained |
| One-command startup | PASS | `tests/test_launcher_e2e.py`; started Temporal, worker, approval, receipt; status reads after server stop |
| Harness SDK pin | PASS | `temporal-agent-harness[ui]==0.11.0` in the optional extra and `uv.lock`; base install has no harness/pydantic |
| Coordinator typed surface | PASS | `tests/test_harness_integration.py`; submit/status/approve/cancel through `AgentClient`, tool events, no model |
| Harness approval authority | PASS | approval goes through `TaskWorkflow.decide`; no harness approval queue, receipt records the operator |
| Coordinator restart/reconnect | PASS | same agent workflow id, new coordinator worker and new `AgentClient`; status and digest unchanged |
| Three real OpenCode tasks via Harness | PASS | `tests/test_harness_live.py` 31.2 s; 3 live reviews, 3 PRs, one approved through the coordinator |
| Harness Console/API | PASS | `tests/test_harness_console_live.py`; real HTTP session, submit, status, approval, receipt; browser UI manual |
| One-command Harness stack | PASS | `FACTORY_LIVE_HARNESS_STACK=1`; console, coordinator, factory worker, clean stop |
| Temporal Cloud | PASS | `alpha-dev.n3kw9` smoke workflow `PR_OPEN`; receipt/history contain no API key |
| Alpha-Wiki context | PASS | receipt context sources pin `AGENTS.md` and `wiki/graph/context_brief.md` |
| xPlan dry-run | PASS | live run returned `NO_CHANGE` with five evidence refs; no write |
| Harness² receipt | PASS | real replay `evaluation.json`, 3/3 holdouts, status `PASS` |
| OpenFlowKit receipt | PASS | real report on `d34c302040c86e0c72780f12d97052a70c76557b`, status `PASS`, model SHA pinned |
| Contract boundaries | PASS | `tests/test_contracts.py` (no provider SDK/HTTP, no xPlan write, no duplicated architecture logic) |

Measured cost: step/test elapsed seconds and workflow wall time are stored in
receipt metrics. OpenCode CLI does not expose per-run token/cost data to this
adapter, so no cost figure is claimed.

Real Harness² and OpenFlowKit receipts used in the integration run:

- Harness² `evaluation.json` SHA-256 `b4e66b1fbc2ab96cddf425546a16b2370ef94b4e09bb1d39c53ce27dfaec1908`
- OpenFlowKit `report.json` SHA-256 `af7d7084570104ec0accb0e950812e0a02e677598a635bbeb9264bd756345310`

## Harness coordination layer

State: **IMPLEMENTED / LIVE E2E PASSED** (AH-01..AH-07). The harness is a
coordination surface over the unchanged factory execution path, not a second
executor or approval authority.

- Python SDK `temporal-agent-harness[ui]==0.11.0` is an optional extra with an
  exact pin and regenerated `uv.lock`. The base install imports neither the
  harness nor pydantic.
- `FactoryCoordinatorAgent` exposes typed `submit_task`, `get_status`,
  `approve_task`, `cancel_task` handlers. Each dispatches one
  `@agent.activity_tool_defn` through `runner.run_tool`, so the Console receives
  real `tool_start`/`tool_end` events.
- `submit_task` uses the existing `validate_batch` + `start_task` path with
  `REJECT_DUPLICATE` and `FAIL`: one `task-<id>` workflow, no second run.
- `approve_task` forwards to `TaskWorkflow.decide`; Harness tool approval is
  deliberately skipped. There is no second approval queue.
- `cancel_task` uses the workflow's cancellation path and returns the finalized
  `CANCELED` receipt.
- The coordinator makes no model call and imports no provider SDK. Real edits
  and reviews in the three-task run still went through OpenCode.
- `launcher up --harness` starts the native session manager, API and Console,
  the coordinator worker and the existing factory worker, then stops the
  process groups on exit. `--task` stays optional; logs and `stack.json` live
  under `FACTORY_STATE_DIR/harness/`.

Evidence (2026-11-16, macOS, Temporal CLI 1.10.1, harness 0.11.0):

- `uv run --extra harness pytest` → 80 passed, 15 skipped.
- Full live run (CLI, review, launcher, harness, Cloud) → 94 passed, 1 skipped;
  the skip is the older live review test that lacks its dedicated flag.
- `tests/test_harness_integration.py` → 11.3 s: submit/status/approve/cancel,
  no harness approval events, coordinator restart and duplicate submit rejected.
- `tests/test_harness_live.py` → 31.2 s: three real OpenCode tasks submitted
  through the coordinator, three live reviews, three PRs, one approval by
  `harness-operator`, both workers restarted, new `AgentClient` reconnected and
  the receipt digests were unchanged.
- `FACTORY_LIVE_HARNESS_STACK=1` → console + coordinator + factory worker start,
  `/api/agents` and pollers ready, clean stop.
- Console API: `doctor --registry harness/agents.toml --api-url ...` passed all
  checks; `tests/test_harness_console_live.py` created a real session, submitted
  a task, observed `AWAITING_APPROVAL`, approved it, and read `PR_OPEN` with a
  frozen receipt over HTTP. The typed events were
  `turn_started → message_handler_start → tool_start → tool_end →
  message_handler_end → turn_end`. No model or harness-approval events.
- Temporal Cloud `alpha-dev.n3kw9`: one fake-agent `TaskWorkflow` completed
  `PR_OPEN` on a unique queue; workflow id `task-cloud-smoke-2b6483cc18`,
  receipt digest `b949325b6835e7950aa380d5ff378e0cc9198c0ec5fdaed7ee95aa9fff894774`;
  a duplicate start was rejected; receipt, PR registry and history contained no
  API key.

Gaps:

1. The Console HTTP API is covered end-to-end; the browser UI itself is not
   separately automated.
2. cmux remains a manual operator view; no launcher integration is claimed.
3. The console binds to `127.0.0.1` and has no authentication or hosted mode.
4. Harness 0.11.0 is pre-1.0; upgrades need deliberate re-pinning and schema
   regeneration.
5. Cost telemetry is elapsed time only; OpenCode exposes no per-run token/cost
   value to this adapter.

## Installation

```bash
cd factory
uv sync --python 3.12
opencode auth list                 # existing OpenCode auth; no key in this package
temporal server start-dev          # or let the launcher start it
uv run python -m agent_factory.launcher up --task task.json
```

Requires Python 3.12+, Git, Temporal CLI, OpenCode with an authenticated paid model,
and an origin repository the worker may push `factory/<task_id>` to.

Optional harness stack: `uv sync --extra harness` once, then
`uv run --extra harness python -m agent_factory.launcher up --harness`. See
[HARNESS.md](HARNESS.md) for console operation, logs and troubleshooting.

Violation check: the released wheel's base dependencies do not include
`temporal-agent-harness`; it is an optional extra.

Built from the verified commit `c51e1a3`:

- `agent_factory-0.1.0-py3-none-any.whl` SHA-256
  `0f66ba7f9e582f95e2e0dfcf63817df71d472eddbf6d238249dcbbd5c86db215`
- `agent_factory-0.1.0.tar.gz` SHA-256
  `dc2a4d7002c8a1b842eb0c16e040c57e4abfdee63a11af7cdefbbd509179b2a6`


## Release record

Merged in the required order; no check was bypassed:

| PR | Scope | Merge commit |
|---|---|---|
| #4 | OpenFlowKit / Harness² | `1382139dba080ef9fc32742ebc22796b8bd3c651` |
| #5 | Document maintenance contract | `269868329e638dad7e75dd178d982dd56b89ec0d` |
| #6 | Factory V1 + Temporal Agent Harness | `54d238fcf5fb96f13136d941efa0d4a058ae91ac` |
| #3 | Claude hooks, separate acceptance | `3443f2f8deded47b7b58ade17b495d265dcc5ee4` |

Hosted checks passed for every PR after the billing restoration: `test`,
`openflowkit` and `factory`. The factory job installs the `harness` extra and
runs the offline suite on Ubuntu with the Temporal CLI.

Release artifacts are attached to the `v0.8.2` GitHub Release with
`SHA256SUMS.txt`. The factory wheel was built from the PR #6 code; it does not
include the Harness extra or a model provider dependency.

Temporal Cloud `alpha-dev.n3kw9` was used for one dev smoke workflow. The API key
stays outside the repository; no production deployment was performed. A real
`gh` PR still requires an authorized sandbox repository.

Remaining P1/P2 items: cmux automation, cost/token telemetry beyond elapsed
time, full browser UI automation, xPlan write-back, GitLab skills registry and
50–100 worker scale. None blocks the 0.8.2 source release.

## Rollback

The package is optional and creates no service. To roll back:

1. Stop `agent_factory.launcher` (or the worker) and any launcher-started
   `temporal server start-dev`.
2. Remove `FACTORY_WORK_ROOT` to discard clones/worktrees. Keep `FACTORY_STATE_DIR`
   for receipts and `prs.json`.
3. Delete `factory/` from the checkout or check out the previous release tag. No
   plugin manifest, hook, skill or wiki migration has to be undone.
4. Close any factory PR whose branch is no longer wanted; branches are
   `factory/<task_id>` and are never force-pushed by the factory.

## Remote pilot (2026-11-25)

Deployment source for the pilot is `4a7d018`. Railway hosts the lightweight control plane (`agent-factory-runtime` and
`agent-factory-harness`, private, no public domains); the external compute host
polls only `bsc-batch`. Temporal Cloud `alpha-dev.n3kw9` remains the execution
backend. The pilot passed paid remote coding with independent review, telemetry,
a real BSC 0029 read-only batch, worker restart and Mac-independent execution.
ITSPlan binding is blocked by API authorization (401); full BSC canary #2 is
blocked on owner/dependency items. Private IDs and credentials are not in this
repository. See roadmap §32 and [HANDOFF.md](HANDOFF.md).
