---
description: "Verify wiki structural integrity — broken links, missing reverses, orphans, dependency rules"
argument-hint: "[--fix | --suggest | --dry-run]"
---

Invoke the `lint` skill from the `alpha-wiki` plugin.

Flags from the user (if any): $ARGUMENTS

Run: `uv run python tools/lint.py --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml $ARGUMENTS`

Surface findings grouped by severity (🔴 errors block; 🟡 warnings inform). If `--fix` was used, summarize what was auto-corrected. Suggest manual follow-ups for non-auto-fixable items.
