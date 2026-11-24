# Railway control plane (pilot)

Status: **PILOT DEPLOYED** for the v0.8.2 factory. Railway runs the persistent
lightweight control plane; `rx-back`/`arm-02` remain the compute workers.
Temporal Cloud (`alpha-dev.n3kw9`) stays the only durable execution backend.
No second Temporal cluster, database, scheduler or backlog is created.

Authority is unchanged: `TaskWorkflow` executes and approves; the Harness Console
is a coordination surface; OpenCode makes every model call; xPlan stays
read-only. See [README.md](README.md), [HARNESS.md](HARNESS.md) and
[RELEASE.md](RELEASE.md).

Actual project/service/volume IDs, deployment SHAs and the cost snapshot live in
the operator's private notes, not in this public repository.

## Topology

| Railway service | Process(es) | Task queues | Volume | Public domain |
|---|---|---|---|---|
| `agent-factory-runtime` | `python -m agent_factory.worker` + `python -m agent_factory.harness.worker` | `factory-code`, `factory-coordinator` | `/data` | none |
| `agent-factory-harness` | `temporal-agent-harness dev factory/harness/agents.toml --host 0.0.0.0 --port 8000` | `session-manager` (adopts the existing workflow) | none | none |

One image serves both services: [Dockerfile](Dockerfile), built from the
repository root so it also carries `tools/xplan_dry_run.py`. The executor and
coordinator share a container because the coordinator reads the executor's
receipts from `FACTORY_STATE_DIR`; a Railway volume can only be attached to one
service.

There is **no** `opencode-server` service. No healthy remote OpenCode server was
present, so the worker runs the pinned OpenCode 2.3.0 CLI locally. A4 can replace
this with one shared server later; keep exactly one and point
`FACTORY_OPENCODE_BIN` at the wrapper. Do not run two.

## Persistence and limits

- `FACTORY_STATE_DIR=/data/state` — receipts and the local PR registry.
- `HOME=/data/home` — OpenCode's integration database, git credentials.
- `FACTORY_WORK_ROOT=/tmp/factory-work` — clones/worktrees are scratch and may
  be lost; recovery rebuilds from the last pushed checkpoint.
- `FACTORY_MAX_ACTIVITIES=4` bounds concurrent activities per worker; one
  replica per service; `restartPolicyType=ALWAYS`.
- No hard CPU/RAM cgroup setting is exposed by the deployment API; the one
  replica and activity bound are the pilot limits. Revisit before scale-out.
- Region: Southeast Asia, matching the existing Railway projects. Temporal Cloud
  is the WAN dependency.

## Queue routing

| Queue | Owner | Rule |
|---|---|---|
| `factory-code` | Railway runtime + external compute | portable coding tasks; the first available poller wins |
| `factory-coordinator` | Railway runtime | typed submit/status/approve/cancel only |
| `session-manager` | Railway harness | adopts the existing durable workflow |
| `bsc-batch` | external compute (A1/A2) | **never** polled by Railway; bulk data stays off the control plane |

Host-affine work (repos or data that exist only on `rx-back`) must use a
dedicated external queue, not shared `factory-code`, because a Railway poller
could otherwise claim it. A2's batch worker is the gate for `bsc-batch`; Railway
intentionally has no poller for it.

## Deploy

Prerequisites: Railway CLI authenticated, project/environment created, the
volume attached to `agent-factory-runtime` at `/data`, and the two service start
commands set as in the topology table.

```bash
export RAILWAY_PROJECT_ID=...
export RAILWAY_ENVIRONMENT_ID=...
export RAILWAY_RUNTIME_SERVICE=agent-factory-runtime
export RAILWAY_HARNESS_SERVICE=agent-factory-harness
factory/scripts/railway_deploy.sh
```

Candidate redeploy (A2/A4 code must be committed and merged first; never deploy
a dirty worktree):

```bash
cd /path/to/accepted-alpha-wiki-checkout
git rev-parse HEAD                      # must equal the accepted source SHA
export RAILWAY_PROJECT_ID=...
export RAILWAY_ENVIRONMENT_ID=...
factory/scripts/railway_deploy.sh
```

