---
name: lint
description: "Validate and repair wiki structure: frontmatter, broken wikilinks, missing reverse links, orphan pages, duplicate slugs, dependency rules, and graph hygiene. Use before commits, after ingest/evolve, when the graph looks wrong, or when pages become hard to find."
argument-hint: "[--fix | --suggest | --dry-run]"
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
| `dependency-rule-violation` | Warning | No |

## Graph And Color Diagnostics

If the Obsidian graph looks wrong, lint should guide the user:

- Isolated red repo/service: missing decisions/specs/contracts/module links.
- Orange contract without owner/consumers: contract page incomplete.
- Green module with no red parent: missing service/repo ownership link.
- Blue feature/flow with no green implementation link: feature is not tied to modules.
- Black document with no inbound links: likely orphan or unindexed output.
- People/tasks cluster disconnected from work pages: missing ownership links.

## Safe Fix Rules

- Add reverse links only when the reverse relation is defined.
- Do not create semantic content automatically.
- Do not delete pages.
- Do not change status values without user confirmation.
- Rebuild `edges.jsonl`, `context_brief.md`, and `open_questions.md` after fixes.

## Done Criteria

- Errors are zero.
- Warnings are either fixed or explained.
- Graph artifacts are current.
- User receives concrete next actions, not just raw output.

## References

- `tools/lint.py`
- `tools/wiki_engine.py`
- `references/cross-reference-rules.md`
- `assets/obsidian/COLOR-LEGEND.md`
