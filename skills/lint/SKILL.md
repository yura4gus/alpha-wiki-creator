---
name: lint
description: Verify wiki structural integrity — broken links, missing reverses, orphans, dependency rules, frontmatter. Triggers include "lint the wiki", "check the wiki", "fix wiki links", "wiki health check". Auto-invoked by pre-commit hook and CI. Use `--fix` for safe auto-corrections.
argument-hint: "[--fix | --suggest | --dry-run]"
---

# wiki:lint — wiki structural validation

## Process

1. Determine flags: `--fix` (apply safe fixes), `--suggest` (print suggestions), `--dry-run` (report-only, exit nonzero on errors).
2. Run: `uv run python tools/lint.py --wiki-dir <wiki_dir> [--fix|--suggest|--dry-run] --config <merged-config-path>`.
3. Surface findings to user, grouped by severity:
   - 🔴 errors (blocking): broken links, missing required frontmatter, duplicate slugs
   - 🟡 warnings: missing reverse links (auto-fixable), orphans, dependency rule violations, contract migration notes missing
4. If `--fix` was used, summarize what was auto-corrected.
5. Suggest manual follow-ups for non-auto-fixable items.

## Lint check inventory

See `references/cross-reference-rules.md` and `tools/lint.py` source for exact check definitions.

| Check | Severity | Auto-fix |
|---|---|---|
| broken-wikilink | 🔴 | no |
| missing-reverse-link | 🟡 | yes |
| orphan | 🟡 | no |
| missing-frontmatter-field | 🔴 | no |
| duplicate-slug | 🔴 | no |
| dependency-rule-violation | 🟡 | no |
