---
description: "Audit wiki structure — status snapshot, lint findings, next actions"
argument-hint: "[--read-only] [--out <path>]"
---

Invoke the `review` skill from the `alpha-wiki` plugin. Human meaning: run the scheduled trust check before sharing or merging wiki changes.

Arguments: $ARGUMENTS

Run:

```bash
python3 .alpha-wiki/run.py -m tools.review --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml $ARGUMENTS
```

Summarize the generated report in the requested format with decisive evidence.
Name its verdict as wiki quality; missing wiki metadata does not establish a
runtime vulnerability or block package publication without an existing rule.
Save only when requested. Use Release Decisions in `references/concept.md`.
For strict no-write audits, pass `--read-only` without `--out` and follow Strict
Read-Only Operations in that reference, including the runtime constraints.
