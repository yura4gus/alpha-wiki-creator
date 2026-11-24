# Remote acceptance

One executable gate runner for the remote factory deployment:

```bash
cd factory
FACTORY_REMOTE_ACCEPTANCE=1 uv run python tests/acceptance_remote.py --list-gates
```

The runner is read-only except for the explicitly authorized `task`,
`independence`, `restart` and `bsc` gates. It never powers off the Mac, never
prints a secret, never writes to a host outside the configured acceptance
paths, and never runs a production task unless the operator supplies the
matching allow flag.

## Gates

| Gate | Pass assertions | Evidence fields |
|---|---|---|
| `preflight` | Temporal target configured, non-loopback and TLS; API key present; namespace readable and equal to config; queues non-empty | target/namespace SHA-256, TLS, API-key-present, queue names, min pollers |
| `services` | Every configured systemd service is `active`/`running`; every queue has at least `FACTORY_ACCEPTANCE_MIN_POLLERS` workflow pollers; optional identity requirement matches; no poller identity contains a local Mac marker | service state/enabled/PID, workflow/activity poller counts, hashed poller identities, host load/memory/disk |
| `resources` | Every service has a live PID; RSS <= `FACTORY_ACCEPTANCE_MAX_RSS_MB`; CPU <= `FACTORY_ACCEPTANCE_MAX_CPU_PERCENT`; host memory is readable | per-service RSS MB, CPU percent, elapsed seconds; host load1, available memory, free disk; caps |
| `task` | One real OpenCode task reaches `PR_OPEN`; local tests passed; independent review returned `APPROVE` with both hashes; approval is recorded; exactly one PR; exactly two `Factory-Step` trailers; reviewed diff hash matches the pushed branch; receipt validates | task/workflow/run id, base/head SHA, review verdict/reviewer/hashes, approver, receipt digest and entries, PR count, elapsed seconds, before/after RSS/CPU samples |
| `readback` | Fresh client sees `COMPLETED`/`PR_OPEN`; run id unchanged; receipt bytes stable across two reads; digest matches result; exactly one receipt file; required entries present; no failure entry; diff/trailer/PR checks repeat independently; no private value appears in receipt or PR registry | run id, state, receipt digest/SHA-256/size, entry keys, PR count, recomputed diff hash, trailer count, telemetry presence |
| `independence` | Target queue has remote-only pollers before and after; two-step task starts; the Mac client object is dropped for `FACTORY_ACCEPTANCE_DETACH_SECONDS`; reconnect sees progress; history contains events and an `ActivityTaskStarted` after detachment; receipt reaches `PR_OPEN` | detached seconds, reconnect state, events after detach, activity starts after detach, receipt digest, hashed pollers before/after |
| `restart` | Isolated `bsc-batch` worker restarted during the slow unit; poller identity changes and returns; `BATCH_SUCCESS`; unit `u0` is `REUSED` with `metrics.reused=true`; unit `u1` completes; `effects.log` is exactly `u0,u1`; outputs and DQ validate; run id unchanged | job/workflow/run id, hashed restart command, hashed pollers before/after, effects, unit statuses, metrics, DQ status, receipt digest/SHA-256 |
| `bsc` | Real manifest reaches `BATCH_SUCCESS`; at least one unit; all units complete/reuse; DQ is `PASS`; DQ report has the configured read-only evidence (`mode=read_only`, `writes=0` by default); DQ report hash and every declared output hash read back from the workspace; manifest/script hashes match; one receipt | job/workflow/run id, source/job manifest hash, script hash, unit statuses, DQ status/report hash/selected fields, per-output readback booleans, receipt digest, metrics |

A gate is `PASS` only when every assertion is true. A missing prerequisite is
`BLOCKED`; it is never treated as a pass. The report result is `FAIL` if any
gate failed, `BLOCKED` if any gate was blocked or skipped, otherwise `PASS`.

## Environment

Private host details stay in the invoking shell or a private config file. The
runner stores only SHA-256 fingerprints. All names are read from the
environment; no value is copied into this repository.

