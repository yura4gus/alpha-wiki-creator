# Agent Factory V1 (Temporal)

Optional package. The Alpha-Wiki plugin stays server-free; this directory has its own
`pyproject.toml` and environment, so no plugin manifest changes.

Authorities stay separate: **Temporal** owns durable execution and retries; **xPlan**
keeps task ownership (read-only dry-run here); **Alpha-Wiki** supplies pinned context
and contracts; **Harness²** and **OpenFlowKit** own their offline experiments and
architecture receipts; **OpenCode/Codex** run unchanged as subprocesses; Git and the
PR adapter supply delivery evidence. The factory reads receipts from the other
authorities and never duplicates their implementations.

## Flow (`workflows.TaskWorkflow`, id `task-<task_id>`)

`pin_snapshot` → `build_context` → `agent_step`×N (one pushed checkpoint commit per
step on `factory/<task_id>`) → `run_tests` → `collect_evidence` → `review` → human
approval (Update `decide`) → `open_pr` → xPlan `reconcile_dry_run` → frozen receipt.

A real task uses the native CLI loop and `--auto` for non-interactive permissions:

```json
{
  "task_id": "fix-calc-1",
  "repo": "/tmp/origin.git",
  "agent_steps": [["opencode", "run", "--auto", "-m", "opencode-go/deepseek-v4.1-flash",
                   "Fix app/calc.py. Only change files under app/. Do not run git commands."]],
  "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
  "owned_paths": ["app"],
  "reviewer": "opencode",
  "review_model": "opencode-go/deepseek-v4.1-flash"
}
```

## One command

```bash
cd factory
uv sync --python 3.12
uv run python -m agent_factory.launcher up --task task.json
uv run python -m agent_factory.launcher status fix-calc-1
uv run python -m agent_factory.launcher receipt fix-calc-1
```

`up` starts `temporal server start-dev` when the configured address is unreachable,
runs the worker in-process, admits the task(s), and prints state, review verdict,
receipt status and measured step/test seconds. The dev server and worktrees stop
with the command; the receipt and pushed branch remain. An existing Temporal server
is reused. Approval waits for an operator unless `--approve-by <name>` explicitly
authorizes automatic approval for that run (recorded in the receipt).

cmux is an optional operator view, not execution authority. Run the same `up`
command inside a cmux workspace and keep `status`/`receipt` in a second pane. No
cmux API or state is required, so a missing or busy cmux never blocks a task.

## One command with the Agent Harness

`--harness` adds the Temporal Agent Harness coordination layer to the same
launcher. It is optional and starts only after Temporal is reachable:

```bash
cd factory
uv sync --python 3.12
uv run --extra harness python -m agent_factory.launcher up --harness
# Console http://localhost:8000 · Temporal UI http://localhost:8233

# follow factory tasks as well
uv run --extra harness python -m agent_factory.launcher up --harness --task task.json
```

It starts the harness session manager/API/console
(`uv run --extra harness temporal-agent-harness dev factory/harness/agents.toml`),
the coordinator worker (`python -m agent_factory.harness.worker`) on
`FACTORY_HARNESS_TASK_QUEUE` (default `factory-coordinator`), and keeps the
existing factory `TaskWorkflow` worker in this process. `--harness-registry`
defaults to `<factory>/harness/agents.toml`; `--harness-port` defaults to `8000`.
Without `--task`, the stack waits for Ctrl-C; `--no-follow` also keeps it up.

Authority does not move with the console:

- `TaskWorkflow` remains the executor and the approval authority. Approval is the
  `decide` Update on `task-<task_id>`; the console reaches it through the
  coordinator's `approve_task` handler. Harness tool approvals are separate and do
  not change factory task state.
- The harness is a coordination/session surface only. It does not run factory
  agent steps, tests, review or PR stages.
- All model calls go through OpenCode. The harness adds no provider SDK, HTTP
  client or credential to this package.
- Ctrl-C stops the console, coordinator and a launcher-started Temporal dev
  server as process groups. Receipts remain in `FACTORY_STATE_DIR`.

Logs are written to `<state_dir>/harness/{harness,coordinator}.log`; the last
stack record is `<state_dir>/harness/stack.json`. See [HARNESS.md](HARNESS.md)
for start/stop, console and CLI operation, reconnect, restart, logs and
troubleshooting.

## Hosted deployment

Control plane (Harness coordinator, Console/API, lightweight coding workers) is
hosted on Railway. The `rx-back` host is external compute for the `bsc-batch`
queue only; see [deploy/README.md](deploy/README.md) for the systemd unit,
limits, state paths and the A2 dependency on `agent_factory.batch_worker`.
`rx-back` must not run the Console, coordinator, `factory-code` worker or an
OpenCode server.

## Recovery and idempotency

- The worker filesystem is **ephemeral**; origin branch `factory/<task_id>` and the
  receipt in `FACTORY_STATE_DIR` are durable.
- A lost worker is detected by heartbeat timeout; the retried `agent_step` rebuilds
  the worktree from the last checkpoint SHA and rewrites the pinned context file.
- A step already pushed is reused, not re-run (`Factory-Step: <task>/<index>` trailer).
- Commits are deterministic (parent, tree, message, base commit date); PRs are looked
  up by head branch; receipts are keyed per step. Repeating an activity adds nothing.
- An unknown or missing review verdict is `BLOCKED_REVIEW`; only `APPROVE` can reach
  the approval/PR stage.

## Review through OpenCode

All model calls go through the OpenCode CLI; there is no provider HTTP client or API
key in this package. The reviewer runs in an empty scratch directory and sees only
the prompt (contract, test result, diff, optional evidence refs). OpenCode's own auth
store is used.

- Default: `opencode-go/deepseek-v4.1-flash` (paid). A model ending in `-free`
  requires `allow_free_review: true`; do not enable it for private code.
