---
name: audit-project
description: "Run a read-only delivery-readiness audit across git, docs, tests, deploy, security, providers, and tech debt. Produces a structured, evidence-first status report a Claude/Codex session can start or end with. Use for 'where did development stop', 'is deploy ready', 'what to test next', 'can we hand this off', or a founder/PM status snapshot. Read-only: never edits, commits, pushes, or deploys."
---

# wiki:audit-project — delivery-readiness audit

## Mission

Produce a reliable, evidence-first delivery audit so any session can answer:
where did development stop, what is done / in progress / not started / blocked,
are blockers real or invented, is deploy ready, what remains to test, which
business cases work today, what provider coverage exists, what tech debt remains,
and whether the project can be handed to the next developer/agent.

## Name Contract

`audit-project` means "read-only project delivery-readiness audit". It is not
`/alpha-wiki:review` (wiki-structure review) and not `receiving-code-review`
(per-change review). It never edits, commits, pushes, or deploys, and it never
declares readiness without evidence.

## Hard Rules (read-only)

- **No writes**: no code edits, no commits, no pushes, no deploy changes.
- Only inspect and run **safe read-only** commands (`git status`, `git log`,
  `git rev-list`, reading files, running existing test commands that don't mutate
  state — ask before running anything that could deploy or write).
- **Never hallucinate readiness.** Every important status needs evidence
  (commit hash, file path, command output, PR/MR number, test line, log line).
- Distinguish: confirmed fact · likely assumption · unconfirmed claim · missing
  evidence · real blocker · suspected/non-root-cause blocker.
- If input is incomplete, **do not block** — proceed with available evidence and
  mark confidence low.
- Do not rely only on chat claims; verify against code/git/docs when possible.
- A proven failure of a required step can block deployment before its root cause
  is known. Keep optional failures and missing verification separately labelled.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

1. **Collect inputs**: project name, repo path(s), period, primary branches,
   focus areas, pasted context (chats/logs/roadmap/PR links). Missing is fine.

2. **Choose the requested output**. Use the full skeleton only for a full
   delivery audit. A user-specified A-G report or short status wins over the
   default 17 sections. The backend can print the skeleton to stdout:

   ```bash
   python3 .alpha-wiki/run.py -m tools.project_audit --project "<name>" \
     --repo <path1> --repo <path2> --period <period> \
     --focus <area> --note "<pasted-context marker>"
   ```

   The optional skeleton emits all 17 sections, the exact status-label legend, an always-present
   security section, provider/business-coverage tables, a read-only git inventory
   per repo, and `not confirmed` defaults for every unproven cell. Strict
   read-only creates no report file and runs no status/review backend that
   refreshes graph artifacts. Read existing reports when relevant.

3. **Fill from evidence**, section by section:
   - **Source inventory**: mark each source checked/unavailable + confidence.
   - **Git audit**: per repo — branch, remote, upstream, divergence, recent
     commits, uncommitted/untracked, branch sprawl, unpushed commits, likely
     last-session commits.
   - **Docs/roadmap/wiki vs code**: flag docs-say-done-but-code-doesn't, stale
     docs, conflicting sources of truth, missing/stale release gates.
   - **Testing**: per layer (unit/integration/contract/E2E/smoke/security/perf/
     UI/API/SDK/provider) — command, last green, current result, failing/skipped/
     flaky, coverage gaps, mocks vs real providers. Never claim "tested" without
     evidence.
   - **Business coverage & providers**: fill the matrices; state which cases run
     today with SDK+backend, which need missing provider work, which block release
     (real vs unverified).
   - **Deploy**: separate real blocker · test blocker · missing evidence ·
     operational task · non-blocking risk.
   - **Security**: use the always-present table; cross-check `wiki/security/`.
   - **Tech debt**: classify and prioritize.

4. **Prove the affected step.** Cite the applicable requirement, observed
   failure, affected required step, and smallest fix. A failing required test
   blocks that step even if its root cause needs investigation. An unchecked
   item is unverified; an optional Pages failure is a docs-deployment result.
   Do not add signing, secrets, approvals, or security controls without an
   existing project requirement.

5. Return the requested summary and only useful next actions. Include an
   appendix or three-action list only when it helps or the user asked for it.

## Status Labels (verbatim)

- 🟢 Done / almost closed — 80–100%
- 🟡 In progress / partially ready — 30–79%
- ⚪ Not started / almost not started — 0–29%
- 🔴 Blocked / risk or stopper
- 🔵 Needs review / done but needs verification

## Relationship To Other Skills

- Uses `/alpha-wiki:review` output (scope + security memory + release readiness)
  as one evidence source.
- Reads the init `raw/docs/source-manifest.md` for active scope / out-of-scope.
- `receiving-code-review` (Superpowers) stays a separate per-change review; this
  audit is project-wide. Reference it as the per-PR checklist, don't replace it.

## Codex Native Delegation

Use native Codex subagents only when independent evidence scopes materially
benefit. A small audit stays single-agent. Keep the controller read-only:

1. The controller reads `AGENTS.md` and Alpha-Wiki context, fetches required
   remote metadata once, and records one immutable repository/SHA snapshot.
2. Choose the smallest useful number of read-only agents by repository or
   non-overlapping scope; do not spawn merely to satisfy a default count.
3. Give every agent the same pinned snapshot, a bounded scope and non-scope,
   forbidden actions, evidence format, and terminal status vocabulary.
4. Treat starting assumptions as hypotheses to confirm, refute, or mark
   `UNPROVEN`. Subagents must not fetch shared refs independently.
5. Wait for every agent to reach a terminal state. Reject `STALE_SNAPSHOT`
   results, permit at most one bounded retry, then deduplicate and synthesize.
6. Run dependent contract alignment after the evidence wave when it needs other
   agents' results. Do not pretend dependent work is independent parallel work.
7. Produce one consolidated audit. Do not begin implementation; a writer wave is
   outside this read-only request.

Use the result envelope and truth precedence from
`references/codex-subagent-orchestration.md`.

## Done Criteria

- Requested output and evidence scope are complete; a full audit uses the
  standard skeleton, and a bounded request includes only applicable sections.
- Every important status carries evidence or is explicitly `not confirmed`.
- Blockers identify a proven failure of an applicable required step.
- The response is concise and preserves material unknowns and next actions.

## References

- `tools/project_audit.py`
- `tools/review.py`, `tools/security.py`, `tools/init_audit.py`
- `docs/project-audit.md`
- `references/codex-subagent-orchestration.md`
