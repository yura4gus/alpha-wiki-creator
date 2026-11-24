# Remote factory acceptance — PR plan

Status: **plan + baseline only**. No gate is claimed as passing. Private host,
project, environment, service, namespace and origin values stay out of this
repository.

## Scope

This plan coordinates the A1/A2/A3/A4/A5/A6 work with the remote acceptance
gates. It does not reimplement any track:

- A1 supplies the external-compute deployment and batch-worker unit.
- A2 supplies `agent_factory.batch` and `agent_factory.batch_worker`.
- A3 supplies the private read-only BSC manifest, scanner and DQ report; only
  generic integration code may enter this repository.
- A4 supplies OpenCode JSON telemetry and receipt wiring.
- A5 supplies the live SSH/systemd collector, this plan and the acceptance
  tooling.
- A6 supplies the Railway control plane (project, deployment, OpenCode and
  private console).
- Remote coding and ITSPLAN evidence is supplied by its owning track; this plan
  only defines the gate and the evidence shape.

The live SSH/systemd collector remains `tests/acceptance_remote.py`. The
canonical sixteen-gate decision is `agent_factory.acceptance`; it consumes a
private bundle assembled from the track artifacts. Neither layer is allowed to
turn a missing observation into a pass. `REMOTE-INTEGRATION-PLAN.md` is the A5
execution note; this file owns the cross-track gate and merge sequence.

## PR stack

| Order | Branch/PR | Owns | Depends on | Must not change |
|---|---|---|---|---|
| 1 | A2 `codex/factory-batch-runtime` | `factory/src/agent_factory/batch/`, `batch_worker.py`, batch tests, batch docs | baseline `dc9f768` | coding workflow, reviewer, Railway config |
| 2 | A4 `codex/factory-remote-telemetry` | `telemetry.py`, reviewer telemetry, telemetry tests | baseline | batch runtime, Railway config |
| 3 | A1 `codex/factory-remote-deploy` | external-host systemd recipe and sanitized env template | A2 for the batch unit | Railway control-plane files |
| 4 | A3 private BSC track | read-only manifest, scanner and DQ report; generic integration only | A2/A1 placement | private scanner, RPC credentials, private manifests |
| 5 | A6 `codex/factory-railway-deploy` | Railway control-plane recipe/evidence, private service wiring, remote OpenCode | A2/A4 code in the deployed release | batch algorithm, reviewer logic, A1 external unit |
| 6 | A5 `codex/factory-remote-qa` | acceptance gates, evaluator, tests, PR plan, baseline | A2/A4 for full suite; A1/A3/A6 for evidence | any A1/A2/A3/A4/A6 implementation |

The A5 branch can merge independently, but its final gate run happens only after
the implementation branches are in the release candidate. A gate is never
promoted by editing the evaluator.

## Merge order and conflicts

1. Merge A2 and A4 first. They add disjoint modules; A4 touches `reviewer.py`.
2. Merge A1 after A2 so the external batch unit can start. A1 must remove private
   host facts from public docs before merge.
3. Merge A3 generic integration only; private manifests, scanner code and RPC
   credentials stay outside this repository.
4. Merge A6 after the code release is deployable. A6 must not carry secrets,
   project IDs, host addresses or namespace values in tracked files.
5. Merge A5 last for the release candidate, or earlier if the parent wants the
   evaluator available while implementation lands. Rebase once after A2/A4.
6. One writer per shared file per wave. Shared files are `factory/README.md`,
   `factory/RELEASE.md`, `factory/REMOTE-ACCEPTANCE.md`,
   `docs/roadmap-execution.md` and this plan; split edits by section and rebase
   before merging.

## Gate ownership and evidence handoff

| Gate | Evidence producer | Evidence form |
|---|---|---|
| `RAILWAY_FACTORY_DEPLOYED` | A6 | Private bundle: IDs, deployment SHA, health, access |
| `RAILWAY_OPENCODE_READY` | A6 | Private bundle: one instance, auth, private access |
| `TEMPORAL_POLLERS_ACTIVE` | A6/A2 | Live `preflight`/`services` report + queue snapshot |
| `ITSPLAN_TASK_BINDING_PASS` | ITSPLAN track | Binding/readback JSON + dry-run planner output + zero-write audit |
| `REMOTE_CODING_E2E_PASS` | remote-coding track | Live `task`/`readback` report + receipt |
| `EXTERNAL_BATCH_WORKER_PASS` | A2/A3/A1 | Live `bsc` report + placement/data evidence |
| `RESTART_RECOVERY_PASS` | A6/A2 | Live `restart` report + both restart observations |
| `MAC_INDEPENDENCE_PASS` | A6/A5 | Live `independence` report + local process/port stop evidence |
| `REMOTE_FACTORY_READY` | A6 | Service/queue/console/state evidence |
| `REMOTE_OPENCODE_PASS` | A6 | One real remote OpenCode call |
| `DETERMINISTIC_BATCH_PASS` | A2 | Two-run checkpoint/output evidence |
| `BSC_0029_CANARY_PASS` | A3/A2 | BSC-0029 canary receipt + DQ |
| `CHECKPOINT_RESUME_PASS` | A2 | Killed-worker resume evidence |
| `DQ_READBACK_PASS` | A3/A2 | DQ report + independent readback |
| `ZERO_DUPLICATE_EFFECTS` | A5 | Coding/batch/restart counters + independent scan |
| `TELEMETRY_VERIFIED` | A4 | Agent and review OpenCode JSON runs + receipt metrics |

The evidence bundle is JSON, schema
`agent-factory.remote-acceptance-bundle/1`, mode `0600`, outside the repository.
Every declared artifact is SHA-256 checked. The evaluator rejects secret-shaped
fields before evaluating any gate.

## Promotion rules

1. Run the offline suite and the acceptance tests first. A failing offline test
   blocks promotion even if a live gate is not selected; record pre-existing
   host-load flakes separately.
2. Run read-only gates before destructive gates. Stop at the first failure and
   keep the private report.
3. All sixteen canonical gates must be `PASS` for remote readiness. A `BLOCKED`
   or `FAIL` gate keeps the release blocked; do not rename it.
4. The A5 reviewer records the bundle SHA-256, the tested source commit, the
   deployment SHA and the exact command in the private evidence record.
5. Public source and the PR description contain only sanitized status. No
   project ID, service ID, environment ID, host, IP, SSH alias, namespace, origin
   URL, API key or token.
6. The parent chooses the release tag only after the canonical report says
   `overall: PASS` and the independent reviewer signs the sanitized summary.

## Rollback

- Stop the Railway deployment and external batch worker; keep durable receipts
  and checkpoints for evidence.
- Remove only the new release; retain the previous release and state directory.
- Close acceptance branches/PRs by name; never force-push a factory branch.
- Do not delete the evidence bundle before the release record is archived.

## Current baseline

See `ACCEPTANCE-BASELINE-2026-11-25.md`. The baseline is `FAIL`: the Railway
project has deployments but no proven source SHA or health, one Temporal queue
still has no pollers, and no remote coding, ITSPLAN, BSC-0029 or telemetry
evidence exists in this worktree. Those are prerequisites, not acceptance
exceptions.
