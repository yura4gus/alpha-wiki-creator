# Final Release Readiness Audit — 2026-05-04

Goal: independently check whether Alpha-Wiki is ready for a final public release.

## Verdict

Current verdict: **READY_WITH_WARNINGS** for the current packaged release.

Reason: P0 packaging blockers are closed. The remaining warning is semantic trust depth: claims, contracts, and contradiction tooling are deferred and must stay explicit in release notes.

## What Is Release-Strong

| Area | Status | Evidence |
|---|---|---|
| Core lifecycle | pass | `doctor -> ingest -> graph -> query -> lint/status/review -> render -> rollup` has deterministic tools. |
| Claude path | pass | Commands, hooks, CI templates, doctor checks. |
| Codex path | pass with limitations | `scripts/install_codex.py`, prefixed skills, doctor platform check. |
| Graph semantics | pass | Typed cluster links, Obsidian colors, Mermaid/DOT exports, Graph QA tests. |
| Static read-only export | pass | `tools/render_html.py`. |
| Test suite | pass | Latest recorded result: `114 passed`. |
| Quickstart | pass | `docs/quickstart.md`. |
| Changelog | pass | `CHANGELOG.md`. |
| Fresh install smoke | pass | `docs/release-smoke-2026-05-05.md`. |
| Packaging/version metadata | pass | `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and changelog entry are aligned. |

## Blocking Gaps

| Gap | Severity | Why it blocks final release |
|---|---|---|
| None currently recorded | - | P0 release blockers are closed as of 2026-05-05. |

## Non-Blocking But Important

| Gap | Severity | Release handling |
|---|---|---|
| Claim/contradiction detector missing | P1 | Acceptable for beta; must be explicit in release notes. |
| Contracts-check tool missing | P1 | Important for software-project users; can be next hardening item. |
| Unified health score missing | P1 | Status sections exist; score can wait. |
| Codex has no hook parity | P1 | Documented limitation, not a blocker if release says "adapter", not "full parity". |
| Gemini unsupported | P2 | Must be clearly excluded. |

## Final-Release Gate Checklist

| Gate | Current State |
|---|---|
| Full test suite | pass: `114 passed` |
| Release readiness audit tool | pass: `tools/release_audit.py` exists |
| Platform compatibility matrix | pass: `docs/platform-compatibility-matrix.md` |
| Quickstart | pass: `docs/quickstart.md` |
| Changelog | pass: `CHANGELOG.md` |
| Fresh install smoke | pass: `docs/release-smoke-2026-05-05.md` |
| Plugin metadata/version/tag | pass for metadata/version; tag should be created at publish time |

## Recommended Next Work

1. Implement or explicitly continue deferring `tools/claims_check.py`, `tools/contracts_check.py`, and `tools/contradiction_detector.py`.
2. Create the git tag only when publishing the release artifact.
3. Re-run `.venv/bin/python tools/release_audit.py --root .` immediately before tagging.
