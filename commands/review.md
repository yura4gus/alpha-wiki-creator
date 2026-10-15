---
description: "Audit wiki structure — status snapshot, lint findings, next actions"
argument-hint: "[--out <path>]"
---

Invoke the `review` skill from the `alpha-wiki` plugin. Human meaning: run the scheduled trust check before sharing or merging wiki changes.

Arguments: $ARGUMENTS

Run:

```bash
uv run python -m tools.review --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml $ARGUMENTS
```

Summarize the generated report in the requested format with decisive evidence.
Name its verdict as wiki quality; missing wiki metadata does not establish a
runtime vulnerability or block package publication without an existing rule.
Save only when requested. Use Release Decisions in `references/concept.md`.
