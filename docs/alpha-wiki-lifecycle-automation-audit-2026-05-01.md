# Alpha-Wiki Lifecycle Automation Audit — 2026-05-01

Goal: verify how closed, universalized, and automated the Alpha-Wiki lifecycle is today, and identify the exact gaps that must be automated before final release.

## Lifecycle Under Audit

```text
install
  -> init/bootstrap
  -> ingest/update pages
  -> rebuild graph artifacts
  -> lint structural rules
  -> status gap report
  -> review trust report
  -> rollup activity summary
  -> CI/hooks keep it current
```

## Automation Verdict

Current state: **partially closed and increasingly automated**.

Alpha-Wiki now has the right deterministic spine: bootstrap, doctor, ingest, query, graph rebuild, lint, status, review, render, rollup, hooks, CI templates, and release audit. The remaining release risk is packaging and fresh-install evidence: quickstart, changelog, version/tag prep, and semantic trust tooling for claims/contracts/contradictions.

## Rule-To-Automation Matrix

| Rule / Invariant | Current Automation | Current Tests | Status | Gap |
|---|---|---|---|---|
| Raw sources are read-only | `CLAUDE.md` mutability matrix, ingest skill discipline | Bootstrap/template tests | partial | No pre-write enforcement for `raw/**` yet. |
| Wiki pages are markdown/frontmatter | Templates, parser, lint frontmatter checks | Parsing/frontmatter tests | pass | Expand invalid YAML/frontmatter shape checks. |
| Graph artifacts are generated, not hand-edited | `wiki_engine.py`, hooks, status/review refresh | Graph/status/hook tests | pass | Add CI check that graph artifacts are current after PR changes. |
| Cluster ownership links are required | `cluster-link-gap` lint, status `Cluster gap`, frontmatter templates | `test_lint_cluster_links`, lifecycle smoke | in-progress | Need stronger per-entity policy and review scoring. |
| Color labels role, not cluster | Obsidian legend, Mermaid/DOT exports, render skill, tests | Obsidian graph tests, Graph export tests | pass | Add visual-image snapshots later if needed. |
| Static read-only export exists | `tools/render_html.py`, render skill | HTML export tests | pass | Keep visual polish minimal until dogfooding. |
| `doctor` verifies install/runtime lifecycle | `tools/doctor.py`, `/alpha-wiki:doctor`, `skills/doctor` | Doctor unit tests | pass | Add release smoke usage once packaging is final. |
| `ingest` updates pages/log/graph/lint | `tools/ingest_pipeline.py`, skill instructions | Ingest pipeline pressure tests | partial | Add conflicting-source/claim extraction after claims tooling. |
| `query` reads brief/index/pages with citations | `tools/wiki_search.py`, skill instructions | Query helper tests | pass | Add contradiction-aware query pressure tests after claims tooling. |
| `lint` blocks structural decay | `tools/lint.py`, pre-commit, CI template | Unit/integration tests | pass | Split checks into modules and add full release check set. |
| `status` exposes gaps | `tools/status.py` | Status tests | pass | Health scoring can be refined after ingest/query are deterministic. |
| `review` produces trust report | `tools/review.py` | Review/rollup tests | pass | Add deeper semantic contradiction checks after query/claims tooling. |
| `rollup` summarizes activity | `tools/rollup.py`, CI template | Rollup tests | pass | Add unresolved gap and decision summary. |
| Claude hooks keep graph fresh | `assets/hooks/*` | Hook mode/runtime asset tests | pass | Hooks are Claude-specific; Codex needs explicit/manual workflow or adapter. |
| CI checks wiki health | `assets/workflows/*` | Runtime asset tests | partial | CI lint template runs; review/rollup depend on headless Claude and secrets. |
| Codex path exists | `scripts/install_codex.py`, docs | Codex installer tests | partial | No Codex-native hooks/automation yet. |

## Lifecycle Closure Analysis

### 1. Install

Automated:

- Claude Code plugin install is documented.
- Codex skill adapter install exists through `scripts/install_codex.py`.
- Bootstrap writes tools, hooks, workflows, Obsidian config, wiki skeleton.
- `doctor` verifies Python, uv, tools import, wiki dir, config, graph artifacts, lint, Claude hooks, CI workflows, and Codex skill installation hints.

Gaps:

- Platform matrix exists; Codex hook parity is still documented as explicit/manual operation.
- Gemini is deferred and must not be claimed in release language.

Next automation:

- Wire `doctor --platform both --refresh --strict` into final release smoke instructions.

### 2. Init / Bootstrap

Automated:

- `scripts/bootstrap.py` renders project files.
- Safe-existing protection exists for top-level files.
- Custom wiki dir is propagated into hooks/workflows.
- Obsidian config and graph seeds are generated.

Gaps:

- First-run checklist is still documentation-level.
- Existing-repo migration audit is planned, not implemented as `tools/init_audit.py`.

Next automation:

- Bootstrap should optionally run `doctor`, `lint`, `status`, and graph rebuild after init and print a first-run checklist.

### 3. Ingest / Update