| Variable | Used by | Meaning |
|---|---|---|
| `FACTORY_REMOTE_ACCEPTANCE=1` | all | Explicit live-run gate |
| `FACTORY_ACCEPTANCE_REPORT` | all | Evidence path; default `$FACTORY_STATE_DIR/acceptance/remote-<run>.json`, mode 0600 |
| `FACTORY_ACCEPTANCE_QUEUES` | preflight/services | Default `factory-code,factory-coordinator,bsc-batch` |
| `FACTORY_ACCEPTANCE_MIN_POLLERS` | services | Minimum workflow pollers per queue (default 1) |
| `FACTORY_ACCEPTANCE_POLLER_REQUIREMENTS` | services | JSON `{queue: identity-substring}`; substring is never stored |
| `FACTORY_ACCEPTANCE_REMOTE_SSH` | services/task/readback/independence/restart/bsc | SSH alias for the compute host |
| `FACTORY_ACCEPTANCE_SERVICES` | services/resources | Comma list of systemd units to check |
| `FACTORY_ACCEPTANCE_HEALTH_CMD` | services/resources | Optional remote command returning the health JSON instead of `systemctl`/`ps` |
| `FACTORY_ACCEPTANCE_REMOTE_STATE_DIR` | task/readback/independence/restart/bsc | Durable state directory on the worker host |
| `FACTORY_ACCEPTANCE_REMOTE_WORK_DIR` | restart/bsc | Ephemeral work directory for acceptance fixtures |
| `FACTORY_ACCEPTANCE_REMOTE_FACTORY_DIR` / `_PYTHON` / `_ENV_FILE` | restart/bsc | Deployed checkout, interpreter and private env file used for remote submissions |
| `FACTORY_ACCEPTANCE_ORIGIN` | task/readback/independence | Scratch Git origin reachable from the worker |
| `FACTORY_ACCEPTANCE_ORIGIN_SCRATCH=1` | task/independence | Authorizes pushing unique `acceptance/<run>-*` branches |
| `FACTORY_ACCEPTANCE_BASE_REF` | task/independence | Base branch in the scratch origin (default `main`) |
| `FACTORY_ACCEPTANCE_TASK_QUEUE` | task/independence | Coding queue (default `factory-code`) |
| `FACTORY_ACCEPTANCE_BATCH_QUEUE` | restart/bsc | Batch queue (default `bsc-batch`) |
| `FACTORY_ACCEPTANCE_REVIEW_MODEL` | task | Paid review model |
| `FACTORY_ACCEPTANCE_ALLOW_PAID=1` | task | Explicit paid-model authorization |
| `FACTORY_ACCEPTANCE_APPROVER` | task/readback | Identity recorded in the approval entry |
| `FACTORY_ACCEPTANCE_TIMEOUT` | task/restart/bsc | Workflow wait budget in seconds (default 900) |
| `FACTORY_ACCEPTANCE_DETACH_SECONDS` | independence | Time with no Mac client connected (default 25) |
| `FACTORY_ACCEPTANCE_INDEPENDENCE_SLEEP` | independence | Slow second agent step (default 35) |
| `FACTORY_ACCEPTANCE_RESTART_CMD` | restart | Remote command that restarts only the isolated batch worker |
| `FACTORY_ACCEPTANCE_ALLOW_RESTART=1` | restart | Explicit destructive authorization |
| `FACTORY_ACCEPTANCE_RESTART_SLEEP` | restart | Slow-unit sleep; must exceed service stop + heartbeat (default 45) |
| `FACTORY_ACCEPTANCE_BSC_MANIFEST` | bsc | Absolute remote path to the frozen real BSC manifest |
| `FACTORY_ACCEPTANCE_ALLOW_BSC=1` | bsc | Explicit live BSC-batch authorization |
| `FACTORY_ACCEPTANCE_BSC_DQ_EXPECT` | bsc | JSON expected DQ report fields (default `{"mode":"read_only","writes":0}`) |
| `FACTORY_ACCEPTANCE_BSC_REUSE_JOB` | bsc | Read an existing job id instead of creating a unique `bsc-acc-<run>` copy |
| `FACTORY_ACCEPTANCE_MAX_RSS_MB` / `_MAX_CPU_PERCENT` | resources | Service caps (default 4096 MB / 200%) |
| `FACTORY_ACCEPTANCE_REQUIRE_ACTIVITY_POLLERS=1` | services/restart | Require activity pollers as well as workflow pollers |
| `FACTORY_ACCEPTANCE_REQUIRE_TELEMETRY=1` | readback | Require the A4 telemetry schema in the receipt |
| `FACTORY_ACCEPTANCE_TASK_ID` | readback | Standalone re-read when the `task` gate did not run in this invocation |
| `FACTORY_ACCEPTANCE_SHOW_TARGETS=1` | all | Put raw targets in the private report; still never secrets |

