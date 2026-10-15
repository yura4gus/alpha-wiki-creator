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
