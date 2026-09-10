# Codex Adapter

Alpha-Wiki supports current OpenAI Codex through a namespaced plugin, optional standalone fallback skills, project `AGENTS.md`, and trusted project hooks. The same markdown wiki and deterministic Python tools remain shared with Claude Code.

## Install Or Upgrade

```bash
npm install -g @openai/codex@latest
git clone https://github.com/yura4gus/alpha-wiki-creator
cd alpha-wiki-creator
python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone
```

On an existing clone:

```bash
git pull --ff-only
npm install -g @openai/codex@latest
python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone
```

The installer:

- builds the personal `alpha-wiki` plugin under `~/plugins/alpha-wiki`;
- adds it to the existing personal marketplace without replacing other entries;
- activates or reinstalls the plugin through `codex plugin`;
- exposes one namespaced set of 16 plugin skills (12 core plus 4 optional AgentOps) and excludes Claude `commands/` from the Codex package;
- removes only generated Alpha-Wiki standalone adapters from `~/.agents/skills` when `--remove-standalone` is supplied;
- removes only managed `alpha-wiki-*` adapters from legacy `~/.codex/skills` when `--remove-legacy` is supplied.

Use `--dry-run` to inspect paths or `--no-activate` in CI/tests. Standalone fallback installation is explicit: `--standalone`; it skips plugin installation so the two skill surfaces cannot coexist. Start a new Codex task after installation so plugin and skill discovery refreshes.

## Invocation

Preferred plugin invocations:

| Operation | Codex plugin |
|---|---|
| init | `$alpha-wiki:init` |
| doctor | `$alpha-wiki:doctor` |
| ingest | `$alpha-wiki:ingest` |
| query | `$alpha-wiki:query` |
| lint | `$alpha-wiki:lint` |
| status | `$alpha-wiki:status` |
| evolve | `$alpha-wiki:evolve` |
| spawn-agent | `$alpha-wiki:spawn-agent` |
| render | `$alpha-wiki:render` |
| review | `$alpha-wiki:review` |
| rollup | `$alpha-wiki:rollup` |
| audit-project | `$alpha-wiki:audit-project` |
| orchestrate (optional) | `$alpha-wiki:orchestrate` |
| backlog (optional) | `$alpha-wiki:backlog` |
| handoff (optional) | `$alpha-wiki:handoff` |
| release-check (optional) | `$alpha-wiki:release-check` |

Standalone compatibility names use hyphens, for example `$alpha-wiki-init` and `$alpha-wiki-status`. Do not install them alongside the plugin because Codex will display duplicate workflows.

## Native Subagents

Alpha-Wiki uses Codex native subagents; it does not ship another agent runtime.
`AGENTS.md` and the skills define when fan-out is useful. The generated
`SubagentStart` hook injects a compact Alpha-Wiki contract and context brief into
every native subagent.

Use `$alpha-wiki:spawn-agent` in three modes:

- `create-profile` writes a reusable `.codex/agents/<name>.toml`;
- `run-now` launches one bounded wiki-aware subagent without creating a file;
- `run-parallel` launches independent scopes and consolidates terminal results.

Normal `doctor`, `lint`, `status`, `render`, and `rollup` remain deterministic
single-controller operations. `audit-project`, `review`, `ingest`, `query`,
`evolve`, and large/multi-repo `init` may use bounded native delegation.

The controller owns one pinned repository/SHA snapshot, permissions, synthesis,
and final gates. For dirty worktrees it records the canonical snapshot with
`uv run python -m tools.worktree_snapshot --root . --json-output`. Subagents do
not independently fetch shared refs, create nested agents, or overlap writes.
See:

- `references/codex-subagent-orchestration.md`;
- `docs/examples/codex-parallel-audit-prompt.md`.

For substantial multi-track work, `$alpha-wiki:orchestrate` wraps the same
native subagent model with opt-in Markdown state under `wiki/agentops/`. It does
not install a second agent runtime. See `references/agentops-control-layer.md`.

## Project Integration

`$alpha-wiki:init` generates:

- `AGENTS.md` with the Codex operating contract and startup reading order;
- `.codex/hooks.json`;
- `.codex/hooks/alpha_wiki_hook.py`;
- the same `CLAUDE.md`, wiki, tools, graph, Obsidian config, git hooks, and CI assets used by Claude Code.

Before a target project has local tools, the init skill can run the installed plugin backend directly:

```bash
uv run --project ~/plugins/alpha-wiki python -m scripts.bootstrap_cli \
  --target /path/to/project \
  --project-name "my-project" \
  --description "one-line purpose" \
  --hooks all \
  --ci
```

Codex hooks load `wiki/graph/context_brief.md`, inject the bounded contract at
`SubagentStart`, warn on direct graph edits, rebuild graph artifacts after source
wiki writes, and run a bounded session-end lint. Project hooks do not run until
the project is trusted and the definitions are reviewed with `/hooks`.

## Verify

```bash
codex plugin list --json
uv run python -m tools.doctor --project-dir . --platform codex --refresh
```

Expected: the plugin package and marketplace entry are present, exactly one set of 16 plugin skills is exposed, no standalone duplicates are detected, `AGENTS.md` is recognized, and project hooks exist when session hooks were enabled.

## Boundaries

- Plugin support is the preferred Codex CLI/desktop path. Standalone skills are an explicit alternative for surfaces that do not load plugins.
- `spawn-agent` can generate project `.codex/agents/*.toml`, but it is optional and is not part of the first-run path.
- Hooks are guardrails, not an enforcement boundary. Deterministic lint/status/review tools remain authoritative.
- Gemini packaging is not implemented.

## Official Codex References

- https://developers.openai.com/codex/
- https://developers.openai.com/codex/skills/
- https://developers.openai.com/codex/hooks/
- https://developers.openai.com/codex/agents-md/
