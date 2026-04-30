---
description: "Generate a weekly or monthly wiki activity rollup"
argument-hint: "[week | month] [--write]"
---

Invoke the `rollup` skill from the `alpha-wiki` plugin.

Arguments: $ARGUMENTS

Default period is `month`. If `$ARGUMENTS` starts with `week` or `month`, use that as `<period>` and pass the remaining flags through. Run:

```bash
uv run python tools/rollup.py --wiki-dir <wiki_dir> --period <period> <remaining-flags>
```

For scheduled CI or persistent summaries, include `--write` so the report is written under `<wiki_dir>/rollups/`.
