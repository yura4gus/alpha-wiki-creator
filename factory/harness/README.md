# Temporal Agent Harness integration

Optional coordination surface over the factory's existing execution path. It is **not** a
second executor and **not** an approval authority:

- `TaskWorkflow` still owns pin → context → agent steps → tests → review → approval → PR →
  xPlan dry-run → receipt.
- `TaskWorkflow.decide` is the only approval decision. The harness tool gate is skipped
  (`ToolApprovalPolicy.dangerously_skip_all()`); a Console tool approval never approves a
  factory task.
- No model is called. Every model call in a factory task still goes through the OpenCode CLI
  inside `TaskWorkflow`; this package imports no provider SDK.
- The four tools in `agent_factory.harness.tools` are the only bridge to the factory client.

Operator runbook (launcher `--harness`, logs, troubleshooting): [../HARNESS.md](../HARNESS.md).

## Versions (locked in `factory/uv.lock`)

| Package | Version |
|---|---|
| Python | 3.12.13 (project requires `>=3.12`) |
| temporal-agent-harness (extra `[ui]`) | 0.11.0 |
| temporalio | 1.36.1 |
| pydantic | 2.14.3 |
| fastapi | 0.163.1 |
| uvicorn | 0.54.0 |
| pyyaml | 6.0.3 |

`temporal-agent-harness` 0.11.0 is the latest published release; every GitHub release is
marked pre-release. Pin exact versions and upgrade deliberately.

## Install

```bash
cd factory
uv sync --python 3.12                 # base: TaskWorkflow, CLI, launcher; harness stays out
uv sync --extra harness               # adds temporal-agent-harness[ui]==0.11.0
```

The extra is declared as:

```toml
[project.optional-dependencies]
harness = ["temporal-agent-harness[ui]==0.11.0"]
```

The base install imports neither `temporal_agent_harness` nor `pydantic`; the two harness test
modules skip on `pytest.importorskip("temporal_agent_harness")`.

## Files

| Path | Purpose |
|---|---|
| `agents.toml` | Registry for `temporal-agent-harness dev|serve|doctor` |
| `FactoryCoordinatorAgent.schema.json` | Generated typed surface (messages, handlers, `$defs`) |
| `../src/agent_factory/harness/models.py` | Pydantic wire models (`FactoryTaskSpec`, four messages, `TaskStatus`) |
| `../src/agent_factory/harness/tools.py` | Four `@agent.activity_tool_defn` tools; the only factory bridge |
| `../src/agent_factory/harness/coordinator.py` | `FactoryCoordinatorAgent` (`@agent.defn`) |
| `../src/agent_factory/harness/worker.py` | Coordinator worker (task queue `factory-coordinator`) |

Regenerate the schema after changing a message model or handler:

```bash
cd factory
uv run --extra harness temporal-agent-harness schema \
  agent_factory.harness.coordinator:FactoryCoordinatorAgent \
  -o harness/FactoryCoordinatorAgent.schema.json
```

Current digests: `agents.toml` `f56d327b032647a5864212dbffdf7671d9d69dd45008da70838a3fb16cfb70c1`;
schema `f9049d1561149c56db0cab30e131da641ac4cceb66ce4f148d84d6d6dd75be36`.

## Messages

| Handler | Input | Result |
|---|---|---|
| `submit_task` | `SubmitTask{spec: FactoryTaskSpec}` | `TaskStatus`; starts `task-<task_id>` with `REJECT_DUPLICATE` + `FAIL`, never a second run |
| `get_status` | `TaskStatusQuery{task_id}` | `TaskStatus` from the live state query + durable receipt |
| `approve_task` | `TaskApproval{task_id, verdict, by, note}` | `TaskStatus`; forwards to `TaskWorkflow.decide` |
| `cancel_task` | `TaskCancellation{task_id}` | `TaskStatus`; workflow cancel, then the finalized `CANCELED` receipt |

All four handlers are `MidTurn.ENQUEUE` and `model_callable=False`. Each dispatches one tool
through `runner.run_tool(str(workflow.uuid4()), TOOL, Request(...))`, so the Console receives
real `tool_start` / `tool_end` events. Failures come back as `TaskStatus.error`; success is
never fabricated. `TaskStatus.entries` lists receipt entry keys; `metrics` carries the recorded
step/test metrics.