`railway_deploy.sh` runs `railway up` for both services from that checkout, so
the Docker build context and `FACTORY_SOURCE_SHA` must describe the same commit.
Update `FACTORY_SOURCE_SHA` to the accepted SHA before the deploy and record it
with the deployment IDs.

Set secrets from files/stdin, never as commit content or shell history:

```bash
set -a; . ~/.config/temporal-mcp/.env; set +a
printf '%s' "$TEMPORAL_API_KEY" \
  | railway variable set TEMPORAL_API_KEY --stdin --skip-deploys \
      -p "$RAILWAY_PROJECT_ID" -e "$RAILWAY_ENVIRONMENT_ID" -s "$RAILWAY_RUNTIME_SERVICE"

# OpenCode 2 integrations live in its database; move them with auth export/import.
opencode auth export --standalone > /tmp/opencode-auth.json   # 0600
base64 < /tmp/opencode-auth.json | tr -d '\n' \
  | railway variable set OPENCODE_AUTH_EXPORT_B64 --stdin --skip-deploys \
      -p "$RAILWAY_PROJECT_ID" -e "$RAILWAY_ENVIRONMENT_ID" -s "$RAILWAY_RUNTIME_SERVICE"
rm -f /tmp/opencode-auth.json
```

`factory/docker/lib.sh` imports that export at boot, writes nothing to the
image, and unsets the variable before workers start. The API key never enters
workflow history, a receipt or a log.

The full variable contract (non-secret):

| Variable | Runtime | Harness |
|---|---|---|
| `TEMPORAL_ADDRESS` | `alpha-dev.n3kw9.tmprl.cloud:7233` | same |
| `TEMPORAL_NAMESPACE` | `alpha-dev.n3kw9` | same |
| `TEMPORAL_TLS` | `true` | same |
| `FACTORY_TEMPORAL_ADDRESS` | same as `TEMPORAL_ADDRESS` | same |
| `FACTORY_TASK_QUEUE` | `factory-code` | — |
| `FACTORY_HARNESS_TASK_QUEUE` | `factory-coordinator` | `factory-coordinator` |
| `FACTORY_STATE_DIR` | `/data/state` | `/tmp/harness-state` |
| `FACTORY_WORK_ROOT` | `/tmp/factory-work` | `/tmp/factory-work` |
| `FACTORY_MAX_ACTIVITIES` | `4` | — |
| `FACTORY_PLUGIN_ROOT` | `/app` | `/app` |
| `FACTORY_REVIEW_MODEL` | `opencode-go/deepseek-v4.1-flash` | same |
| `HOME` | `/data/home` | `/tmp/home` |
| `PORT` | — | `8000` |

## Private access

Neither service has a public domain. The Console is reachable only on Railway's
private network and through SSH:

```bash
# From the runtime container to the console (private DNS):
railway ssh -p "$RAILWAY_PROJECT_ID" -e "$RAILWAY_ENVIRONMENT_ID" \
  -s "$RAILWAY_RUNTIME_SERVICE" -- \
  'curl -fsS http://agent-factory-harness.railway.internal:8000/api/agents'

# Operator shell on the harness container:
railway ssh -p "$RAILWAY_PROJECT_ID" -e "$RAILWAY_ENVIRONMENT_ID" \
  -s "$RAILWAY_HARNESS_SERVICE" -- 'curl -fsS http://127.0.0.1:8000/api/agents'
```

There is no authentication layer on the Console. Keeping it domainless is the
access control: the only routes are private DNS and SSH. Do not add a public
domain without an authenticated proxy.

## Verification

```bash
# Pollers (use the Temporal MCP target or CLI):
temporal task-queue describe --address alpha-dev.n3kw9.tmprl.cloud:7233 \
  --namespace alpha-dev.n3kw9 --tls --api-key "$TEMPORAL_API_KEY" \
  --task-queue factory-code --task-queue-type workflow
# repeat for factory-coordinator; bsc-batch must show 0 pollers.
```

Restart `agent-factory-runtime`; both queues must regain a poller. Restart
`agent-factory-harness`; `/api/agents` must return 200 and the existing
`session-manager` workflow must be adopted, not recreated.

## One bounded pilot task

