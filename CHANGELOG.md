# Changelog

All notable Alpha-Wiki release changes are recorded here.

## [0.2.0] - 2026-07-10

### Fixed

- Made the clustered-lifecycle rollup integration test deterministic by pinning the rollup period to the activity window instead of depending on the wall-clock date the suite runs on.

### Changed

- Bumped plugin, marketplace, and package version to `0.2.0` so `claude plugin update` reliably detects and pulls the release. Version was stuck at `0.1.0` across 39 commits, which caused installs to serve a stale build without the `doctor`, `review`, and `rollup` skills.
- Scoped Obsidian graph colors to wiki paths and made the wiki folder the Obsidian vault root.
- Hardened static HTML export links and the release-process audit path.

## [0.1.0] - 2026-05-05

### Added

- Claude Code plugin surface with 11 operations: `init`, `doctor`, `ingest`, `query`, `lint`, `evolve`, `status`, `spawn-agent`, `render`, `review`, and `rollup`.
- Codex adapter installer that writes prefixed `$alpha-wiki-*` skills.
- Init source corpus audit that discovers existing project documents, proposes raw placement, target wiki slots, and gradual ingest batches.
- Deterministic wiki engine for markdown/frontmatter parsing, graph rebuilds, context brief generation, and open-question extraction.
- Deterministic lifecycle tools for doctor, ingest, query, lint, status, review, rollup, Mermaid/DOT graph export, static HTML export, release audit, and fresh-install smoke.
- Deterministic sanity-check tools for contracts, claims, and explicit contradictions.
- Beta hardening docs with small API, code, and feature contract examples.
- Obsidian graph semantics where colors represent node roles and clusters are formed by typed links such as `belongs_to`, `service`, `implements`, and `affects`.
- Release documentation: quickstart, platform compatibility matrix, final-release hardening plan, lifecycle automation audit, and release readiness audit.

### Release Notes

- Claude Code is the primary supported runtime.
- Codex is supported through the adapter and deterministic tools; Codex hook parity is not included.
- Gemini is not packaged or supported in this release.
- Deterministic contract/claim checks cover contract ownership/consumers, claim provenance/freshness, and explicit contradiction links. They are not semantic truth resolution.
