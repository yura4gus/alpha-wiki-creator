---
description: "Run a wiki-level structural review - status snapshot, lint findings, next actions"
argument-hint: "[--out <path>]"
---

Invoke the `review` skill from the `alpha-wiki` plugin.

Arguments: $ARGUMENTS

Run:

```bash
uv run python tools/review.py --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml $ARGUMENTS
```

Surface the generated markdown report. This is Alpha-Wiki structural review, not AgentOps `cto-review`.
