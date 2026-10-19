---
description: "Health / Gap status — one cross-cutting wiki health report"
argument-hint: "[--read-only] [--out <path>]"
---

Invoke the `status` skill from the `alpha-wiki` plugin to produce the standard wiki health report with mandatory Gap Check. Human meaning: show what is healthy, stale, missing, or risky across the wiki.

Arguments: $ARGUMENTS

Run: `python3 .alpha-wiki/run.py -m tools.status --wiki-dir <wiki_dir> $ARGUMENTS`

Then run `python3 .alpha-wiki/run.py -m tools.lint --wiki-dir <wiki_dir> --suggest --config .alpha-wiki/config.yaml` and append a brief lint summary (counts by severity) to the user-visible report.

Return the requested format with decisive findings. For strict read-only, use
`--read-only`, never `--out`, and follow Strict Read-Only Operations in
`references/concept.md`, including prepared runtime and no bytecode writes.
Save a report only when requested.
