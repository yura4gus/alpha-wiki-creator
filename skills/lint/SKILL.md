---
name: lint
description: "Validate and repair wiki structure: frontmatter, broken wikilinks, missing reverse links, orphan pages, duplicate slugs, dependency rules, and graph hygiene. Use before commits, after ingest/evolve, when the graph looks wrong, or when pages become hard to find."
---

# wiki:lint - structural validation

## Mission

Keep the wiki trustworthy as a graph. Lint is the guardrail that prevents markdown memory from decaying into loose notes.

## Name Contract

`lint` means "check structural integrity". It does not do semantic review, product judgment, or team process review. Use `/alpha-wiki:review` for a higher-level report.

## Severity Model

- Error: blocks CI/commit. Examples: broken wikilink, missing required frontmatter, duplicate slug.
- Warning: should be fixed or reviewed. Examples: missing reverse link, orphan page, dependency rule violation.
- Suggestion: useful cleanup that should not block. Examples: stale page, missing owner, weak title, poor graph placement.

## Modes

- `--dry-run`: report only; nonzero on errors.
- `--suggest`: report plus suggested manual fixes.
- `--fix`: apply deterministic safe fixes, then re-run checks.
- CI/pre-commit mode: fail on errors; allow warnings unless strict mode is explicitly requested.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

1. Detect wiki dir and config:
   - `--wiki-dir <wiki_dir>`
   - `--config .alpha-wiki/config.yaml`
2. Run all deterministic checks.
3. Group findings by severity and check name.
4. If `--fix`:
   - Apply only safe deterministic fixes.
   - Rebuild graph files.
   - Re-run lint.
5. Summarize:
   - Counts by severity.
   - Files changed by auto-fix.
   - Manual next actions.

## Checks

| Check | Severity | Auto-fix |
|---|---|---|
| `broken-wikilink` | Error | No |
| `missing-frontmatter-field` | Error | No |
| `duplicate-slug` | Error | No |
| `missing-reverse-link` | Warning | Yes |
| `orphan` | Warning | No |
| `cluster-link-gap` | Warning | No |
| `dependency-rule-violation` | Warning | No |

## Graph And Color Diagnostics

Treat `_index.md` as folder navigation: require title and unique slug, not the
folder's entity fields or a mandatory owner. Keep link, duplicate, orphan,
dependency and typed-reverse checks active. See `references/cross-reference-rules.md`.

If the Obsidian graph looks wrong, lint should guide the user:

- Isolated red repo/service: missing decisions/specs/contracts/module links.
- Orange contract without owner/consumers: contract page incomplete.
- Green module with no red parent: missing service/repo ownership link.
- Blue feature/flow with no green implementation link: feature is not tied to modules.
- Black document with no inbound links: likely orphan or unindexed output.
- People/tasks cluster disconnected from work pages: missing ownership links.

Cluster ownership is checked through typed frontmatter links such as `belongs_to`, `owned_by`, `affects`, `implements`, `service`, `target_module`, `defined_in`, and `consumers`. Colors help humans read node roles; cluster links help agents and tools understand where a page belongs.

## Safe Fix Rules

- Add reverse links only when the reverse relation is defined.
- Do not create semantic content automatically.
- Do not delete pages.
- Do not infer accepted/completed status from formatting. Apply a requested,
  evidence-backed status repair within its authorized scope; ask only for a
  missing semantic decision.
- Rebuild `edges.jsonl`, `context_brief.md`, and `open_questions.md` after fixes.

## Codex Native Delegation

Do not fan out lint. One deterministic lint run must evaluate one integrated
wiki state. When fixes are requested, the controller may delegate disjoint page
groups only after assigning exact write ownership; shared indexes, config, log,
and graph source relations have one writer. The controller then rebuilds the
graph and reruns lint once on the integrated result.

## Done Criteria

- Errors are zero.
- Warnings are either fixed or explained.
- Graph artifacts are current.
- User receives concrete next actions, not just raw output.

## References

- `tools/lint.py`
- `tools/wiki_engine.py`
- `references/cross-reference-rules.md`
- `references/codex-subagent-orchestration.md`
- `assets/obsidian/COLOR-LEGEND.md`