`FACTORY_ACCEPTANCE_HEALTH_CMD` contract (for Docker or non-systemd hosts):

```json
{
  "services": {
    "<unit>": {"state": "running", "pid": 123, "rss_kb": 102400,
               "cpu_percent": 1.5, "elapsed_seconds": 3600}
  },
  "host": {"load1": 0.5, "mem_available_mb": 2048, "disk_free_mb": 4096}
}
```

## Run order

Run the cheap read-only gates first. Stop at the first failure and keep its
report.

```bash
# 1. auth and deployment surface
... python tests/acceptance_remote.py --gate preflight --gate services --gate resources

# 2. real coding task, then independent receipt readback
... python tests/acceptance_remote.py --gate task --gate readback

# 3. detached-client independence
... python tests/acceptance_remote.py --gate independence

# 4. controlled destructive window
... python tests/acceptance_remote.py --gate restart

# 5. real read-only BSC batch
... python tests/acceptance_remote.py --gate bsc
```

The restart command must target an **isolated** acceptance/batch worker, not a
shared production worker. The gate hashes the command and verifies that the
queue poller identity actually changed.

## Independence scope

The Mac is not powered off. The gate drops its only local Temporal client
reference (the Python SDK exposes no `Client.close()`), waits without polling,
reconnects with a new client, and reads the workflow history. A pass requires
an `ActivityTaskStarted` event timestamp after the detach point plus
remote-only poller identities. This proves the remote worker continued; it
does not claim a physical network partition test.

## BSC manifest contract

`FACTORY_ACCEPTANCE_BSC_MANIFEST` points at a frozen A2 manifest on the worker
host. The runner copies the manifest with a unique `job_id`, recomputes
`manifest_hash`, submits it through the deployed A2 CLI, and reads the remote
receipt. The manifest must:

- target `bsc-batch` (or `FACTORY_ACCEPTANCE_BATCH_QUEUE`);
- declare at least one unit and outputs;
- declare a `dq_contract` whose JSON report includes the fields in
  `FACTORY_ACCEPTANCE_BSC_DQ_EXPECT` (default `mode=read_only`, `writes=0`);
- run only read-only chain access. A3 owns the scanner and the real RPC
  credentials; they stay outside this repository.

## Evidence and exit codes

The JSON report schema is `agent-factory.remote-acceptance/1`. It contains the
source branch/SHA, hashed connection and host targets, the gate plan, every
assertion with expected/actual/pass, gate evidence, summary counts and a
redaction count. The report is written mode 0600 outside the repository unless
`FACTORY_ACCEPTANCE_ALLOW_REPO_REPORT=1` is set.

Exit codes: `0` PASS, `1` FAIL, `2` BLOCKED or misuse. A blocked gate must be
reported as blocked; do not convert it into a pass.

## Canonical release gates (A6 scope update, 2026-11-25)

The eight collection gates above answer "can the remote host run work?" The
release decision uses these sixteen canonical gate IDs. `tests/acceptance_remote.py`
supplies the live SSH/systemd observations; the A6/A4/A3-specific observations
come from the private evidence bundle evaluated by
`python -m agent_factory.acceptance`.

