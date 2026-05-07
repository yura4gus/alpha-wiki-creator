# Final Release Hardening Plan

Goal: turn the current Alpha-Wiki/AgentOps design package into a release-ready product set: installable, understandable, testable, and reliable for a real operator and for AI agents that need fast context.

This plan consolidates the key improvements discovered during Phase 0:

- Karpathy LLM-Wiki compliance audit.
- Codex/OpenAI adapter pass.
- Obsidian graph semantics review.
- Best-practices gap analysis.
- User requirement: documents must form meaningful clusters, while colors label node roles inside those clusters.

## Release Target

| Release | Scope | Gate |
|---|---|---|
| Alpha-Wiki v1.0 | Standalone memory/wiki plugin: Claude Code + Codex adapter, typed markdown memory, graph discipline, lint/status/review/rollup, Obsidian + export layer. | Fresh install → init → ingest → query → lint → status → review works on a real project. |
| AgentOps future | Adjacent/future product, not part of the Alpha-Wiki first-run or beta release gate. | Tracked separately. |
| Combined future | Optional future integration, not part of the Alpha-Wiki first-run or beta release gate. | Tracked separately. |

## Implementation Progress

| Item | Status | Evidence |
|---|---|---|
| R0.1 cluster semantics base | in-progress | `owned_by/source` graph edges, `cluster-link-gap` lint, status `Cluster gap`, cluster frontmatter templates, unit tests. |
| Lifecycle automation audit | done | `docs/alpha-wiki-lifecycle-automation-audit-2026-05-01.md`, lifecycle closure integration test. |
| R0.7 doctor command | done | `tools/doctor.py`, `/alpha-wiki:doctor`, `skills/doctor`, unit tests. |
| R0.8 first-run checklist | done | `docs/quickstart.md`, README/docs index links, release smoke usage. |
| Init source corpus audit | done | `tools/init_audit.py`, init skill/command workflow, source-manifest tests. |
| R0.2 Graph QA exports | done | `tools/render_mermaid.py`, `tools/render_dot.py`, mixed-role cluster export tests. |
| R0.6 trust report base | in-progress | Status/review now include cluster health, provenance score, freshness, open-question follow-up, and next actions. |
| Contract/claim sanity checks | done | `tools/contracts_check.py`, `tools/claims_check.py`, `tools/contradiction_detector.py`, unit tests, release-audit gate. These are deterministic checks, not semantic contradiction intelligence. |
| R0.4 query helper | done | `tools/wiki_search.py`, query CLI, citation/ranking tests. |
| R0.3 ingest pipeline MVP | in-progress | `tools/ingest_pipeline.py`, local-file ingest CLI, provenance/log/graph/lint/resume pressure tests. |
| R1.10 static HTML export | done | `tools/render_html.py`, static read-only HTML bundle tests. |
| R1.9 platform compatibility matrix | done | `docs/platform-compatibility-matrix.md` documents Claude primary support, Codex adapter support, and Gemini deferral. |
| Release readiness audit | done | `tools/release_audit.py`, `docs/final-release-readiness-audit-2026-05-04.md`, release-audit unit tests. |
| R0.10 release packaging P0 | done | `CHANGELOG.md`, version metadata audit, marketplace description updated to 11 skills, fresh smoke evidence. |

## Release Principles

1. Markdown memory remains inspectable plain files.
2. `ingest`, `query`, and `lint` remain the canonical Karpathy operations.
3. Deterministic tools handle repeatable checks and graph rebuilds.
4. LLM work is reserved for classification, synthesis, and judgement.
5. Clusters are mandatory and built by typed ownership links.
6. Colors label node roles inside clusters; colors must not create separate color-only clusters.
7. No "done" without verification evidence.
8. Claude Code and Codex UX must both be documented.

## P0 — Release Blockers

These must be done before a final public release.

