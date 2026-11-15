# Harness operator runbook

The Temporal Agent Harness layer is the **coordination surface** for the factory:
durable sessions, a browser console and the coordinator worker. It is not the
executor and not the approval authority. `TaskWorkflow` still runs the pinned
snapshot, agent steps, tests, review, approval and PR stages. Every model call
goes through OpenCode; the harness adds no provider SDK or API key.

This layer is optional. Without `--harness`, `agent_factory.launcher up` behaves
exactly as in [README.md](README.md).

## Prerequisites

- Python 3.12+, `uv`, Git and the `temporal` CLI.
- The `harness` extra declared in `factory/pyproject.toml` (the packaged
  `temporal-agent-harness[ui]==0.11.0` dependency).
- `factory/harness/agents.toml` (the agent registry) and the coordinator package
  `agent_factory.harness.worker`. If either is missing, `--harness` exits 2 with
  the missing path instead of starting a partial stack.
- OpenCode already authenticated for the factory's agent/reviewer calls.

## Start

From the factory directory:

```bash
cd factory
uv run --extra harness python -m agent_factory.launcher up --harness
```

The launcher:

1. starts `temporal server start-dev` when `--address` /
   `FACTORY_TEMPORAL_ADDRESS` is unreachable;
2. opens the in-process factory `TaskWorkflow` worker on `FACTORY_TASK_QUEUE`
   (default `factory`) and on every task queue named by admitted tasks;
3. starts the harness session manager, API and console with
   `uv run --extra harness temporal-agent-harness dev <registry> --port <port>
   --host 127.0.0.1`;
4. waits for Temporal, then for the console port to accept TCP connections;
5. starts `python -m agent_factory.harness.worker` on
   `FACTORY_HARNESS_TASK_QUEUE` (default `factory-coordinator`);
6. prints a `READY` block with the Temporal address/UI, console URL, queues,
   task ids and log directory.

Useful flags:

```bash
--harness-registry PATH   # default <factory>/harness/agents.toml
--harness-port PORT       # default 8000
--task SPEC.json          # repeatable; admits factory tasks
--no-follow               # do not follow workflows; with --harness stay up
--approve-by NAME         # explicit auto-approval for this launcher run
--address HOST:PORT       # factory Temporal address
```

Without `--task`, the stack stays up until Ctrl-C. With tasks and without
`--no-follow`, the launcher follows them and stops the harness stack after they
close. With `--no-follow`, the stack remains up for the operator.

Ports:

| Service | URL |
|---|---|
| Harness console / API | `http://localhost:8000` (`--harness-port`) |
| Temporal Web UI | `http://localhost:8233` for gRPC `:7233`; a launcher-started custom dev port uses gRPC port + 1000 |
| Temporal gRPC | `localhost:7233` (`--address`) |

The console binds to `127.0.0.1` so it is not exposed on the LAN.

### Temporal Cloud

Set the SDK profile variables in the launcher shell; the coordinator, harness
server and factory worker all use the same resolved target:

```bash
set -a; . ~/.config/temporal-mcp/.env; set +a   # TEMPORAL_API_KEY, mode 600
export TEMPORAL_ADDRESS=alpha-dev.n3kw9.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=alpha-dev.n3kw9
export TEMPORAL_TLS=true
cd factory
uv run --extra harness python -m agent_factory.launcher up --harness
```

A loopback `FACTORY_TEMPORAL_ADDRESS` or `--address` stays plaintext even when a
Cloud key is exported. A non-loopback target keeps the namespace, API key and
TLS. The API key is read only by `agent_factory.connection`/the harness SDK; it
never enters workflow history, a receipt or a log.

## Submit, inspect, approve, cancel

Open the console and create a session for the factory coordinator agent listed
in `factory/harness/agents.toml`. Its handlers are `submit_task`, `get_status`,
`approve_task` and `cancel_task`; the console's message/handler controls select
one and send its typed request. The coordinator calls the same factory client
and Temporal workflows; it does not execute agent steps itself and calls no
model.

Approval authority is **`TaskWorkflow.decide`**, an Update on workflow
`task-<task_id>`. In the Console, the coordinator's `approve_task` handler calls
that Update (and `cancel_task` cancels the workflow); the receipt records the
operator name from the `decide` Update. The harness's own per-tool approval gate
is separate: the coordinator skips it, and approving a harness tool would not
change factory task state.

The authoritative CLI paths remain available and are useful when the console is
unavailable:

```bash
# use the launcher's --address if it is not localhost:7233
uv run python -m agent_factory.client --address localhost:7233 start task.json
uv run python -m agent_factory.client --address localhost:7233 status fix-calc-1
uv run python -m agent_factory.client --address localhost:7233 \
  decide fix-calc-1 approve --by owner --note "reviewed diff"
uv run python -m agent_factory.client --address localhost:7233 cancel fix-calc-1
uv run python -m agent_factory.launcher --address localhost:7233 status fix-calc-1
uv run python -m agent_factory.launcher receipt fix-calc-1
```

