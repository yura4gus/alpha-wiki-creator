---
name: spawn-agent
description: "Create a reusable wiki-aware agent profile or run bounded native Codex subagents now. Use for curator, reviewer, domain maintainer, importer, or documentation-gardener work that must read Alpha-Wiki context and respect its mutability rules. Do not use for AgentOps team-role bootstrap or arbitrary non-wiki agents."
argument-hint: "[create-profile | run-now | run-parallel] <name-or-scopes>"
---

# wiki:spawn-agent - create wiki-aware helper

## Mission

Create or run focused native subagents that improve wiki maintenance without
diluting ownership boundaries. The agent must understand Alpha-Wiki rules
before it touches files.

## Name Contract

`spawn-agent` means "create or run a wiki-aware helper". It is not AgentOps
`agent-skills-bootstrap`, not a team hierarchy creator, and not a replacement
for project-specific engineering agents.

## Modes

- `create-profile`: create a reusable project agent definition. Codex writes
  `.codex/agents/<name>.toml`; Claude Code writes
  `.claude/agents/<name>.md`.
- `run-now`: launch one bounded native subagent for a one-off wiki task. Do not
  create an agent file unless the user also requests a reusable profile.
- `run-parallel`: launch two to four independent native subagents and
  consolidate their terminal results. Use more only when explicitly requested
  or clearly justified by independent scopes.

When the mode is omitted, use `create-profile` for a recurring role and
`run-now` for an explicit one-off task. State the selected mode before acting.

## Boundary From ADR-006

- Alpha-Wiki owns wiki awareness and mutability discipline.
- AgentOps owns team roles, hierarchy, handoffs, CTO review, and operating model.
- This skill may create generic wiki helpers.
- It must not encode CTO, Domain, Security, QA, Release, or other AgentOps team-role logic.

## Workflow

1. Resolve:
   - Mode: `create-profile`, `run-now`, or `run-parallel`.
   - Agent name or independent scopes.
   - One-sentence role per agent.
   - Wiki scope: read-only, curator, ingest helper, lint fixer, reviewer, or
     domain maintainer.
   - Allowed Alpha-Wiki skills and exact write ownership.
   - Whether a reusable profile or companion skill is required.

2. Validate scope:
   - Reject non-wiki agents.
   - Reject AgentOps team bootstrap requests and point to AgentOps.
   - Keep permissions minimal.
   - Require disjoint writers and one writer for every shared file.
   - Treat user-supplied starting points as hypotheses, not evidence.

3. For `run-now` or `run-parallel` on Codex:
   - Use native Codex subagents directly; do not merely describe how to launch
     them.
   - The controller records any required repository/SHA snapshot once before
     fan-out. For a dirty worktree, run
     `uv run python -m tools.worktree_snapshot --root . --json-output`.
   - Give every subagent the bounded prompt contract below.
   - Wait for all terminal results, allow at most one bounded retry, consolidate
     evidence, and close completed agent threads.
   - Do not create profiles or wiki outputs unless requested.

4. For `create-profile`, detect the active platform and generate its native
   project agent:
   - Claude Code: `.claude/agents/<name>.md`.
   - Codex: `.codex/agents/<name>.toml` with required `name`, `description`, and `developer_instructions`.
   - When the project intentionally supports both, generate both files from the same prompt contract and keep their instructions equivalent.
   - On Codex, default explorers/reviewers to `sandbox_mode = "read-only"`.
   - Inherit the parent model and reasoning effort. Write `model` or
     `model_reasoning_effort` only when the user explicitly chooses them.

5. Include:
   - Role.
   - Required first read: `<wiki_dir>/graph/context_brief.md`.
   - Required files: `CLAUDE.md`, `AGENTS.md` on Codex, and relevant index pages.
   - Allowed tools.
   - Mutability matrix.
   - Required graph rebuild/lint after edits.
   - Obsidian color semantics if the agent can move/create pages.

6. Optional companion skill:
   - Generate `.claude/skills/<name>/SKILL.md`.
   - On Codex, generate `.agents/skills/<name>/SKILL.md`.
   - Keep it project-local.
   - Include triggers and explicit boundaries.

7. Log:
   - `## [YYYY-MM-DD] spawn-agent | <name> | role: <role>`
   - Log profile creation or wiki mutations, not a purely read-only one-off run.

8. Verify:
   - In `create-profile`, the agent file exists.
   - Codex TOML parses and contains all three required fields when Codex output was selected.
   - In run modes, every agent reached a terminal status and the controller
     checked snapshot consistency before synthesis.
   - No AgentOps team-role names are introduced.
   - Instructions include context read and lint/graph rebuild discipline.

## Agent Instruction Requirements

Every spawned wiki agent must know:

- `raw/` is read-only source evidence.
- `<wiki_dir>/graph/` is generated.
- `CLAUDE.md` is schema/contract.
- `AGENTS.md` is the Codex startup contract when present.
- Frontmatter is not optional.
- Cross-links need reverses.
- Contracts are orange boundary nodes.
- Service/module nodes should not stay isolated.

## Codex Native Delegation

Codex run modes use the platform's native subagent tools. They do not emulate
parallelism with files, shell processes, or repeated prompts in the main task.
The controller owns preflight, one pinned snapshot, result validation,
synthesis, and thread closure. Use two to four agents by default, prohibit
nested delegation, and follow
`references/codex-subagent-orchestration.md`.

## Done Criteria

- Agent is useful for a recurring wiki maintenance job.
- The generated format or native run matches the active platform.
- Scope is narrow enough to trust.
- No AgentOps coupling.
- Wiki graph discipline is explicit.
- Parallel results are consolidated only after all agents are terminal.

## Generated Agent Prompt Contract

Every generated profile or run-now task must use a *bounded* prompt. Include all
nine elements so the spawned agent stays trustworthy and does not drift:

1. **Mode and scope** - one bounded wiki job, active product scope, and explicit
   out-of-scope/deferred modules from `raw/docs/source-manifest.md`.
2. **Pinned snapshot** - exact repository SHA(s) from the controller when
   runtime evidence is involved, plus the canonical `tools.worktree_snapshot`
   digest for a dirty worktree. A mismatch returns `STALE_SNAPSHOT`.
3. **Constraints** - `raw/` read-only, `graph/` generated, frontmatter and
   reverse links required, plus exact read/write ownership.
4. **Relevant context** - `<wiki_dir>/graph/context_brief.md`, index/pages,
   accepted ADRs, contracts/API/enums, and relevant security pages. Carry
   recorded security constraints forward as hard limits.
5. **Forbidden actions** - no raw/graph writes, unapproved schema change,
   nested delegation, secret output, external side effects, AgentOps behavior,
   or out-of-scope work.
6. **Gates** - graph rebuild and lint after edits; no duplicate deterministic
   backends across parallel agents.
7. **Evidence and output envelope** - findings with paths, symbols, wiki pages,
   exact SHAs, evidence status, unknowns, and owner decisions.
8. **Terminal status** - `GREEN`, `FIXES_REQUIRED`, `BLOCKED`, `UNPROVEN`, or
   `STALE_SNAPSHOT`.
9. **Handoff** - state the next safe action. Append a log entry only when a
   profile or wiki state was changed.

This is a checklist for the generated prompt, not a new subsystem. Do not expand
spawn-agent beyond producing these bounded helpers.

## References

- `docs/ADR-006-spawn-agent-boundary.md`
- `references/cross-reference-rules.md`
- `references/codex-subagent-orchestration.md`
- `assets/obsidian/COLOR-LEGEND.md`
- OpenAI Codex custom agents: https://developers.openai.com/codex/subagents/