| ID | Improvement | Why | Files / Modules | Acceptance | Tests |
|---|---|---|---|---|---|
| R0.1 | Cluster semantics and ownership links | Documents must not float as random colored nodes. AI needs machine-readable grouping. | `tools/wiki_engine.py`, `tools/lint.py`, `skills/ingest`, `skills/lint`, `skills/status`, `skills/review`, `assets/frontmatter/*` | Entity pages support `belongs_to`, `owned_by`, `affects`, `implements`, `service`, `target_module`; lint flags unclustered docs/features/contracts; status/review report cluster gaps. | Unit tests for cluster link extraction, lint violations, status gap output; sample wiki graph fixture. |
| R0.2 | Graph QA snapshots | Verify that Obsidian and machine graph represent mixed-role clusters correctly. | `assets/obsidian/*`, `tools/render_mermaid.py`, `tools/render_dot.py`, tests fixtures | Sample graph contains mixed red/green/blue/black/orange nodes in one service cluster; no color-only cluster assumption. | Snapshot tests for Obsidian config, Mermaid/DOT export, `edges.jsonl`. |
| R0.3 | Deterministic ingest pipeline | Ingest is the growth path; final release needs repeatable provenance, page creation, and graph updates. | `tools/ingest_pipeline.py`, `tools/classifier.py`, `skills/ingest` | Ingest writes pages with frontmatter, provenance, cluster links, open questions, log entry, graph rebuild, lint summary. | Pressure tests: PRD, ADR, OpenAPI, transcript, contradicting source, oversized source, unparseable source. |
| R0.4 | Deterministic query helper | Agent must find relevant pages without embeddings or guesswork. | `tools/wiki_search.py`, `skills/query` | Query reads context brief + index, ranks candidate pages by slug/title/frontmatter/wikilinks, cites pages and line references where possible. | Query pressure tests: no answer, stale answer, conflicting evidence, cross-cluster answer. |
| R0.5 | Full lint check set | Lint must protect graph/wiki integrity before release. | `tools/lint.py`, `tools/lint_checks/*`, `skills/lint` | Checks include broken links, missing reverses, orphan/unclustered pages, required frontmatter, duplicate slugs/aliases, dependency rules, stale metadata, missing provenance, contracts without owners/consumers. | Per-check unit tests; `--fix`, `--suggest`, `--dry-run`, CI/pre-commit tests. |
| R0.6 | Status/review trust reports | Operator needs one clear picture of health, gaps, provenance, freshness, and clusters. | `tools/status.py`, `tools/review.py`, `skills/status`, `skills/review` | Reports include Gap Check, cluster health, provenance score, freshness, open-question owner/timebox, lint summary, next actions. | Status/review pressure tests on empty, small, broken, stale, and 100-page wikis. |
| R0.7 | Doctor command | Operators need one command to verify install and runtime. | `tools/doctor.py`, `skills/doctor` or command entry, README | Verifies Python, uv, tools import, Claude/Codex install notes, wiki dir, config, hooks, CI, graph artifacts, permissions. | Unit tests with mocked missing/present dependencies; smoke run in temp project. |
| R0.8 | First-run checklist | New user must reach value quickly. | README, generated `assets/readme.j2`, `docs/quickstart.md` | 10-minute path: install → init → ingest sample → status → query → Obsidian open. | Template render tests; manual smoke checklist. |
| R0.9 | Codex adapter hardening | Codex support must be more than docs. | `scripts/install_codex.py`, `docs/codex-adapter.md`, generated skills | Installer supports dry-run, target dir, update mode, validation; generated skills have valid YAML and prefixed names. | Existing Codex installer tests plus update/idempotency tests. |
| R0.10 | Release packaging | User can install the final artifact cleanly. | `.claude-plugin/*`, marketplace metadata, CHANGELOG, tags | Plugin metadata accurate, versions bumped, changelog complete, install docs current. | Fresh machine/manual install, CI green. |

## P1 — Release Quality

These should be completed before v1.0 unless they threaten schedule. If deferred, release notes must say so explicitly.

