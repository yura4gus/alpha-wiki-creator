# Final Release Readiness Audit — 2026-05-04

Goal: independently check whether Alpha-Wiki is ready for a final packaged release candidate.

## Verdict

Current verdict: **READY** for the current local packaged release candidate.

Reason: P0 packaging blockers are closed and deterministic sanity checks now exist for contracts, claims, and explicit contradictions.

Historical note: at the time of this audit, public install depended on pushing the audited commits. That follow-up is now closed: public `origin/main` contains the audited state and tag `v0.1.0-beta.1` is published.

## What Is Release-Strong

| Area | Status | Evidence |
|---|---|---|
| Core lifecycle | pass | `doctor -> ingest -> graph -> query -> lint/status/review -> render -> rollup` has deterministic tools. |
| Claude path | pass | Commands, hooks, CI templates, doctor checks. |
| Codex path | pass with limitations | `scripts/install_codex.py`, prefixed skills, doctor platform check. |
| Graph semantics | pass | Typed cluster links, Obsidian colors, Mermaid/DOT exports, Graph QA tests. |
| Static read-only export | pass | `tools/render_html.py`. |
| Test suite | pass | Latest verified result: `129 passed`. |
| Quickstart | pass | `docs/quickstart.md`. |
| Changelog | pass | `CHANGELOG.md`. |
| Fresh install smoke | pass | `docs/release-smoke-2026-05-05.md`. |
| Packaging/version metadata | pass | `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and changelog entry are aligned. |
| Contract/claim sanity checks | pass | `tools/contracts_check.py`, `tools/claims_check.py`, `tools/contradiction_detector.py`. These are deterministic checks, not semantic truth resolution. |

## Blocking Gaps

| Gap | Severity | Why it blocks final release |
|---|---|---|
| None currently recorded | - | P0 release blockers are closed as of 2026-05-05. |

## Non-Blocking But Important

| Gap | Severity | Release handling |
|---|---|---|
| Unified health score missing | P1 | Status sections exist; score can wait. |
| Codex has no hook parity | P1 | Documented limitation, not a blocker if release says "adapter", not "full parity". |
| Gemini unsupported | P2 | Must be clearly excluded. |

## Final-Release Gate Checklist

| Gate | Current State |
|---|---|
| Full test suite | pass: `129 passed` |
| Release readiness audit tool | pass: `tools/release_audit.py` exists |
| Platform compatibility matrix | pass: `docs/platform-compatibility-matrix.md` |
| Quickstart | pass: `docs/quickstart.md` |
| Changelog | pass: `CHANGELOG.md` |
| Fresh install smoke | pass: `docs/release-smoke-2026-05-05.md` |
| Contract/claim sanity checks | pass: contract, claim, and explicit contradiction tools exist |
| Plugin metadata/version/tag | pass for metadata/version; tag should be created at publish time |

## Recommended Next Work

1. Create the git tag only when publishing the release artifact.
2. Re-run `.venv/bin/python -m tools.release_audit --root .` immediately before tagging.
3. Improve unified health scoring and Codex automation parity in the next hardening pass.
