# Alpha-Wiki Release Smoke - 2026-09-10

- Version: `0.6.0`
- Smoke verdict: PASS
- Command: `uv run python -m tools.release_smoke`

## Evidence

- PASS `Claude/Codex doctor`: fresh generated project and both runtime surfaces were detected.
- PASS `Ingest/query/status/review`: one source was ingested and returned three query hits.
- PASS `Render exports`: Mermaid, DOT, and static HTML outputs were created.

This smoke runs in a temporary directory and does not depend on the current
repository's installed plugin cache.

## Maintenance Release Verification - 2026-10-15

- Version: `0.6.1`; isolated release worktree based on public `main`.
- `uv sync --dev`: PASS.
- `.venv/bin/python -m pytest`: `204 passed`.
- `.venv/bin/python -m tools.release_audit --root .`: `READY`, 8 pass, 0 warn, 0 fail.
- `.venv/bin/python -m tools.release_smoke`: `PASS`; fresh Claude/Codex doctor
  reported 23 pass, 1 warn, 0 fail; ingest/query/status/review and
  Mermaid/DOT/HTML exports passed.
- All 16 skill files passed the skill validator.
- The case replays cover instruction behavior, not a live Claude inference run.
  The attempted live Claude check could not authenticate because its OAuth
  session expired. Live Claude execution remains unverified for this patch.
- Pending schema migration, document-worker changes, and AgentOps extensions
  in the development checkout are not part of this maintenance release.

## Runtime Release Verification - 2026-10-18

- Version: `0.6.2`, isolated from the development working tree on top of 0.6.1.
- `.venv/bin/python -m pytest -o addopts='' -q`: `215 passed`.
- `.venv/bin/python -m tools.release_audit --root .`: `READY`, 8 pass, 0 warn, 0 fail.
- `.venv/bin/python -m tools.release_smoke`: `PASS`; fresh doctor reported
  24 pass, 2 warn, 0 fail; ingest/query/status/review and graph/HTML exports passed.
- Four subprocess lifecycle cases cover fresh/brownfield projects for Claude and
  Codex hook adapters, including packaged Codex bootstrap, graph refresh,
  upgrade, custom `.wiki`, spaces, and a prepared runtime without `uv`.
- Product `pyproject.toml`, `uv.lock`, `requirements.txt`, `package.json`, and
  virtualenv remain unchanged. `click` stays absent from the product virtualenv.
- Runtime-only upgrade additionally preserves custom schema, `CLAUDE.md`,
  `AGENTS.md`, wiki/graph files, CI settings, and hook routing; dry-run writes
  nothing. Codex package upgrades override inherited product environment paths
  explicitly when bootstrapping from the plugin environment.
- Subprocess cases use cached dependency wheels offline in fresh environments;
  they do not require private services or live model credentials.
- `CLAUDE.md` generation, schema evolution, and AgentOps state remain compatible
  with 0.6.1. No document worker, schema migration, or new AgentOps state is
  present. Live Claude/Codex model sessions are not part of these tests.
