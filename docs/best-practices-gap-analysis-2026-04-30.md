# Best Practices Gap Analysis — Phase 0

Goal: identify operator and AI ergonomics that make Alpha-Wiki easier to install, understand, maintain, and trust before Phase 1a deep implementation.

## Added Now

| Practice | Status | Notes |
|---|---|---|
| Dual install path | done | README now shows Claude Code and Codex CLI setup. |
| Codex skill adapter | done | `scripts/install_codex.py` installs prefixed `$alpha-wiki-*` skills. |
| Human-readable command meanings | done | Every command explains "Human meaning". |
| Mandatory Gap Check | done | `status_report()` refreshes graph artifacts and reports cross-cutting gaps. |
| Graph color contract | done | Red/green/blue/black/orange/light-grey semantics documented and tested. |
| Color is not cluster | done | Docs clarify that clusters emerge from typed links, not palette grouping. |

## Practices Still Worth Adding

| Practice | Priority | Why it helps |
|---|---|---|
| `doctor` / install verification command | P1 | Gives operators one command to verify Python, uv, Codex/Claude install, hooks, CI, wiki dir, graph files. |
| First-run operator checklist | P1 | Helps a user go from install → init → ingest → status in 10 minutes. |
| Example prompt cards per skill | P1 | Helps AI and operator invoke the right skill with the right inputs. |
| Pressure-test fixtures for skills | P1 | Makes skill behavior measurable, not just documented. |
| Graph QA snapshots | P1 | Verifies that graph exports preserve mixed-color clusters and typed links. |
| Provenance score | P1 | Surfaces pages without source, date, owner, or evidence strength. |
| Open-question owner/timebox | P1 | Prevents open questions from becoming passive notes. |
| Decision freshness policy | P1 | Marks decisions/specs that need review after age or dependency changes. |
| Alias/glossary registry | P1 | Helps AI resolve synonyms and renamed modules without embedding search. |
| Context budget profiles | P2 | Produces small/medium/large `context_brief` variants for different AI tools. |
| Recovery/resume state | P2 | Lets long ingest/evolve operations resume after interruption. |
| Platform compatibility matrix | P2 | Makes Claude/Codex/Gemini capability differences explicit. |

## Skill-Level Improvements To Consider

- `init`: add `doctor` step and platform choice (`claude`, `codex`, `both`).
- `ingest`: require source provenance and extract explicit open questions/risks.
- `query`: cite file paths and line ranges when possible.
- `lint`: split deterministic checks into named modules for easier extension.
- `status`: add health score only after Gap Check is stable.
- `render`: add Mermaid/DOT exports and graph snapshot tests.
- `review`: include provenance, freshness, and cluster-shape checks.
- `rollup`: distinguish activity, decisions, unresolved gaps, and schema changes.
- `spawn-agent`: generate platform-specific instructions for Claude and Codex.

## Phase Recommendation

Treat Codex adapter + graph/status clarity as Phase 0 closure work. Move `doctor`, prompt cards, pressure fixtures, provenance score, and graph QA snapshots into Phase 1a because they need executable checks and user-facing examples.
