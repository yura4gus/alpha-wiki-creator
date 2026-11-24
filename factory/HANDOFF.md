# Factory V1 handoff

- **From:** Claude Super Master (factory integration session, 2026-11-24)
- **To:** Next factory owner / operator
- **Context:** v0.8.2 source release. `TaskWorkflow` remains the executor and
  approval authority; Temporal Agent Harness 0.11.0 is the coordination surface;
  every model call still runs through the OpenCode CLI. PRs #4, #5, #6 and #3
  merged after hosted CI was restored.
- **Completed:** Factory V1 and Harness integration; typed
  submit/status/approve/cancel; native Console/API; one-command stack; worker
  restart/reconnect; three real OpenCode tasks with live review; Temporal Cloud
  dev smoke; factory CI job; release artifacts and runbooks.
- **Unfinished (P1/P2):**
  - cmux automation is manual; no reliable CLI contract.
  - Cost/token telemetry is elapsed time only; OpenCode does not expose per-run
    cost to the adapter.
  - Browser UI is covered through the Console HTTP API, not a browser test.
  - xPlan write-back needs a conditional, conflict-safe write.
  - GitLab skills registry delivery and 50–100 worker scale remain deferred.
- **Files:** `factory/README.md`, `factory/HARNESS.md`, `factory/RELEASE.md`,
  `factory/harness/agents.toml`, `factory/src/agent_factory/{connection,launcher}.py`,
  `factory/src/agent_factory/harness/`, `docs/roadmap-execution.md` §§30–31.
- **Contracts:**
  - one task = one `TaskWorkflow` = one worktree = one file owner;
  - `TaskWorkflow.decide` is the only approval authority;
  - Harness tools must not become a second approval queue;
  - xPlan stays dry-run;
  - no direct provider HTTP client or provider credential in this package;
  - local loopback stays plaintext even when `TEMPORAL_API_KEY` is exported.
- **Risks:** Harness 0.11.0 is pre-1.0 and upgrades need schema regeneration;
  the Console is loopback-only with no authentication; the Cloud API key lives
  outside the repository and expires; GitHub checks must stay green.
- **Decisions:** Keep Temporal Core plus the thin CLI adapter rather than adopt
  the Harness SDK loop. Keep the factory package optional so plugin users are
  unaffected. Do not bypass checks or write to xPlan.
- **Next action:** add token/cost telemetry from OpenCode JSON output without
  introducing a provider client, then rerun the Harness live suite.
