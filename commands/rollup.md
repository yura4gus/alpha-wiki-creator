---
description: "Summarize wiki or optional AgentOps activity for a week or month"
argument-hint: "[week | month] [--scope wiki|agentops|all] [--write]"
---

Invoke the `rollup` skill from the `alpha-wiki` plugin. Human meaning: summarize what changed in the wiki over a week or month.

Arguments: $ARGUMENTS

Default period is `month`. If `$ARGUMENTS` starts with `week` or `month`, use that as `<period>` and pass the remaining flags through. Run:

```bash
uv run python -m tools.rollup --wiki-dir <wiki_dir> --period <period> <remaining-flags>
```

Use `--scope agentops` to summarize sessions, handoffs, and backlog updates;
that output is written under `<wiki_dir>/agentops/rollups/`. The default
`--scope wiki` and ordinary first-run behavior are unchanged.
