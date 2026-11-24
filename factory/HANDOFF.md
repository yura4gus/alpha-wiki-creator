# Factory handoff — remote pilot (2026-11-25)

- **From:** Claude Super Master (remote factory sprint)
- **To:** Next factory operator / owner
- **Context:** AlphaWiki v0.8.2 source, Railway control plane, Temporal Cloud
  `alpha-dev.n3kw9`, external compute worker for `bsc-batch`. Private Railway
  IDs and credentials live in the operator record under
  `~/.config/alpha-wiki-factory/`, not in this repository.
- **Completed:**
  - Railway pilot: private `agent-factory-runtime` (factory worker +
    coordinator) and `agent-factory-harness` (session manager/API/console), no
    public domains, persistent `/data` volume, restart `ALWAYS`.
  - Temporal pollers: one workflow+activity pair each on `factory-code` and
    `factory-coordinator`; external `bsc-batch` worker on dedicated compute.
  - Batch runtime: frozen manifests, allowlisted Python/Bash/Rust units,
    checkpoints, DQ, duplicate/cancel/crash-resume and receipt.
  - OpenCode: pinned v2.3.0, paid `opencode-go/deepseek-v4.1-flash`, independent
    review and JSON token/cost telemetry in receipt metrics.
  - Remote coding: Railway task `task-railway-final-20261124T225707Z` reached
    `PR_OPEN` with tests, `APPROVE`, approval and telemetry.
  - Remote BSC read-only: A2 job through `bsc-batch`, 25/25 DQ checks, outputs
    read back; restart test preserved progress and no duplicate effects.
  - ITSPlan adapter: snapshot-fed, read-only, delegates to
    `tools/xplan_dry_run`; no automatic writes.
- **Unfinished / blockers:**
  - ITSPlan API returns 401 and the ITSPlan Railway project is not visible to
    the authorized account; issue binding and real readback pending.
  - Full BSC canary #2 remains `BLOCKED_BY_VERIFIED_DEPENDENCY` (MISSING-1..6);
    `BSC_V1 = NO`.
  - No public Console authentication; keep it private.
  - Railway pilot has no hard cgroup limit; one replica plus bounded activities.
  - Real `gh` PR path still needs an authorized sandbox repository.
  - cmux remains manual.
- **Files:** `factory/README.md`, `factory/HARNESS.md`, `factory/RAILWAY.md`,
  `factory/TELEMETRY.md`, `factory/REMOTE-ACCEPTANCE.md`,
  `factory/deploy/`, `factory/src/agent_factory/batch/`,
  `factory/src/agent_factory/{telemetry,xplan,connection}.py`,
  roadmap §32.
- **Contracts:**
  - TaskWorkflow owns coding execution/approval/PR; BatchWorkflow owns
    deterministic data units and never calls a model.
  - xPlan stays read-only; no automatic transition.
  - One task = one worktree; one unit = one checkpoint fence.
  - No provider HTTP client; all models through OpenCode.
  - No private host/IP/credential in the public repository.
- **Risks:** Harness 0.11.0 is pre-1.0; Railway has no hard CPU/RAM cgroup in
  the pilot; old Temporal pollers linger for ~5 minutes after redeploy; the
  Cloud API key expires and must be rotated via the private env file; macOS
  cannot enforce `RLIMIT_AS` (Linux external compute does).
- **Decisions:** Railway is the lightweight control plane; dedicated servers
  are compute only. Deploy from the merged main SHA on a new release only after
  CI; do not reopen v0.8.2. Keep ITSPlan writes disabled until conditional
  authorization is proven.
- **Next action:** obtain an authorized ITSPlan API token for a read-only issue
  snapshot, run `xplan.bind_issue` + `xplan.task_spec`, submit that issue
  through the coordinator, and read back the dry-run transition; then request
  owner GO for BSC canary #2 MISSING-1..6.
