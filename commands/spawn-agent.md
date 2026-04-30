---
description: "Create wiki helper agent — maintainer, reviewer, or domain-specific"
argument-hint: "<name> <role>"
---

Invoke the `spawn-agent` skill from the `alpha-wiki` plugin. Human meaning: create a wiki-aware helper that follows Alpha-Wiki boundaries.

Arguments: $ARGUMENTS

Ask the user for the agent name, role description (1-2 sentences), which wiki skills it should use, and whether to generate a companion skill. Render `.claude/agents/<name>.md` with frontmatter, allowed tools, and required reading of `<wiki_dir>/graph/context_brief.md` at start. Append a `spawn-agent` entry to `<wiki_dir>/log.md`. Commit and print activation instructions.
