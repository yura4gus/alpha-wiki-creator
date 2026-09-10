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