| Canonical gate | Owner | Satisfied by |
|---|---|---|
| `RAILWAY_FACTORY_DEPLOYED` | A6 | Private bundle: project/environment/service IDs, deployment SHA equal to the tested commit, healthy deployment, private access |
| `RAILWAY_OPENCODE_READY` | A6/A4 | Private bundle: one remote OpenCode instance, authenticated, private endpoint, no public domain |
| `TEMPORAL_POLLERS_ACTIVE` | A6/A2 | `preflight` + `services`: workflow and activity pollers on `factory-code`, `factory-coordinator`, `bsc-batch` |
| `ITSPLAN_TASK_BINDING_PASS` | A4 | Private bundle: bound issue readback, dry-run planner output, zero attempted/applied mutations, identical replay |
| `REMOTE_CODING_E2E_PASS` | A4 | `task` + `readback`: real OpenCode task, tests, independent review, receipt, one PR |
| `EXTERNAL_BATCH_WORKER_PASS` | A2/A1 | `bsc` plus bundle: `bsc-batch` worker on external compute, no Railway batch service, <= 1 MiB Railway data |
| `RESTART_RECOVERY_PASS` | A6/A2 | `restart`: Railway service and external worker restart, replay passes, checkpoint reused, no duplicate effects |
| `MAC_INDEPENDENCE_PASS` | A6/QA | `independence`: local processes/ports stopped, remote history advances after detach |
| `REMOTE_FACTORY_READY` | A6 | `services` + `resources` + bundle: factory worker, coordinator and private console online, durable state |
| `REMOTE_OPENCODE_PASS` | A4 | `task` or bundle: one real remote OpenCode call, paid model, private access |
| `DETERMINISTIC_BATCH_PASS` | A2 | `bsc` repeated over the same manifest: identical checkpoint digest and outputs |
| `BSC_0029_CANARY_PASS` | A2 | `bsc` with job id `bsc-0029`, `BATCH_SUCCESS`, DQ `PASS`, external compute |
| `CHECKPOINT_RESUME_PASS` | A2 | `restart`: killed unit, one execution, checkpoint reused, outputs match |
| `DQ_READBACK_PASS` | A2 | `bsc`: DQ `PASS`, report hash read back, expected JSON equals reported JSON |
| `ZERO_DUPLICATE_EFFECTS` | QA | `readback` + `restart` counters plus bundle: zero duplicate commits, PRs, branches, units, reports, receipts, notifications |
| `TELEMETRY_VERIFIED` | A3 | `readback` with `FACTORY_ACCEPTANCE_REQUIRE_TELEMETRY=1` plus bundle: agent and review runs have numeric cost, input/output tokens and measured duration |

The canonical evaluator exits `0` only when all sixteen gates are `PASS`; a
missing observation is `BLOCKED`, and a contradiction is `FAIL`:

```bash
uv run python -m agent_factory.acceptance \
  --bundle "$FACTORY_ACCEPTANCE_EVIDENCE" --format markdown
```

The bundle schema is `agent-factory.remote-acceptance-bundle/1`; all private
values stay in the bundle outside the repository. The evaluator rejects
secret-shaped fields, hashes declared artifacts, and never trusts a self-reported
`PASS`. The live report remains an artifact referenced by the bundle.

Bundle envelope:

```json
{
  "schema": "agent-factory.remote-acceptance-bundle/1",
  "generated_at": "<ISO-8601>",
  "commit": "<40-hex tested source commit>",
  "environment": "remote",
  "artifacts": [{"id": "<name>", "path": "<relative-or-absolute>",
                  "sha256": "<64-hex>"}],
  "checks": {"<gate id>": {"artifacts": ["<name>"], "...": "..."}}
}
```

Required fields per gate (add `artifacts` to bind a private file):

