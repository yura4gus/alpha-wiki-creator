# Control-plane rollback on rx-back (2026-11-24T21:08Z)

Scope change A6: Railway is the control plane. `rx-back` is external compute for
`bsc-batch` only. This record preserves the deployment evidence gathered before
the rollback and states exactly what was stopped, removed and left in place.

## Host facts

| Fact | Value |
|---|---|
| Host | `rx-back` (95.217.72.204), ASUS KRPA-U16 |
| OS / kernel | Ubuntu 24.04 LTS, 6.8.0-147-generic |
| CPU / RAM / swap | 64 vCPU / 125 GiB / 31 GiB |
| Disk | `/dev/md2` 847G, 268G used, 537G free (34%) |
| Load at rollback | 1.35 / 1.23 / 1.08 |
| Uptime | 13 days 23:57 |
| Temporal CLI | 1.10.1 (server 1.32.2) |
| Temporal endpoint | reachable over TLS from `rx-back` with `/etc/alpha-wiki/factory.env` |

## Stopped and removed

All actions ran on 2026-11-24 between 22:03 and 22:08 CET (21:03–21:08Z).

| Service | MainPID | Before | After |
|---|---|---|---|
| `alpha-wiki-factory-worker.service` (`factory-code`) | 2687323 | enabled, active | disabled, unit file removed |
| `alpha-wiki-harness-coordinator.service` (`factory-coordinator`) | 2687343 | enabled, active | disabled, unit file removed |
| `alpha-wiki-harness-console.service` (127.0.0.1:8000) | 2687465 (child 2687470) | enabled, active | disabled, unit file removed; port 8000 free |
| OpenCode server (`opencode serve --service`) | 2685832 | running, 127.0.0.1:49374 | terminated; port 49374 free |

Commands:

```bash
systemctl disable --now alpha-wiki-harness-console.service \
  alpha-wiki-harness-coordinator.service alpha-wiki-factory-worker.service
rm -f /etc/systemd/system/alpha-wiki-factory-worker.service \
  /etc/systemd/system/alpha-wiki-harness-coordinator.service \
  /etc/systemd/system/alpha-wiki-harness-console.service
systemctl daemon-reload
```

The Console stop exits 143 under systemd; that is the expected SIGTERM result,
not a failure. No unit file for these services remains.

OpenCode was installed at 21:46 CET during this deployment. Its install and
credentials were archived, not deleted, to keep evidence and avoid leaving a
server or credential on active paths:

```text
/root/factory-rollback-20261125/.opencode/
/root/factory-rollback-20261125/.config/opencode/
/root/factory-rollback-20261125/.local/share/opencode/
/root/factory-rollback-20261125/.cache/opencode/
```

Nothing in `/root/.bashrc`, `/root/.profile`, cron or systemd starts OpenCode.
`opencode` is not on `PATH`. Do not restore it on `rx-back`; A4/A6 own remote
execution on Railway.

A second OpenCode server (PID 2696760) appeared at 22:07 CET from
`/root/factory-telemetry-20261124/runtime/bin/opencode`. It was not created by
this deployment; concurrent work wrote `coding.json` and test logs in that
directory. It had no established connections after 22:11 CET and was stopped at
22:15 CET together with its pty child (PID 2698375). The telemetry runtime
directory is left in place for its owner. Port 49374 is free.

## Left in place

- `/etc/systemd/system/alpha-wiki-batch-worker.service` — loaded, **disabled**,
  inactive. Exact command:
  `/opt/alpha-wiki-factory/current-venv/bin/python -m agent_factory.batch_worker`,
  queue `bsc-batch`.
- `/opt/alpha-wiki-factory/{releases,venvs}/v0.8.2`, `current`, `current-venv`
  (release checkout at `dc9f768`).
- `/etc/alpha-wiki/factory.env`, mode 0600 root:root (API key not printed).
- `/var/lib/alpha-wiki-factory/state`: `prs.json`, `prs.lock`, receipts
  `task-health-20261124T204859Z.json`, `task-health2-20261124T205108Z.json`.
- `/var/lib/alpha-wiki-factory/deployment-receipt-v0.8.2-20261124.md` with its
  addendum.
- `/var/lib/alpha-wiki-factory/smoke`, `/work` (ephemeral), `/home`.

The remaining BSC, PostgreSQL (5432), Redis (6379), nginx (4080/4443/5080/7080),
r53 and Docker workloads were not touched. Docker still runs `platform-bff` and
`celery-exporter`.

## Queue state after rollback (2026-11-24T21:08Z)

```text
bsc-batch          0 workflow pollers, 0 activity pollers, backlog 0
factory-code       0 pollers, backlog 0
factory-coordinator 0 pollers, backlog 0
```

`factory-code` and `factory-coordinator` poller identities disappeared after the
Temporal poller-history window. Railway must register the replacement pollers
for those queues. `bsc-batch` remains intentionally empty.

## Capacity and limits for the batch worker

- 2 vCPU (`CPUQuota=200%`) and 4 GiB (`MemoryMax=4G`) reserved for the unit;
  host has 64 vCPU / 125 GiB, so the limit is conservative.
- `Nice=10`, `IOWeight=100`, `LimitNOFILE=65536`.
- `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`,
  `NoNewPrivileges=true`, `UMask=0077`, state/work/home are the only writable
  paths.
- `Restart=always`, `RestartSec=10`, `TimeoutStopSec=30`.
- Durable state on local disk: `/var/lib/alpha-wiki-factory/state`; ephemeral
  work at `/var/lib/alpha-wiki-factory/work`.

## Dependency on A2

`/opt/alpha-wiki-factory/current/factory/src/agent_factory/batch_worker.py` does
not exist. The unit must stay disabled. When A2 ships the module:

1. Install a release that contains it and sync the venv.
2. Confirm `python -c "import agent_factory.batch_worker"` with the release venv.
3. `systemctl enable --now alpha-wiki-batch-worker.service`.
4. Confirm one workflow and one activity poller on `bsc-batch`.

No paid resource was created by this rollback.