| ID | Improvement | Why | Acceptance |
|---|---|---|---|
| R1.1 | Example prompt cards per skill | Helps operator and AI invoke skills correctly. | Each skill has 3 examples: common, edge case, wrong-use redirect. |
| R1.2 | Pressure-test fixtures for every skill | Makes skill behavior measurable. | `tests/skills/*_pressure.py` exists for all user-facing skills. |
| R1.3 | Provenance score | Surfaces unsupported pages. | Status/review score pages by source path, source date, owner, evidence strength. |
| R1.4 | Open-question owner/timebox | Prevents passive open questions. | Open questions support owner/due/status; stale open questions appear in status/review. |
| R1.5 | Decision freshness policy | Old decisions/specs need review. | Stable/accepted pages older than policy threshold are surfaced unless explicitly exempt. |
| R1.6 | Alias/glossary registry | AI needs to resolve renames and synonyms. | `wiki/glossary` or `wiki/aliases.yaml` maps terms/slugs/renames; query/lint use it. |
| R1.7 | Context budget profiles | Different tools need different context sizes. | `context_brief.small.md`, `context_brief.md`, `context_brief.large.md` or equivalent CLI flag. |
| R1.8 | Recovery/resume state | Long ingest/evolve should survive interruption. | Ingest/evolve writes resumable state and can continue safely. |
| R1.9 | Platform compatibility matrix | Claude/Codex/Gemini differences must be explicit. | Matrix covers install, skills, hooks, subagents, browser, CI, limitations. |
| R1.10 | HTML/Mermaid/DOT exports | Visual QA beyond Obsidian. | Render modes produce deterministic files and snapshots. |

## P2 — Post-Release Enhancements

These are valuable, but should not block a stable v1.0.

| ID | Improvement | Trigger |
|---|---|---|
| R2.1 | BM25 local search | Wiki grows beyond easy index/context traversal. |
| R2.2 | Embedding backend reconsideration | Only if BM25 and file graph are insufficient; requires revisiting ADR-003. |
| R2.3 | Multi-project memory | Users operate several related repos. |
| R2.4 | Static web UI | Obsidian/GitHub view is insufficient for non-technical users. |
| R2.5 | Rich semantic contradiction graph | Real usage shows persistent unresolved claims. |

## Cluster Semantics Contract

This is release-critical.

Documents must be grouped into meaningful clusters by frontmatter and typed links. Color only labels the role of each node inside a cluster.

Required shape:

```text
auth-service cluster
  red: auth-service
  green: auth-domain, jwt-module
  blue: login-flow
  black: auth-adr-001, auth-api-spec, auth-risk-note
  orange: auth-rest-contract
```

Required link patterns:

```yaml
belongs_to: [[auth-service]]
affects: [[jwt-module]]
implements: [[login-flow]]
service: [[auth-service]]
consumes: [[auth-rest-contract]]
depends_on: [[user-domain]]
source: [[raw-auth-prd]]
```

Lint/review must detect:

- Black document with no cluster owner.
- Blue feature/flow with no implementing module.
- Green module with no service/repo/domain owner when applicable.
- Orange contract with no service owner or consumers.
- Red service/repo with no attached docs/specs/decisions.
- Color-only cluster language in docs or skills.

## Release Gates

| Gate | Required Evidence |
|---|---|
| Unit/integration tests | Full test suite green. |
| Skill pressure tests | All P0 skills have pressure fixtures. |
| Smoke: Alpha-Wiki only | Fresh project: install, init, ingest, query, lint, status, review. |
| Smoke: Codex | Install Codex skills, run init/status/lint workflow manually. |
| Smoke: AgentOps only | Future/adjacent; not part of Alpha-Wiki beta release. |
| Smoke: Combined | Future/adjacent; not part of Alpha-Wiki beta release. |
| Graph QA | Mixed-color clusters render and machine graph agrees with frontmatter links. |
| Docs | README, quickstart, compatibility matrix, CHANGELOG, migration notes complete. |
| Packaging | Plugin metadata, marketplace metadata, tags, release notes complete. |

## Suggested Execution Order

1. Cluster semantics and lint rules.
2. Deterministic ingest pipeline.
3. Query helper and citation policy.
4. Status/review trust reports.
5. Doctor and first-run checklist.
6. Graph QA exports/snapshots.
7. Codex adapter hardening and platform matrix.
8. Release docs, changelog, packaging.
9. Alpha-Wiki smoke test.
10. Optional future AgentOps/combined smoke tests outside the Alpha-Wiki beta gate.

This order keeps the knowledge graph trustworthy first. Everything else builds on that.
