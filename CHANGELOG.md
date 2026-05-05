# Changelog

All notable Alpha-Wiki release changes are recorded here.

## [0.1.0] - 2026-05-05

### Added

- Claude Code plugin surface with 11 operations: `init`, `doctor`, `ingest`, `query`, `lint`, `evolve`, `status`, `spawn-agent`, `render`, `review`, and `rollup`.
- Codex adapter installer that writes prefixed `$alpha-wiki-*` skills.
- Deterministic wiki engine for markdown/frontmatter parsing, graph rebuilds, context brief generation, and open-question extraction.
- Deterministic lifecycle tools for doctor, ingest, query, lint, status, review, rollup, Mermaid/DOT graph export, static HTML export, release audit, and fresh-install smoke.
- Trust-depth tools for contracts, claims, and contradictions.
- Obsidian graph semantics where colors represent node roles and clusters are formed by typed links such as `belongs_to`, `service`, `implements`, and `affects`.
- Release documentation: quickstart, platform compatibility matrix, final-release hardening plan, lifecycle automation audit, and release readiness audit.

### Release Notes

- Claude Code is the primary supported runtime.
- Codex is supported through the adapter and deterministic tools; Codex hook parity is not included.
- Gemini is not packaged or supported in this release.
- Semantic trust tools now cover contract ownership/consumers, claim provenance/freshness, and deterministic contradiction detection.
