---
name: spawn-agent
description: "Create a wiki-aware Claude Code subagent that reads context, respects the mutability matrix, and operates on Alpha-Wiki content. Use for recurring wiki roles such as curator, reviewer, domain maintainer, importer, or documentation gardener. Do not use for AgentOps team-role bootstrap or arbitrary non-wiki agents."
argument-hint: "<name> <role>"
---

# wiki:spawn-agent - create wiki-aware helper

## Mission

Generate a focused subagent that improves wiki maintenance without diluting ownership boundaries. The agent must understand Alpha-Wiki rules before it touches files.

## Name Contract

`spawn-agent` means "create a wiki-aware helper". It is not AgentOps `agent-skills-bootstrap`, not a team hierarchy creator, and not a replacement for project-specific engineering agents.

## Boundary From ADR-006

- Alpha-Wiki owns wiki awareness and mutability discipline.
- AgentOps owns team roles, hierarchy, handoffs, CTO review, and operating model.
- This skill may create generic wiki helpers.
- It must not encode CTO, Domain, Security, QA, Release, or other AgentOps team-role logic.

## Workflow

1. Ask for:
   - Agent name.
   - One-sentence role.
   - Wiki scope: read-only, curator, ingest helper, lint fixer, reviewer, domain maintainer.
   - Allowed Alpha-Wiki skills.
   - Whether to generate companion skill.

2. Validate scope:
   - Reject non-wiki agents.
   - Reject AgentOps team bootstrap requests and point to AgentOps.
   - Keep permissions minimal.

3. Generate `.claude/agents/<name>.md`:
   - Role.
   - Required first read: `<wiki_dir>/graph/context_brief.md`.
   - Required files: `CLAUDE.md`, relevant index pages.
   - Allowed tools.
   - Mutability matrix.
   - Required graph rebuild/lint after edits.
   - Obsidian color semantics if the agent can move/create pages.

4. Optional companion skill:
   - Generate `.claude/skills/<name>/SKILL.md`.
   - Keep it project-local.
   - Include triggers and explicit boundaries.

5. Log:
   - `## [YYYY-MM-DD] spawn-agent | <name> | role: <role>`

6. Verify:
   - Agent file exists.
   - No AgentOps team-role names are introduced.
   - Instructions include context read and lint/graph rebuild discipline.

## Agent Instruction Requirements

Every spawned wiki agent must know:

- `raw/` is read-only source evidence.
- `<wiki_dir>/graph/` is generated.
- `CLAUDE.md` is schema/contract.
- Frontmatter is not optional.
- Cross-links need reverses.
- Contracts are orange boundary nodes.
- Service/module nodes should not stay isolated.

## Done Criteria

- Agent is useful for a recurring wiki maintenance job.
- Scope is narrow enough to trust.
- No AgentOps coupling.
- Wiki graph discipline is explicit.

## References

- `docs/ADR-006-spawn-agent-boundary.md`
- `references/cross-reference-rules.md`
- `assets/obsidian/COLOR-LEGEND.md`
