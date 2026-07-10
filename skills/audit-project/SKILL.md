---
name: audit-project
description: "Run a read-only delivery-readiness audit across git, docs, tests, deploy, security, providers, and tech debt. Produces a structured, evidence-first status report a Claude/Codex session can start or end with. Use for 'where did development stop', 'is deploy ready', 'what to test next', 'can we hand this off', or a founder/PM status snapshot. Read-only: never edits, commits, pushes, or deploys."
argument-hint: "--project <name> [--repo <path> ...] [--period today|24h|week|all|custom] [--focus backend,frontend,sdk,providers,deploy,testing,security,tech-debt,release]"
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
- Do not mark deploy blocked without a proven root cause. If deploy is configured
  and only verification remains, say so explicitly.

## Workflow

1. **Collect inputs**: project name, repo path(s), period, primary branches,
   focus areas, pasted context (chats/logs/roadmap/PR links). Missing is fine.

2. **Generate the audit skeleton** (guarantees structure + invariants):

   ```bash
   uv run python -m tools.project_audit --project "<name>" \
     --repo <path1> --repo <path2> --period <period> \
     --focus <area> --note "<pasted-context marker>" --out <wiki_dir>/outputs/delivery-audit.md
   ```

   The tool emits all 17 sections, the exact status-label legend, an always-present
   security section, provider/business-coverage tables, a read-only git inventory
   per repo, and `not confirmed` defaults for every unproven cell.

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

4. **Root-cause over symptoms.** When a blocker is claimed, trace it; if you
   can't prove a root cause, label it "suspected — not confirmed".

5. **Founder/PM summary stays compact**; technical detail goes in the appendix
   sections. Finish with a concrete **Next 3 Actions**.

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

## Done Criteria

- All 17 sections present; security/tech-debt/release always included for software
  projects.
- Every important status carries evidence or is explicitly `not confirmed`.
- Deploy is not called blocked without a proven root cause.
- The report ends with an actionable Next 3 Actions.

## References

- `tools/project_audit.py`
- `tools/review.py`, `tools/security.py`, `tools/init_audit.py`
- `docs/project-audit.md`
