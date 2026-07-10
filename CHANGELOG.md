# Changelog

All notable Alpha-Wiki release changes are recorded here.

## [0.3.0] - 2026-07-10

Operational-hardening release driven by the first real-world use (Zamio / ZamWallet workspace), where `init` proposed 253 candidate files dominated by `repos/*/vendor/**` noise. No breaking changes to existing skills or wiki architecture.

### Added

- **Init source curation** (`tools/init_audit.py`): expanded default folder exclusions (`vendor`, `node_modules`, `.next`, `coverage`, `.cache`, `tmp`, `logs`, build/dist/target, and more); per-file classification into operational categories (canonical, adr, architecture, api-contract, security, release, product, impl-notes, third-party, generated, duplicate, unknown); third-party/licensing and lockfile detection; duplicate/source-of-truth resolution (prefer a repo's own `docs/` over workspace mirrors); and a focused `batch1_plan` that prefers durable memory and drops noise.
- **Scope control**: `InitScope` (active / out-of-scope / deferred / source-of-truth notes / human decisions) recorded in a restructured `raw/docs/source-manifest.md` with explicit sections, so agents don't reconstruct corpus logic from chat history.
- **Security memory** (`tools/security.py`): deterministic `scaffold_security_pages` (7 minimal, non-hallucinated placeholder pages), capture detection, and `security_release_blockers`. `/alpha-wiki:review` now reports `## Scope`, `## Security Memory`, and `## Release Readiness` (NOT READY when scope is unrecorded, security memory is incomplete, or structural errors remain).
- **Agent-start guidance**: README "Daily agent start" now lists the six questions a new agent must answer (active scope, out-of-scope, canons, frozen areas, pre-coding gates, next safe action).
- **spawn-agent contract**: generated prompts must carry active scope, out-of-scope/deferred modules, and security constraints as hard limits.
- **Tests**: `tests/unit/test_init_source_filtering.py` and `tests/unit/test_security_memory.py` (vendor exclusion, classification, duplicate/source-of-truth, scope recording, Batch 1 excludes noise, security placeholders, review security/scope sections, lint safety), plus a spawn-agent scope/security guardrail.

### Changed

- Version bump `0.2.1` -> `0.3.0`.

## [0.2.1] - 2026-07-10

### Added

- Version-drift guardrail test (`tests/unit/test_release_guardrails.py`) that fails when `plugin.json`, `marketplace.json`, and `pyproject.toml` versions disagree, or when the reinstall docs, release checklist, or the 11 expected skills go missing. Prevents the 0.1.0 stale-plugin class of bug from recurring.
- README "Daily agent start" and "Recommended lifecycle" guidance so Alpha-Wiki is used as the first context source before Claude/Codex begins coding.
- spawn-agent "Generated Agent Prompt Contract" section documenting the seven required elements of a bounded subagent prompt (scope, constraints, context, forbidden actions, gates, output format, handoff).

### Changed

- Version bump `0.2.0` -> `0.2.1` (operational-hardening release; no behavior or schema changes).

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
