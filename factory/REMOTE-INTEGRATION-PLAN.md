# Remote factory integration and release plan

Status: **WAVE 1 PREPARED**. No production merge, deploy or v0.8.2 change has
been made. Base is `v0.8.2` / `dc9f768`.

This is the A5 execution note for the acceptance runner and its Wave 1
blockers. It is not a second cross-track gate definition; when a parallel
`factory/ACCEPTANCE-PR-PLAN.md` is present, that file owns the canonical
sixteen-gate release decision.

## Tracks and ownership

| Track | Branch | Scope | A5 boundary |
|---|---|---|---|
| A1 | `codex/factory-remote-deploy` | Remote compute deployment, systemd batch unit, environment template, rollback evidence | Read only; A5 does not edit deployment files |
| A2 | `codex/factory-batch-runtime` | `BatchWorkflow`, manifest freeze, checkpoints, DQ, `batch_worker` | Read only; A5 binds acceptance to the public CLI/receipt |
| A3 | Private BSC track (branch/repo supplied by controller) | Real read-only BSC manifest, scanner, DQ report | A5 consumes the manifest; no private chain or RPC detail enters this repo |
| A4 | `codex/factory-remote-telemetry` | OpenCode JSON telemetry parser and receipt wiring | A5 asserts only the public telemetry schema |
| A5 | `codex/factory-remote-qa` | Acceptance runner, offline contract tests, evidence, merge verification | This document and `tests/acceptance_remote.py` |

## Merge order

Do not reopen `v0.8.2`. Create a new integration branch from `main` at
`dc9f768` and merge one reviewed PR per track:

1. **A2 batch runtime** - the deployment unit cannot start until
   `agent_factory.batch_worker` exists. Run factory offline + new batch tests.
2. **A4 reviewer/telemetry** - resolve any overlap in `reviewer.py` and
   `activities.py`; run the review/telemetry suites.
3. **A1 deployment** - after A2, the release install and unit are valid.
   A1 must first remove private host facts from public docs (see blockers).
4. **A3 private BSC** - keep private manifests/credentials out of this repo;
   merge only generic integration code, if any.
5. **A5 acceptance tooling** - unit tests/docs can merge earlier, but the final
   evidence commit follows the successful Wave 2 run.

Each PR: review, hosted `test`/`openflowkit`/`factory` checks green, no bypass.
The integration branch stays unmerged until the full acceptance report passes.

## CI and local checks

Offline before every merge:

```bash
# repository
uv run pytest
# factory, including the new acceptance contract tests
cd factory && uv run --extra harness pytest
```

Live gates are never run in hosted CI; they need the deployed host, Cloud
credential and paid model. The acceptance runner itself is imported by the
offline suite, so import/schema regressions fail fast.

Baseline recorded before A5 edits (2026-11-24/25):

| Check | Result |
|---|---|
| Repository suite | 411 passed, 85.58 s |
| Factory offline suite | 80 passed, 15 skipped, 88.25 s |
| Launcher live (local Temporal, no model) | 1 passed |
| Harness stack live (local Temporal + console, no model) | 1 passed |
| Temporal Cloud smoke (fake agent) | 1 passed, 8.61 s |
| New acceptance contract tests | 16 passed, 2 skipped on the base branch (A2 import test and the opt-in live test) |
| A5 full factory suite, foreign evaluator excluded | 95 passed, 17 skipped, 1 deselected; the deselected pre-existing concurrency timing test fails under host load 49 and is unrelated to A5 |

The factory baseline was measured in a clean copy because this worktree's
`.git` file points into a macOS TCC-protected `~/Documents` path; the code and
offline tests themselves pass. This is a local environment issue, not a
release result.

Read-only Wave 1 probe against the existing Cloud namespace: `factory-code` and
`factory-coordinator` each had two workflow and two activity pollers, while
`bsc-batch` had none; the configured batch unit was `inactive`/`disabled`.
This matches the A2 deployment blocker and is not a pass.

## Deploy sequence after merge

1. Build and verify the new factory artifact from the integrated commit; keep
   the existing `v0.8.2` artifacts untouched.
2. Deploy the Railway/control-plane services (A1/A6) on `factory-code` and
   `factory-coordinator`.
3. Install the new immutable release on the compute host, switch
   `current`/`current-venv` together, install the batch unit, then enable it
   only after `agent_factory.batch_worker` exists.
4. Confirm `bsc-batch`, `factory-code`, `factory-coordinator` pollers and the
   configured systemd service.
5. Run acceptance in this order: `preflight`, `services`, `resources`, `task`,
   `readback`, `independence`, `restart`, `bsc`.
6. Attach the sanitized JSON report to the integration PR. Do not attach raw
   host output, credentials or private manifests.

Proposed release: a new minor tag after acceptance (for example `v0.9.0`), not
a re-tag or edit of `v0.8.2`.

## Rollback

- Disable/stop the batch unit; leave state, receipts and other host workloads
  untouched.
- Switch `current` and `current-venv` back together to the prior release.
- Roll back the control-plane services to the prior image.
- Keep the acceptance report and receipts as evidence; do not delete durable
  state.
- Close any acceptance branches/PRs created by the gates. Branches are
  `factory/<task-id>` and `acceptance/<run>-*` on the scratch origin.

## Blockers and defects to resolve before Wave 2

| ID | Severity | Finding | Required action |
|---|---|---|---|
| B1 | P0 (public repo) | A1 public docs/evidence currently contain private host identity, address and capacity facts. A5 must not edit A1 code. | A1 removes or replaces them with environment placeholders before merge. |
| B2 | P1 | A1 systemd unit sets `FACTORY_TASK_QUEUE=bsc-batch`; A2 reads `FACTORY_BATCH_TASK_QUEUE` with the same default. | Align the variable in A1/A2 before changing the queue. |
| B3 | P1 | A2 batch worker is not deployed yet; `bsc-batch` has no pollers. | Deploy the A2 release and enable the unit. |
| B4 | P1 | A3 real read-only BSC manifest and DQ report are not supplied; A5 has no scanner and will not invent one. | Provide the remote manifest and DQ contract fields. |
| B5 | P1 | A4 telemetry parser is not yet proven wired into the receipt. | Wire and test receipt telemetry; then set `FACTORY_ACCEPTANCE_REQUIRE_TELEMETRY=1`. |
| B6 | P1 | Control-plane placement moved to Railway (A6); A5's `services` gate only checks the configured compute host. | Supply the control-plane health command or rely on Cloud pollers for `factory-code`/`factory-coordinator`. |
| B7 | P2 | The restart gate needs an isolated worker command; restarting a shared worker is not acceptable. | Provide `FACTORY_ACCEPTANCE_RESTART_CMD` for the acceptance/batch unit only. |
| B8 | P2 | Acceptance needs a scratch origin reachable by the remote worker. | Provide `FACTORY_ACCEPTANCE_ORIGIN` and authorize unique branch pushes. |

No pass result is claimed for B3-B5 until the real gates run and return
evidence.
