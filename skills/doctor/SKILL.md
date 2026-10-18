---
name: doctor
description: "Run a deterministic Alpha-Wiki install and lifecycle health check. Use before first ingest, after init, when hooks/CI feel broken, when Codex/Claude setup is uncertain, or before release smoke testing."
---

# wiki:doctor - install and lifecycle verifier

## Mission

Give the operator and AI one reliable command that answers: "Is this Alpha-Wiki installation wired well enough to trust the next operation?"

## Name Contract

`doctor` means "verify runtime readiness". It does not synthesize wiki knowledge and does not edit source pages. With `--refresh`, it may rebuild generated graph artifacts because `wiki/graph/**` is derived state.

## Workflow

If an existing wiki predates the isolated launcher, report the missing runtime
and the upgrade command below. Run it only as part of an authorized init/upgrade:
`UV_PROJECT_ENVIRONMENT="<runtime_root>/.venv" uv run --project <runtime_root> --directory <runtime_root> --no-dev python -m scripts.bootstrap_cli --target <absolute-project> --runtime-only`.
It preserves schema, contracts, wiki, CI settings, and hook routing. A read-only
health check can use the installed plugin environment with `--project-dir`
pointing at the target. Do not replace product dependencies to make the old
invocation work.

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

1. Detect project and wiki:
   - Prefer `--wiki-dir` when supplied.
   - Otherwise read `AGENTS.md` `Wiki dir`.
   - Fall back to `wiki/`.

2. Run deterministic backend:
   - `python3 .alpha-wiki/run.py -m tools.doctor --project-dir .`
   - Add `--refresh` after init or after manual page edits.
   - Add `--strict` only when requested or required by existing release policy.
   - Add `--platform claude`, `--platform codex`, or `--platform both` when checking a specific runtime.

3. Read the result:
   - `PASS`: ready.
   - `WARN`: usable but incomplete; schedule repair.
   - `FAIL`: identify the affected operation and concrete failure; block only
     a required step that depends on the failed capability.

4. Route follow-up:
   - Missing wiki/config: run `/alpha-wiki:init`.
   - Missing graph artifacts: rerun with `--refresh` or run `/alpha-wiki:status`.
   - Lint errors: run `/alpha-wiki:lint --fix`, then rerun `doctor`.
   - Missing optional hooks/CI: report the limitation. Install them only when
     chosen or required for the operation being checked.
   - Missing/stale Codex plugin or skills: run `python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone` from the Alpha-Wiki repo, then start a new Codex task.
   - Missing Codex project contract/hooks: rerun init with session hooks enabled, merge the Alpha-Wiki section into an existing `AGENTS.md`, and review hooks with `/hooks`.
   - Legacy `CLAUDE.md`: merge only unique project guidance into `AGENTS.md`, then remove it; never use it as a runtime contract.

## Required Output Discipline

Always surface:

- Project path.
- Wiki dir.
- Platform checked.
- Pass/warn/fail counts.
- Blocking failures first in the user summary.
- Concrete next command for every failure.

## Release-Gate Use

For a lifecycle release check, select the supported platform and applicable
checks below. Ordinary warnings remain warnings unless the existing policy
requires strict mode. Do not enable an unused platform just to clear a warning.

```bash
python3 .alpha-wiki/run.py -m tools.doctor --project-dir . --platform <claude|codex|both> --refresh
python3 .alpha-wiki/run.py -m tools.lint --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml --dry-run
python3 .alpha-wiki/run.py -m tools.review --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml
```

## Codex Native Delegation

Do not spawn subagents for doctor. Run the deterministic backend once in the
controller so all checks observe one environment and one filesystem state. If
doctor exposes independent follow-up investigations, delegate those as separate
tasks only after recording the doctor result; do not run competing doctor
instances.

## Done Criteria

- The user can tell whether install/runtime is ready.
- The report distinguishes environment issues from wiki content issues.
- No source wiki page is mutated.
- Generated graph artifacts are only mutated when `--refresh` is explicit.

## References

- `tools/doctor.py`
- `tools/lint.py`
- `tools/status.py`
- `docs/final-release-hardening-plan.md`
- `references/codex-subagent-orchestration.md`