`launcher status` adds a `harness` object when a stack record exists: recorded
port, console URL, `listening`, process `pid`/`alive`, state and queues. It does
not infer task state; task rows still come from Temporal and the receipt. Run
`launcher status` with no task id to print only harness liveness.

## Stop

Press Ctrl-C in the launcher terminal. The launcher stops the coordinator and
harness process groups (SIGTERM, then SIGKILL after 10 s) and stops a Temporal
dev server it started. A Temporal server that was already running is left
alone. Receipts, the local PR registry and pushed `factory/<task_id>` branches
remain durable.

If the launcher was killed with SIGKILL, its children can survive. Inspect the
record and kill the recorded process groups manually:

```bash
cat "${FACTORY_STATE_DIR:-$HOME/.agent-factory/state}/harness/stack.json"
kill -TERM -<pid>     # one process group from the record
```

## Session reconnect and worker restart

Sessions are Temporal workflows. Reload the console and reopen the same session
id; the session continues after a browser reload or a worker restart. An agent
whose worker is not polling accepts a created session but does not progress.

Restart the coordinator without restarting Temporal:

```bash
export TEMPORAL_ADDRESS=localhost:7233
export FACTORY_HARNESS_TASK_QUEUE=factory-coordinator
# from factory/; add PYTHONPATH=src when the package is not installed
uv run --extra harness python -m agent_factory.harness.worker
```

In the normal flow, stop the launcher and start it again; this restarts the
factory worker, console and coordinator together. The console's session list is
durable, so the old session can be resumed.

The session manager caches the registry on first start. After changing
`factory/harness/agents.toml`, stop the stack and either use a fresh
`FACTORY_STATE_DIR` or remove the stopped dev database
(`$FACTORY_STATE_DIR/temporal/temporal.db`) before restarting. This resets local
Temporal history; receipts are separate files and are not removed.

## Logs and records

```text
$FACTORY_STATE_DIR/
  harness/harness.log       harness dev stdout/stderr (uv, session manager, API)
  harness/coordinator.log   agent_factory.harness.worker stdout/stderr
  harness/stack.json        launcher record: state, pids, port, registry, queues
  temporal/temporal.log     launcher-started Temporal dev server
  receipts/                 per-task frozen receipts
```

The launcher appends to logs; it does not truncate them. `stack.json` is written
during startup, after the coordinator starts, and on stop/failure.

## Troubleshooting

| Symptom | Cause and action |
|---|---|
| `harness registry not found: ...` | `factory/harness/agents.toml` is missing. Restore it or pass `--harness-registry`; rerun without `--harness` for the factory-only stack. |
| ``the `harness` extra is not declared`` | `factory/pyproject.toml` lacks the `harness` optional dependency. Sync the extra or rerun without `--harness`. |
| `coordinator package is unavailable` | `agent_factory.harness.worker` is absent. Install the coordinator package; the launcher will not run a console without it. |
| `port 8000 is already accepting connections` | Another process owns the console port. Stop it or pass `--harness-port`. |
| `harness API did not accept connections ...` | Read `harness/harness.log`. Common causes: `uv` install failure, missing `[ui]` extra, or a Temporal connection error. |
| `coordinator exited during startup` | Read `harness/coordinator.log`. Common causes: missing coordinator module, import error, or a Temporal address mismatch. |
| Console lists an agent but sessions never progress | The coordinator worker is not polling. Check `stack.json` process liveness and `temporal task-queue describe --task-queue factory-coordinator`. Restart the coordinator. |
| Factory task waits in `AWAITING_APPROVAL` | This is the `TaskWorkflow` decision. Use the Console coordinator's `approve_task` handler or `decide <task> approve --by <name>` (or `--approve-by` at launch). A harness tool approval is not this decision. |
| Console shows stale agents after a registry edit | The session manager cached the registry. Stop the stack and reset the dev database as described above. |
| Harness console works, factory tasks do not run | The in-process factory worker polls `FACTORY_TASK_QUEUE` and admitted task queues. Confirm the task's `task_queue` is in the `Factory queues` line. |

## cmux (manual, optional)

cmux is a terminal UI for the operator, not execution authority and not a
launcher dependency. There is no launcher integration or automation; a missing
or busy cmux never blocks a task. In this environment `cmux` is not on `PATH`;
the app-bundle CLI is at
`/Applications/cmux.app/Contents/Resources/bin/cmux` (verified with `--help`).

Open a workspace at the factory directory manually:

```bash
/Applications/cmux.app/Contents/Resources/bin/cmux open /path/to/alpha-wiki/factory
# or, when the cmux CLI is on PATH:
cmux open /path/to/alpha-wiki/factory
```

Then run the start command in that pane and `launcher status`/`receipt` in a
second pane. Workspace opening itself was not exercised here; treat it as a
manual operator step.