Automated:

- Skill-level workflow is strong.
- Classifier exists for artifact classification.
- Graph rebuild and lint can be run after writes.

Gaps:

- Deterministic `tools/ingest_pipeline.py` exists for local source files.
- Provenance, optional cluster-link attachment, log append, graph rebuild, lint summary, and resume state are backend-backed.
- Claim extraction / contradiction detection is still deferred.

Next automation:

- Add claim extraction and contradiction detection after claims tooling.

### 4. Graph / Cluster

Automated:

- `wiki_engine.py` rebuilds `edges.jsonl`, `context_brief.md`, `open_questions.md`.
- `cluster-link-gap` detects unclustered documents/features/contracts/modules.
- Status surfaces cluster gaps.
- Obsidian colors are documented and tested.

Gaps:

- Mermaid/DOT exports exist and group mixed-role nodes by typed service links.
- Export tests prove mixed red/green/blue/black/orange service clusters are not color-only clusters.
- Red service/repo with no attached docs is not yet detected.

Next automation:

- Extend lint/review to detect service/repo nodes with no attached evidence pages.
- Add optional rendered image snapshots if Graphviz/Mermaid renderers are available in CI.

### 5. Lint

Automated:

- Deterministic lint exists.
- Pre-commit hook runs `lint --fix`.
- CI lint workflow exists.
- Cluster-link lint has tests.

Gaps:

- Checks are still in one file.
- Full release set not complete: duplicate aliases, stale metadata, missing provenance, invalid frontmatter shape, current graph check.

Next automation:

- Split into `tools/lint_checks/*` and add per-check tests.

### 6. Status

Automated:

- Status rebuilds graph artifacts before reporting.
- Status includes Gap Check and cluster gap.

Gaps:

- Provenance score, cluster health, freshness, and open-question owner/timebox follow-up exist.
- No unified health score yet.

Next automation:

- Refine unified health score after core checks are stable.

### 7. Review

Automated:

- `tools/review.py` combines status + lint findings.
- CI review workflow exists.

Gaps:

- Review now summarizes cluster gaps, isolated services, provenance, and freshness.
- It is still not a semantic contradiction audit.

Next automation:

- Extend later with contradiction, claim confidence, and decision freshness details.

### 8. Rollup

Automated:

- `tools/rollup.py` and CI rollup workflow exist.
- Rollup write is idempotent.

Gaps:

- Rollup does not yet separate activity, decisions, unresolved gaps, and schema changes.

Next automation:

- Add sections and link back to source pages.

### 9. Hooks / CI / Platform Automation

Automated:

- Claude hooks cover session start, pre-tool-use, post-tool-use, session end, pre-commit.
- CI templates cover lint, review, rollup.

Gaps:

- Codex has skill adapter but no native hook automation.
- Review/rollup CI depends on Claude secrets.
- `doctor` checks hook/workflow presence and Codex skill installation hints.

Next automation:

- Document Codex manual equivalent flow and add `doctor` warnings.
- Make workflow templates fail clearly when secrets are missing.

## Universalization Scorecard

| Area | Score | Reason |
|---|---:|---|
| Domain presets | 7/10 | Multiple presets exist; cluster fields strongest in software preset first. |
| Platform support | 5/10 | Claude good; Codex adapter exists; Gemini deferred. |
| Automation closure | 8/10 | Graph/lint/status/review/render automated; deterministic ingest/query backends exist; release is blocked mainly by packaging and fresh-install smoke. |
| Graph/cluster discipline | 8/10 | Cluster lint and Mermaid/DOT Graph QA exports exist; service evidence scoring still missing. |
| Operator UX | 7/10 | README/commands improved; doctor exists; first-run checklist still missing. |
| AI context grasp | 7/10 | context brief/index/graph exist; budget profiles/search helper missing. |

## Key Findings

1. The lifecycle is **structurally closed** for graph/status/lint/review once pages exist.
2. The lifecycle is **mostly closed** for ingest/query at the deterministic backend level; claim extraction and contradiction handling remain.
3. Cluster semantics are now partially automated through lint/status and Graph QA exports, but release needs richer review.
4. Claude automation is significantly stronger than Codex automation.
5. Final release should prioritize quickstart/changelog, fresh install smoke evidence, packaging/version prep, and then deeper semantic trust checks.

## Evidence Commands

Run during this audit:

```bash
rg --files assets commands docs references scripts skills tests tools .github .claude-plugin | sort
for f in assets/hooks/*.sh assets/workflows/*.yml; do sed -n '1,220p' "$f"; done
.venv/bin/python -m pytest
```

Additional lifecycle evidence:

- `tests/integration/test_alpha_wiki_lifecycle_closure.py`
- `tests/unit/test_lint_cluster_links.py`
- `tests/unit/test_graph_exports.py`
- `tests/unit/test_ingest_pipeline.py`
- `tests/unit/test_wiki_search.py`
- `tests/unit/test_status.py`
- `tests/unit/test_wiki_engine_edges.py`
- `tests/unit/test_release_audit.py`

Latest result: `111 passed`.
