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

1. Detect project and wiki:
   - Prefer `--wiki-dir` when supplied.
   - Otherwise read `CLAUDE.md` `Wiki dir`.
   - Fall back to `wiki/`.

2. Run deterministic backend:
   - `uv run python -m tools.doctor --project-dir .`
   - Add `--refresh` after init or after manual page edits.
   - Add `--strict` for release gates.
   - Add `--platform claude`, `--platform codex`, or `--platform both` when checking a specific runtime.

3. Read the result:
   - `PASS`: ready.
   - `WARN`: usable but incomplete; schedule repair.
   - `FAIL`: block the next lifecycle step until fixed.

4. Route follow-up:
   - Missing wiki/config: run `/alpha-wiki:init`.
   - Missing graph artifacts: rerun with `--refresh` or run `/alpha-wiki:status`.
   - Lint errors: run `/alpha-wiki:lint --fix`, then rerun `doctor`.
   - Missing Claude hooks/CI: rerun init with hooks/CI enabled or copy generated assets.
   - Missing Codex skills: run `python3 scripts/install_codex.py` from the plugin repo.

## Required Output Discipline

Always surface:

- Project path.
- Wiki dir.
- Platform checked.
- Pass/warn/fail counts.
- Blocking failures first in the user summary.
- Concrete next command for every failure.

## Release-Gate Use

Use this sequence for release smoke checks:

```bash
uv run python -m tools.doctor --project-dir . --platform both --refresh --strict
uv run python -m tools.lint --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml --dry-run
uv run python -m tools.review --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml
```

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
