---
name: wiki-lint
description: Use when the user wants to verify wiki structural integrity, fix broken links, surface orphans, or check before commit. Triggers include "lint the wiki", "check the wiki", "fix wiki links", "wiki health check". Also auto-invoked by pre-commit hook and CI. Use the `--fix` flag to apply safe corrections.
---

# wiki-lint — wiki structural validation

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