```bash
railway ssh ... -s agent-factory-runtime -- \
  'python /app/factory/scripts/railway_seed_demo.py'
# then submit the printed spec and approve at AWAITING_APPROVAL
railway ssh ... -s agent-factory-runtime -- \
  'python -m agent_factory.client start /data/seed/task.json'
railway ssh ... -s agent-factory-runtime -- \
  'python -m agent_factory.client status <task-id>'
railway ssh ... -s agent-factory-runtime -- \
  'python -m agent_factory.client decide <task-id> approve --by railway-operator --note pilot'
```

The seed repo is a bare repo on `/data`, so no GitHub credential is needed for
the pilot. The task uses the real OpenCode CLI and live review; the receipt is
frozen under `/data/state/receipts`.

Pilot evidence (2026-11-24/25 UTC):

- The first real task failed at the step commit boundary with
  `OwnershipViolation: changed files outside owned paths ['app']:
  ['tests/__pycache__/test_calc.cpython-312.pyc']`. The model edit and tests
  were correct; the factory staged generated bytecode because the pilot origin
  had no `.gitignore`. **This is the A2 generated-cache/PWD gate, not a model or
  Railway failure.** Do not claim remote coding E2E acceptance before the A2
  candidate lands.
- A second task with a repository `.gitignore` (only `__pycache__/` and `*.pyc`)
  reached `PR_OPEN` in 144 s with a live `APPROVE`, 17.4 s measured step time and
  a valid frozen receipt. This verifies the Railway execution/review/approval
  path; it does **not** replace the A2 factory-level fix.
- `bsc-batch` has an external poller on `rx-back` and no Railway poller.
- Restarting the harness adopted the existing `session-manager` workflow; no
  second session-manager run was created.

## ITSPlan (xPlan), read-only

`plan-api.value8.dev` returns **HTTP 401** for `/docs` and has no public
`openapi.json`; no authenticated read route was discoverable from this account.
The adapter therefore consumes a read-only snapshot produced by an authorised
exporter and never calls the write API:

```bash
uv run python -m agent_factory.xplan bind snapshot.json
uv run python -m agent_factory.xplan build snapshot.json task-template.json --out task.json
uv run python -m agent_factory.xplan plan snapshot.json event.json --plugin-root .
uv run python -m agent_factory.xplan receipt /data/state/receipts/task-<id>.json
```

Snapshot contract (`agent-factory.xplan-snapshot/1`):

```json
{
  "schema": "agent-factory.xplan-snapshot/1",
  "project": {"id": 7, "name": "RateX", "revision": "..."},
  "issue": {
    "id": 42, "identifier": "RATEX-42", "title": "...", "description": "...",
    "columnId": 1, "updatedAt": "2026-11-24T12:00:00Z",
    "dependencies": [{"identifier": "RATEX-40", "status": "DONE"}],
    "required_delivery_level": 3, "worker": "opencode"
  },
  "columns": {"TODO": 1, "IN_PROGRESS": 2, "DONE": 3, "REWORK": 4},
  "run_id": "pilot-1",
  "approved_by": "owner"
}
```

`bind` maps the identifier to `task-<task_id>`; `build` merges it with
`repo`, `agent_steps`, `test_command`, `owned_paths` for the coordinator's
`submit_task`; `plan` delegates to `tools/xplan_dry_run.plan_transition` and
returns only `dry_run` decisions (`PROPOSE`, `NO_CHANGE`, `SKIP_CONFLICT`,
`STALE_SHA`, `GATE_PENDING`, `NEEDS_OWNER`, `REWORK`). No write path exists and
no second backlog is created.

## Gates and rollback

Gates outside this deployment:

- A2 batch worker: `bsc-batch` has no Railway poller by design.
- A4 OpenCode server: none existed; the pilot uses the local CLI. Replace only
  when one shared server is ready.
- A1 external compute: `rx-back`/`arm-02` own host-affine queues.

Rollback removes only the pilot services/volume/domain (none) in
`agent-factory-control`; Temporal Cloud workflows and receipts on the volume are
the only state. Never modify or restart ITSPlan services (`plan.value8.dev`,
`plan-api.value8.dev`); they are not in this project.
