# Agent Factory V1 — release candidate

Status: **RELEASE-READY, MERGE BLOCKED EXTERNALLY**. Functional acceptance is local
and passed. Hosted checks and the stacked PR merge order are not satisfied; nothing
was deployed and no protected check was bypassed.

Verified code: `2f9a9dd023286df1fa8a5cb6e5181a8826f60b98` on
`codex/agent-factory-v1`, based on `0e99fa8` (PR #5) and `fd73821`.

## Scope

Optional `factory/` package only. No plugin manifest, skill, hook, wiki schema or
production runtime is changed by enabling it. Temporal Core plus the existing
thin CLI adapter remain the executor; the Temporal Agent Harness spike decision in
`spikes/harness/FINDINGS.md` is unchanged.

## Acceptance evidence (2026-11-15, macOS, Temporal 1.8.3, OpenCode 2.1.4)

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

## Merge path and blockers

Required order: PR #4 (OpenFlowKit/Harness²) → PR #5 (document contracts) → Factory
V1 → PR #3 (Claude hooks, separate acceptance).

Observed blockers on 2026-11-15:

1. GitHub Actions jobs for PRs #3, #4, #5 fail in about 2 s before running steps.
   The account billing lock reported in the roadmap is still present. Checks were
   not bypassed; draft PRs remain unmerged.
2. PRs #4 and #5 are draft and unmerged, so Factory V1 stays stacked on
   `codex/openflowkit-document-contract` (`0e99fa8`).
3. No authorized sandbox GitHub repository is configured, so `pr_backend: "gh"` was
   not exercised. The adapter is written and the local registry is tested.
4. cmux exposes no stable CLI here; it remains a manual operator view.

Next actions: restore GitHub Actions billing, run the factory job in
`.github/workflows/plugin-ci.yml`, mark #4/#5 ready, merge in order, then open the
factory PR with the receipt and this document attached. A real `gh` PR requires a
sandbox repository and explicit owner approval.

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