`FactoryTaskSpec` mirrors `agent_factory.models.TaskSpec` field for field (25 fields); the
conversion is `TaskSpec(**spec.model_dump())`. `test_harness_units.py` fails if the two
definitions drift.

## Run

```bash
cd factory
temporal server start-dev            # or reuse a running server

# console/API + session manager (localhost:8000)
uv run --extra harness temporal-agent-harness dev harness/agents.toml --host 127.0.0.1

# coordinator worker (separate terminal; same Temporal namespace)
TEMPORAL_ADDRESS=localhost:7233 FACTORY_HARNESS_TASK_QUEUE=factory-coordinator \
  PYTHONPATH=src uv run --extra harness python -m agent_factory.harness.worker
```

Or one command with the factory worker and both harness processes:

```bash
uv run --extra harness python -m agent_factory.launcher up --harness --no-follow
```

Connection environment:

- `FACTORY_TEMPORAL_ADDRESS`, then the SDK `TEMPORAL_*` profile (Cloud: namespace, API key,
  TLS), then `localhost:7233` — resolved by `agent_factory.connection`, the same rule the
  factory worker uses.
- `FACTORY_HARNESS_TASK_QUEUE` (default `factory-coordinator`) must match the registry's
  `task_queue`. Both are also prefixed by `TASK_QUEUE_PREFIX` when that is set, because the
  registry loader and the worker apply the same prefix.
- `FACTORY_STATE_DIR` / `FACTORY_WORK_ROOT` are read by the tools/activities exactly as in
  the base factory.

## Verification (2026-11-15, macOS, local Temporal 1.32.2 dev server)

```bash
uv run --extra harness temporal-agent-harness doctor --registry harness/agents.toml \
  --api-url http://127.0.0.1:8000
# OK registry: 1 agents; referenced schemas loaded
# OK temporal: namespace default
# OK queue:factory-coordinator: ready
# OK queue:session-manager: ready
# OK api: 1 registered agents
# OK worker:FactoryCoordinatorAgent: ready

curl -s http://127.0.0.1:8000/api/agents
# FactoryCoordinatorAgent / factory-coordinator / worker.status "ready"
```

A Console session created through `POST /api/sessions` and a `get_status` message through
`POST /api/chat` produced `turn_started → message_handler_start → tool_start → tool_end →
message_handler_end → turn_end`; the typed reply was a `TaskStatus` with `state=NOT_FOUND`
and an explicit `error` for an unknown task. No model events, no approval events. Port 8000
was released after the check.

The end-to-end DoD is `factory/tests/test_harness_integration.py`: normal `TaskWorkflow`
worker + coordinator worker, three `TaskWorkflow` tasks with the scripted fake agent
(success, approval, cancel), a coordinator
worker restart with the same workflow id, and a duplicate submit that starts nothing.
The live AH-07 acceptance is `factory/tests/test_harness_live.py`: three real OpenCode
tasks submitted through the coordinator, one approved through `TaskWorkflow.decide`,
live independent review, worker restart and a new `AgentClient` reconnect.

## Tests

```bash
cd factory
uv run --extra harness pytest tests/test_harness_units.py tests/test_harness_integration.py
uv run --extra harness pytest          # whole suite, live tests still skip
```

The integration test needs only the local `temporal` CLI (through the existing `env`
fixture) and the `harness` extra; it makes no live model call.

## Gaps

- The harness tool-approval gate is intentionally skipped; if a future tool ever needs its
  own approval, it must not become a second path for `TaskWorkflow.decide`.
- The session manager caches `agents.toml` at first start. After editing the registry, restart
  the stack and reset the local dev database (see [../HARNESS.md](../HARNESS.md)).
- Changing a message model requires regenerating the schema file; `test_harness_units.py`
  compares the file with `agent_schema(FactoryCoordinatorAgent)` and fails on drift.
- One coordinator worker per `factory-coordinator` queue is the supported topology. A second
  worker is harmless (Temporal load-balances workflow tasks) but does not add capacity for
  the factory work itself.
- `AgentHarnessPlugin` defaults to local-filesystem large-payload offload. A multi-host
  deployment must pass a shared `ExternalStorage` (for example S3) to the plugin, or large
  tool payloads written by one host are unreadable by another.
- The harness release is pre-release; API changes are expected on upgrade.
