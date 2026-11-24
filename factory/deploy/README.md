# Hosted deployment (systemd)

Sanitized operator recipe for a single-host, low-resource pilot. It is not a
production guide: the Console has no authentication and must stay on loopback.

## Layout

```text
/opt/alpha-wiki-factory/
  releases/v0.8.2/          immutable tag checkout (factory/ inside)
  venvs/v0.8.2/             uv environment, external to the checkout
  current -> releases/v0.8.2
  current-venv -> venvs/v0.8.2
/etc/alpha-wiki/factory.env 0600 root:root, never committed
/var/lib/alpha-wiki-factory/
  state/                    durable receipts, prs.json, harness records
  work/                     ephemeral clones and worktrees
  home/                     service HOME (OpenCode auth must be provisioned here)
  cache/uv/                 uv cache for the Console unit
```

Releases stay immutable: the venv lives outside the checkout. Switch `current`
and `current-venv` together when changing release.

## Install

```bash
TAG=v0.8.2
install -d -m 0755 /opt/alpha-wiki-factory/{releases,venvs}
install -d -m 0700 /var/lib/alpha-wiki-factory/{state,work,home,cache,cache/uv}
git clone --branch "$TAG" --depth 1 \
  https://github.com/yura4gus/alpha-wiki-creator.git \
  "/opt/alpha-wiki-factory/releases/$TAG"
uv venv --python 3.12 "/opt/alpha-wiki-factory/venvs/$TAG"
UV_PROJECT_ENVIRONMENT="/opt/alpha-wiki-factory/venvs/$TAG" \
  uv sync --frozen --extra harness \
  --project "/opt/alpha-wiki-factory/releases/$TAG/factory"
ln -sfn "/opt/alpha-wiki-factory/releases/$TAG" /opt/alpha-wiki-factory/current
ln -sfn "/opt/alpha-wiki-factory/venvs/$TAG" /opt/alpha-wiki-factory/current-venv
```

Create `/etc/alpha-wiki/factory.env` from
[`factory.env.example`](factory.env.example), mode 0600 root:root. Transfer the
Temporal Cloud API key over SSH stdin; never put it in a command line, shell
history, repository or chat.

```bash
install -d -m 0700 /etc/alpha-wiki
# read the key from an existing 0600 file into the environment, then:
umask 077
ssh <host> 'cat > /etc/alpha-wiki/factory.env.tmp && chmod 600 /etc/alpha-wiki/factory.env.tmp && mv /etc/alpha-wiki/factory.env.tmp /etc/alpha-wiki/factory.env'
```

## Units

```bash
scp factory/deploy/systemd/*.service <host>:/etc/systemd/system/
ssh <host> systemctl daemon-reload
ssh <host> systemctl enable --now \
  alpha-wiki-factory-worker.service alpha-wiki-harness-coordinator.service
ssh <host> systemctl enable --now alpha-wiki-harness-console.service
```

`alpha-wiki-batch-worker.service` is prepared but must stay disabled until A2
delivers `agent_factory.batch_worker`. Its exact command is
`python -m agent_factory.batch_worker` on queue `bsc-batch`.

All units use `EnvironmentFile=/etc/alpha-wiki/factory.env`,
`ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`,
`NoNewPrivileges=true`, `UMask=0077`, `CPUQuota=200%`, `MemoryMax=4G`,
`Nice=10`, `IOWeight=100` and journald logging. State and work paths are the only
writable locations; the Console additionally writes `home/` and `cache/uv`.

## Verify

```bash
set -a; . /etc/alpha-wiki/factory.env; set +a
temporal task-queue describe --task-queue factory-code
temporal task-queue describe --task-queue factory-coordinator
temporal task-queue describe --task-queue bsc-batch   # empty until A2
curl -fsS http://127.0.0.1:8000/api/agents
ss -ltnp | grep ':8000'                                # must be 127.0.0.1
```

`bsc-batch` is expected to have no pollers in the v0.8.2 deployment.

## Console access

```bash
ssh -L 8000:127.0.0.1:8000 <host>
# then open http://127.0.0.1:8000 locally
```

Do not open port 8000 in the host firewall. Verify from outside the host that
the public address is closed.

## Health workflow (no model call)

Use the packaged fake agent to prove the worker, queue, checkpoint, tests,
review and receipt path without OpenCode:

```json
{
  "task_id": "health-<unique>",
  "repo": "/var/lib/alpha-wiki-factory/smoke/origin.git",
  "agent_steps": [["/opt/alpha-wiki-factory/current-venv/bin/python",
                   "/opt/alpha-wiki-factory/current/factory/tests/fake_agent.py",
                   "write", "src/health.txt", "ok"]],
  "test_command": ["/opt/alpha-wiki-factory/current-venv/bin/python", "-c",
                   "import pathlib,sys; sys.exit(0 if pathlib.Path(\"src/health.txt\").exists() else 1)"],
  "owned_paths": ["src"],
  "task_queue": "factory-code",
  "reviewer": "stub",
  "require_approval": false,
  "max_step_seconds": 60,
  "test_timeout_seconds": 60,
  "heartbeat_timeout_seconds": 15
}
```

Submit with the release venv:

```bash
set -a; . /etc/alpha-wiki/factory.env; set +a
cd /opt/alpha-wiki-factory/current/factory
/opt/alpha-wiki-factory/current-venv/bin/python -m agent_factory.client start health.json
/opt/alpha-wiki-factory/current-venv/bin/python -m agent_factory.client status <task_id>
```

## Restart and rollback

```bash
systemctl restart alpha-wiki-factory-worker.service
systemctl restart alpha-wiki-harness-coordinator.service
systemctl restart alpha-wiki-harness-console.service
```

Confirm each MainPID changed, pollers return and `GET /api/agents` is 200.
A post-restart health workflow proves the full path.

Rollback:

```bash
systemctl disable --now alpha-wiki-harness-console.service \
  alpha-wiki-harness-coordinator.service alpha-wiki-factory-worker.service
rm -rf /var/lib/alpha-wiki-factory/work/*     # ephemeral only
ln -sfn /opt/alpha-wiki-factory/releases/<previous> /opt/alpha-wiki-factory/current
ln -sfn /opt/alpha-wiki-factory/venvs/<previous> /opt/alpha-wiki-factory/current-venv
systemctl daemon-reload
systemctl enable --now alpha-wiki-factory-worker.service \
  alpha-wiki-harness-coordinator.service alpha-wiki-harness-console.service
```

Keep `/var/lib/alpha-wiki-factory/state`: receipts and `prs.json` are durable.
The batch unit is disabled, so rollback does not touch `bsc-batch`.

## Known gaps

- OpenCode CLI must be installed and authenticated on the host before a real
  task or OpenCode review can run. The units set
  `HOME=/var/lib/alpha-wiki-factory/home`; provision auth there or adjust the
  unit deliberately. No provider credential belongs in this repository.
- The Temporal Cloud API key expires; rotate the env file and restart all units.
- Harness 0.11.0 is pre-1.0 and pinned; upgrades need schema regeneration.
- The Console is unauthenticated and loopback-only.
