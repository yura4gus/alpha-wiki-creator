# rx-back compute worker (systemd)

`rx-back` is external compute for the `bsc-batch` task queue only. The control
plane — Harness coordinator, Console/API, Session Manager and lightweight coding
workers — runs on Railway (A6). This host must not run a coordinator, Console,
OpenCode Server, `factory-code` worker or any other control service.

Current state (2026-11-24T21:08Z): the batch unit is installed and **disabled**.
It cannot start until A2 delivers `agent_factory.batch_worker`. `bsc-batch` has
no pollers and an empty backlog. The rollback that removed the control-plane
units is recorded in
[EVIDENCE-2026-11-25-control-plane-rollback.md](EVIDENCE-2026-11-25-control-plane-rollback.md).

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
  home/                     service HOME (no OpenCode credential on this host)
```

Releases stay immutable: the venv lives outside the checkout. Switch `current`
and `current-venv` together when changing release.

## Install the release

```bash
TAG=v0.8.2   # replace with the release that contains agent_factory.batch_worker
install -d -m 0755 /opt/alpha-wiki-factory/{releases,venvs}
install -d -m 0700 /var/lib/alpha-wiki-factory/{state,work,home}
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

`--extra harness` is only needed if the batch module imports harness code. It
does not start a harness process.

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

## Unit

```bash
scp factory/deploy/systemd/alpha-wiki-batch-worker.service <host>:/etc/systemd/system/
ssh <host> systemctl daemon-reload
```

Do not enable it until the module exists:

```bash
ssh <host> 'test -f /opt/alpha-wiki-factory/current/factory/src/agent_factory/batch_worker.py'
ssh <host> systemctl enable --now alpha-wiki-batch-worker.service
```

Exact unit contract:

| Field | Value |
|---|---|
| Unit | `alpha-wiki-batch-worker.service` |
| Command | `/opt/alpha-wiki-factory/current-venv/bin/python -m agent_factory.batch_worker` |
| Queue | `bsc-batch` (`Environment=FACTORY_TASK_QUEUE=bsc-batch`) |
| Restart | `Restart=always`, `RestartSec=10`, `TimeoutStopSec=30` |
| Limits | `CPUQuota=200%` (2 of 64 vCPU), `MemoryMax=4G`, `Nice=10`, `IOWeight=100`, `LimitNOFILE=65536` |
| Isolation | `User=root`, `UMask=0077`, `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=true`, `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` |
| Writable | `/var/lib/alpha-wiki-factory/{state,work,home}` only |
| Logging | journald, `SyslogIdentifier=alpha-wiki-batch-worker` |

State survives restart and release switch: keep
`/var/lib/alpha-wiki-factory/state`. `work/` is ephemeral and safe to clear.

## Verify Temporal connectivity

```bash
set -a; . /etc/alpha-wiki/factory.env; set +a
temporal task-queue describe --task-queue bsc-batch
```

Expected before A2: statistics at 0 and an empty poller list. Expected after
enable: pollers for the task types the batch module registers, with identity
`<pid>@rx-back`. Never print `TEMPORAL_API_KEY`; the env file is mode 0600
root:root.

Recorded on 2026-11-24T21:08Z: the Cloud endpoint is reachable from `rx-back`
over TLS with this env file, `bsc-batch` describes successfully with 0 pollers,
and the CLI version is 1.10.1.

## Capacity

Measured 2026-11-24T21:00Z on `rx-back` (ASUS KRPA-U16, Ubuntu 24.04, kernel
6.8.0-147):

- 64 vCPU, 125 GiB RAM, 31 GiB swap, 537 GiB free on `/dev/md2`.
- Load average 1.35 / 1.23 / 1.08; 24 GiB used, 101 GiB available.
- Existing BSC, PostgreSQL, Redis, r53 and Docker workloads stay untouched.

A 2-vCPU / 4 GiB batch worker fits without pressure. Raise `CPUQuota` or add a
second unit only after observing `bsc-batch` backlog and queue latency; the
queue name must stay `bsc-batch`.

## Rollback

```bash
systemctl disable --now alpha-wiki-batch-worker.service
```

This stops queue consumption. It does not delete receipts or state. The control
plane on Railway is unaffected. Do not remove units or state that belong to
other `rx-back` workloads.

## Known gaps

- A2 has not delivered `agent_factory.batch_worker`; the unit is disabled and
  `bsc-batch` has no pollers.
- The Temporal Cloud API key expires; rotate the env file and restart the unit.
- No OpenCode installation or credential belongs on this host. OpenCode remote
  execution is owned by A4/A6 on Railway.