| Gate | `checks` fields |
|---|---|
| `RAILWAY_FACTORY_DEPLOYED` | `project_id`, `environment_id`, `services` (role→id), `deployment{id,sha,status}`, `health{status,checked_at}`, `git_sha`, `public_exposure`, `access` |
| `RAILWAY_OPENCODE_READY` | `instances[]` (exactly one: `id,placement,status`), `auth{provider,model,authenticated}`, `access{method,public_domain}`, `health{status,checked_at}` |
| `TEMPORAL_POLLERS_ACTIVE` | `target`, `namespace`, `observed_at`, `queues{factory-code,factory-coordinator,bsc-batch}` each with `workflow.poller_count`, `activity.poller_count`, `identities`; optional `placement` |
| `ITSPLAN_TASK_BINDING_PASS` | `issue{id,identifier,updatedAt,columnId,source_revision,observed_revision}`, `binding{issue,run_id,worker,columns}`, `planner{decision,mode,proposed_column_id}`, `write_audit{writes_attempted,writes_applied,methods,paths}`, `replay{identical,decision}` |
| `REMOTE_CODING_E2E_PASS` | `task_id`, `workflow_id`, `workflow_status`, `execution{placement,local_process}`, `agent{runner,model,steps,session_id}`, `tests{passed}`, `review{verdict,independent,session_id,diff_sha256,prompt_sha256}`, `checkpoints[]`, `pr{number,head_sha}`, `receipt{sha256}`, `duplicates{commits,prs}` |
| `EXTERNAL_BATCH_WORKER_PASS` | `job_id`, `workflow_id`, `task_queue`, `status`, `worker{placement,identity,railway_service_id}`, `units[]`, `data_plane{bulk_data_on_railway,railway_bytes,durable_state_placement}`, `receipt{sha256}` |
| `RESTART_RECOVERY_PASS` | `railway_restart{service_id,restart_count,observed_at}`, `external_restart{worker_identity,restart_count,observed_at}`, `recovery{resumed,replay,terminal_state,checkpoints_reused}`, `duplicates{commits,prs,batch_units,side_effects}`, `continuity{before_sha,after_sha}` |
| `MAC_INDEPENDENCE_PASS` | `local{stopped_at,processes[],ports[],remote_tunnels_required}`, `remote{continued,observed_after_local_stop,workflow_id,terminal_state}` |
| `REMOTE_FACTORY_READY` | `release_sha`, `services{factory_worker,coordinator,console}`, `state{durable,receipts_readable}` |
| `REMOTE_OPENCODE_PASS` | `instance{placement}`, `auth{authenticated,model}`, `real_call{exit_code,session_id,text_sha256}`, `access{public_domain}` |
| `DETERMINISTIC_BATCH_PASS` | `job_id`, `manifest_hash`, `script_sha`, `runs[]` with identical `checkpoint_digest`/`outputs`, `checkpoint_fields`, `deterministic` |
| `BSC_0029_CANARY_PASS` | `job_id` = `bsc-0029`, `status`, `worker{placement}`, `dq{status}`, `outputs`, `receipt{sha256}`, `canary` |
| `CHECKPOINT_RESUME_PASS` | `job_id`, `unit_id`, `killed`, `worker_restart{observed}`, `resume{checkpoint_reused,unit_rerun,outputs_match}`, `counts{unit_executions}`, `receipt{sha256}` |
| `DQ_READBACK_PASS` | `job_id`, `dq{status,exit_code,expected_exit,report_sha256,expected_json,reported_json}`, `readback{independent,matches_expected,report_hash_matches}` |
| `ZERO_DUPLICATE_EFFECTS` | `counts` (commits, PRs, branches, batch units, DQ reports, receipts, notifications), `scope`, `evidence`, `independent` |
| `TELEMETRY_VERIFIED` | `schema`, `source`, `runs[]` with `stage` in `agent|review`, numeric `cost`/tokens/duration, `receipt{contains_telemetry,metrics_sha256}` |

### A6 Railway control plane boundary

Railway is the control plane, not the BSC data plane. A6 evidence must show:

- project, environment and service IDs plus a deployment SHA equal to the tested
  source commit;
- one remotely authenticated OpenCode instance on a private endpoint;
- `factory-code` and `factory-coordinator` pollers on Railway and `bsc-batch`
  pollers on external compute;
- no bulk BSC data in Railway (<= 1 MiB) and durable checkpoints on external
  storage;
- restart of both the Railway service and the external worker with no duplicate
  commit, PR, unit, DQ report, receipt or notification.

Until that evidence exists, the A6 gates stay `BLOCKED`; a running Railway
project with no deployment is not a pass.

## Known Wave 1 boundaries

- A2 `agent_factory.batch_worker` must be deployed before `restart` and `bsc`
  can run. Until then they are `BLOCKED`.
- A3 is the owner of the real read-only BSC manifest and DQ readback. This
  runner does not invent a BSC scanner.
- A4 telemetry must be wired into the receipt before
  `FACTORY_ACCEPTANCE_REQUIRE_TELEMETRY=1` can pass.
- The remote host remains an A1 deployment concern. No address, key, hostname,
  origin or systemd unit path with a private value is stored here.
- A6 Railway control-plane gates need a real deployment, one authenticated
  OpenCode instance and the three queue pollers. An empty project skeleton is
  `BLOCKED`, not ready.
- The current baseline is in
  [ACCEPTANCE-BASELINE-2026-11-25.md](ACCEPTANCE-BASELINE-2026-11-25.md);
  merge order is in [ACCEPTANCE-PR-PLAN.md](ACCEPTANCE-PR-PLAN.md).
