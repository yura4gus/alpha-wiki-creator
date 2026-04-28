---
name: spawn-agent
description: Add a Claude Code subagent that operates on the wiki — e.g. maintainer, reviewer, or domain-specific agent. Triggers include "add an agent for X", "spawn a wiki agent", "create a subagent that does X with the wiki". Generates `.claude/agents/<name>.md` and optionally a companion skill. Out of scope: writing arbitrary agents unrelated to the wiki.
argument-hint: "<name> <role>"
---

# wiki:spawn-agent — add a wiki-aware subagent

## Process

1. Ask the user for:
   - Agent name (e.g. `wiki-reviewer`, `domain-curator`)
   - Role description (1-2 sentences)
   - Which wiki skills the agent should use (subset of `/alpha-wiki:ingest`, `/alpha-wiki:query`, `/alpha-wiki:lint`, `/alpha-wiki:evolve`)
   - Whether to also generate a companion skill (yes/no)

2. Render `.claude/agents/<name>.md` with frontmatter and a body that:
   - States the role
   - Lists allowed tools (typically `Read`, `Edit`, `Bash`)
   - Lists which wiki skills to invoke
   - Notes that it MUST read `<wiki_dir>/graph/context_brief.md` at start

3. (Optional) If companion skill requested, render `.claude/skills/<name>/SKILL.md` with a description and process steps tailored to the role.

4. Append `<wiki_dir>/log.md`: `## [date] spawn-agent | <name> | role: <role>`.

5. Commit and print activation instructions to the user.

## Constraints

- The agent operates within the wiki — it does not bypass `pre-tool-use` validation.
- The agent MUST honor the mutability matrix in CLAUDE.md.
