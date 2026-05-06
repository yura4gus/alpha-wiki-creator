---
description: "Summarize wiki activity — weekly or monthly rollup"
argument-hint: "[week | month] [--write]"
---

Invoke the `rollup` skill from the `alpha-wiki` plugin. Human meaning: summarize what changed in the wiki over a week or month.

Arguments: $ARGUMENTS

Default period is `month`. If `$ARGUMENTS` starts with `week` or `month`, use that as `<period>` and pass the remaining flags through. Run:

```bash
uv run python -m tools.rollup --wiki-dir <wiki_dir> --period <period> <remaining-flags>
```

For scheduled CI or persistent summaries, include `--write` so the report is written under `<wiki_dir>/rollups/`.