- Real `gh` PRs require `reviewer: "opencode"`. Stub review is for local dry-runs.
- Failure, quota error, nonzero exit, unparseable reply, `APPROVE` without findings,
  empty diff or failed tests never approve. The receipt records `diff_sha256` and
  `prompt_sha256` so the reviewed bytes are reproducible.

## Read-only integration receipts

Set optional paths in the task spec; `collect_evidence` only reads the JSON:

```json
{
  "harness2_evaluation": "/path/to/harness2/evaluation.json",
  "openflowkit_report": "/path/to/openflowkit/report.json"
}
```

Expected producers are the existing `scripts/harness2_alpha_wiki.py` replay and
`scripts/openflowkit_pilot.py` report. The receipt records source hashes, result,
pinned Git SHA/model hash and stable evidence refs. `PASS`, `DRIFT`, `UNKNOWN`,
`MISSING` and `INVALID` stay distinct; invalid receipts are never trusted. Evidence
refs flow into the independent review prompt and the read-only xPlan planner.

xPlan remains read-only. `reconcile_dry_run` calls `tools.xplan_dry_run` and records
`NO_CHANGE`, `PROPOSE`, `REWORK`, `SKIP_CONFLICT`, `STALE_SHA` or `NEEDS_OWNER`.
No automatic transition or write path exists.

## Config (env)

`FACTORY_HOME`, `FACTORY_WORK_ROOT` (ephemeral), `FACTORY_STATE_DIR` (durable),
`FACTORY_TEMPORAL_ADDRESS`, `FACTORY_TASK_QUEUE`, `FACTORY_PLUGIN_ROOT`,
`FACTORY_OPENCODE_BIN` (default `opencode`), `FACTORY_MAX_ACTIVITIES`,
`FACTORY_FAULTS` (test-only fault injection). `env_passthrough` lists variable
**names**; values stay in the worker environment and never enter workflow history.

The harness layer additionally reads `FACTORY_HARNESS_TASK_QUEUE` (default
`factory-coordinator`) and the standard harness/Temporal connection settings:
`TEMPORAL_ADDRESS` (set by the launcher to the same address as the factory),
`TEMPORAL_NAMESPACE`, `TEMPORAL_TLS`, `TEMPORAL_API_KEY` (inherited when set).
The factory worker still uses `FACTORY_TEMPORAL_ADDRESS`.

### Temporal Cloud

`connection.py` loads the SDK profile whenever `TEMPORAL_CONFIG_FILE`,
`TEMPORAL_PROFILE`, `TEMPORAL_NAMESPACE` or `TEMPORAL_API_KEY` is present. For
the dev namespace verified here:

```bash
set -a; . ~/.config/temporal-mcp/.env; set +a   # TEMPORAL_API_KEY, mode 600
export TEMPORAL_ADDRESS=alpha-dev.n3kw9.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=alpha-dev.n3kw9
export TEMPORAL_TLS=true
uv run python -m agent_factory.launcher up --address "$TEMPORAL_ADDRESS" --task task.json
```

An explicit or `FACTORY_TEMPORAL_ADDRESS` loopback target stays plaintext even
when a Cloud key is exported: local tests and dev servers are not converted to
TLS. A non-loopback target keeps the Cloud namespace/key/TLS.

## Tests

```bash
uv run --extra harness pytest                   # offline suite; live tests skipped
FACTORY_LIVE_CLI=1 uv run pytest tests/test_live_cli.py
FACTORY_LIVE_REVIEW=1 uv run pytest tests/test_review_live.py
FACTORY_LIVE_LAUNCHER=1 uv run pytest tests/test_launcher_e2e.py
FACTORY_LIVE_HARNESS_STACK=1 uv run pytest tests/test_launcher_e2e.py
FACTORY_LIVE_HARNESS=1 uv run --extra harness pytest tests/test_harness_live.py
FACTORY_LIVE_CLOUD=1 uv run pytest tests/test_cloud_connection.py
```

The live CLI suite proves real OpenCode edits, tests, two checkpoint commits,
checkpoint recovery after a killed worker, cancellation with process-group kill,
one-model-call reuse after a post-push failure, and three concurrent isolated tasks.
The live review suite sends only synthetic diffs to the paid model and checks scope
rejection plus receipt provenance. The launcher suite proves one-command startup,
the approval update and receipt readback after the server stops. The harness
stack test starts Temporal, the console and both workers, checks `/api/agents`
and task-queue pollers, then stops the process groups; it skips with the exact
preflight reason when the registry, extra or coordinator is absent. The harness
live test submits three real OpenCode tasks through `FactoryCoordinatorAgent`,
approves one through `TaskWorkflow.decide`, restarts both workers and reconnects
with a new `AgentClient`. The Cloud test runs one fake-agent task on
`alpha-dev.n3kw9` and checks the receipt/history contain no API key.

Tests accept `FACTORY_TEMPORAL_BIN` when `temporal` is not on `PATH`.

## Not covered in V1

Real `gh` PR creation against a sandbox repository (adapter written; local registry
tested), live Codex implementation runs, cmux automation, xPlan writes, cost/token
reporting from OpenCode (only elapsed time is measured), Continue-As-New for very
long tasks, multi-host task queues, and 50–100 worker scale.

For the harness layer: the coordinator, Console HTTP API, worker restart and a
three-real-task run are verified. The Console API is covered end-to-end by
`tests/test_harness_console_live.py` (session, submit, status, approval,
receipt); the browser UI itself is not separately automated. Temporal Agent
Harness remains pre-1.0 and pinned to 0.11.0, and the console has no built-in
authentication layer. cmux remains manual.

See [RELEASE.md](RELEASE.md) for the release candidate state, rollback and blockers.
