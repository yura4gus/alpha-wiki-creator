---
description: "Health / Gap status — one cross-cutting wiki health report"
---

Invoke the `status` skill from the `alpha-wiki` plugin to produce the standard wiki health report with mandatory Gap Check. Human meaning: show what is healthy, stale, missing, or risky across the wiki.

Run: `uv run python -m tools.status --wiki-dir <wiki_dir>`

Then run `uv run python -m tools.lint --wiki-dir <wiki_dir> --suggest --config .alpha-wiki/config.yaml` and append a brief lint summary (counts by severity) to the user-visible report.

Surface the full report. Offer to save it to `<wiki_dir>/outputs/status-YYYY-MM-DD.md`.
