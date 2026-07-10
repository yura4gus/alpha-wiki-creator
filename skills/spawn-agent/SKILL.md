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

## Generated Agent Prompt Contract

Every agent file this skill writes must be a *bounded* prompt. Include all seven
elements so the spawned agent stays trustworthy and does not drift:

1. **Scope** — the one recurring wiki job it owns, plus the **active product scope** and the **out-of-scope / deferred modules** from `raw/docs/source-manifest.md`. State both so the agent cannot drift onto deferred work (e.g. if active scope is Web Wallet, it must not start on Launchpad/dApp/DeFi).
2. **Constraints** — the mutability matrix: `raw/` read-only, `graph/` generated, `CLAUDE.md` is the contract, frontmatter + reverse links required.
3. **Relevant context** — required first read `<wiki_dir>/graph/context_brief.md`, plus the specific index/pages, relevant ADRs, contracts/API/enums, and any `security/` pages for its domain.
4. **Forbidden actions** — no `raw/` writes, no hand-edits to `graph/`, no schema changes without `/alpha-wiki:evolve`, no AgentOps team-role behavior, and **no work on out-of-scope/deferred modules**. Carry forward any recorded **security constraints** (auth/session/secrets/custody freezes) as hard limits.
5. **Gates to run** — graph rebuild + `/alpha-wiki:lint` after edits; stop if lint reports errors.
6. **Output format** — what the agent returns (edited pages, a lint summary, a proposed batch) so its result is reviewable.
7. **Handoff requirement** — append a `## [YYYY-MM-DD] spawn-agent | <name> | ...` log entry and state the next safe action for the human or next agent.

This is a checklist for the generated prompt, not a new subsystem. Do not expand
spawn-agent beyond producing these bounded helpers.

## References

- `docs/ADR-006-spawn-agent-boundary.md`
- `references/cross-reference-rules.md`
- `assets/obsidian/COLOR-LEGEND.md`
