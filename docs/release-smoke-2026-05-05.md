# Alpha-Wiki Release Smoke

- Date: 2026-05-05
- Smoke verdict: PASS
- Command: `.venv/bin/python tools/release_smoke.py`
- Project: temporary fresh project generated under system temp
- Codex home: temporary `CODEX_HOME` with installed Alpha-Wiki skills

## Checks

- PASS `Claude/Codex doctor`: 16 pass, 2 warn, 0 fail
- PASS `Ingest/query/status/review`: 1 ingested page(s), 3 query hit(s)
- PASS `Render exports`: Mermaid, DOT, and static HTML exports exist

## Notes

- Doctor warnings were acceptable for the pre-ingest stage of the smoke path.
- The smoke covered bootstrap, Claude runtime assets, Codex skill install, graph refresh, deterministic ingest, deterministic query, status, review, Mermaid export, DOT export, and static HTML export.
- This is fresh-project smoke evidence for the Alpha-Wiki standalone plugin. It does not claim Gemini support or semantic claim/contract/contradiction tooling.
