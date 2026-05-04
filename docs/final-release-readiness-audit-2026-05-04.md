# Final Release Readiness Audit — 2026-05-04

Goal: independently check whether Alpha-Wiki is ready for a final public release.

## Verdict

Current verdict: **BLOCKED for final v1.0**, acceptable for a beta/hardening release.

Reason: the lifecycle backbone is now real and tested, but release packaging docs and semantic trust tooling are not complete.

## What Is Release-Strong

| Area | Status | Evidence |
|---|---|---|
| Core lifecycle | pass | `doctor -> ingest -> graph -> query -> lint/status/review -> render -> rollup` has deterministic tools. |
| Claude path | pass | Commands, hooks, CI templates, doctor checks. |
| Codex path | pass with limitations | `scripts/install_codex.py`, prefixed skills, doctor platform check. |
| Graph semantics | pass | Typed cluster links, Obsidian colors, Mermaid/DOT exports, Graph QA tests. |
| Static read-only export | pass | `tools/render_html.py`. |
| Test suite | pass | Latest recorded result: `111 passed`. |

## Blocking Gaps

| Gap | Severity | Why it blocks final release |
|---|---|---|
| `CHANGELOG.md` missing | P0 | Users need release notes and migration visibility. |
| `docs/quickstart.md` missing | P0 | A new user needs a reliable 10-minute path. |
| Fresh install smoke not recorded | P0 | Tests cover internals; release needs install/init/ingest/query/status smoke evidence. |
| Packaging/version gate not completed | P0 | Plugin metadata, version, changelog, and tag are not release-final. |

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
| Full test suite | pass: `111 passed` |
| Release readiness audit tool | pass: `tools/release_audit.py` exists |
| Platform compatibility matrix | pass: `docs/platform-compatibility-matrix.md` |
| Quickstart | fail |
| Changelog | fail |
| Fresh install smoke | fail until executed and recorded |
| Plugin metadata/version/tag | fail until release prep |

## Recommended Next Work

1. Add `docs/quickstart.md`.
2. Add `CHANGELOG.md`.
3. Run and record fresh install smoke for Claude and Codex.
4. Add release notes that explicitly defer claims/contradictions and Gemini.
5. Then rerun `tools/release_audit.py`.
