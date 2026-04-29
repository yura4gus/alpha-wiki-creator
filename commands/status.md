---
description: "Wiki health report — recent activity, stale pages, schema-evolution log, gaps, lint summary"
---

Invoke the `status` skill from the `alpha-wiki` plugin to produce a wiki health report.

Run: `uv run python -c "from tools.status import status_report; from pathlib import Path; print(status_report(Path('<wiki_dir>')))"`

Then run `uv run python tools/lint.py --wiki-dir <wiki_dir> --suggest --config .alpha-wiki/config.yaml` and append a brief lint summary (counts by severity) to the user-visible report.

Surface the full report. Offer to save it to `<wiki_dir>/outputs/status-YYYY-MM-DD.md`.
