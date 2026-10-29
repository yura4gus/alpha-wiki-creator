# OpenCode v2 adapter

Alpha-Wiki uses OpenCode's native skills and Markdown commands, not a JavaScript
plugin or a second server. Commands `/alpha-wiki/<operation>` load the matching
`alpha-wiki-<operation>` skill. Direct skill mentions use `@alpha-wiki-init`, etc.
The same source skills supply Claude, Codex and OpenCode workflows.
Shared CLI reports can still show Claude-style `/alpha-wiki:<operation>` hints;
in OpenCode invoke the corresponding `/alpha-wiki/<operation>` command.

## Runtime and instructions

Read the target project's `AGENTS.md`, configured wiki brief and index. OpenCode
v2 discovers AGENTS.md; it does not use CLAUDE.md as a fallback. Preserve existing
instructions and deliberately merge unique legacy guidance only when authorized.
Read source documents when wiki freshness or authority is uncertain.

Before init, use the installed runtime path from the skill adapter note:

```bash
UV_PROJECT_ENVIRONMENT="<runtime_root>/.venv" uv run --project "<runtime_root>" --directory "<runtime_root>" --no-dev python -m scripts.bootstrap_cli --target "<absolute-project>" --hooks none --dry-run
```

After reviewing the preview, repeat without `--dry-run` for an authorized init.
Use `--hooks none` for an OpenCode-only project: Claude/Codex session adapters
are not OpenCode hooks. Do not add CI or other-platform hooks unless requested.
Keep the existing shared AGENTS.md and user configuration; no opencode.json edit
or separate OpenCode project contract is required.

For an existing wiki, use the same runtime command with `--runtime-only` and
`--dry-run`, review it, then apply. This preserves schema, wiki pages, contracts,
product dependencies and existing hook routing. Updating global skills alone
does not upgrade target-project tools.

Before using `--platform opencode` on an older project, inspect its doctor help;
preview a runtime-only upgrade if that choice is absent. Review existing Git
changes under `tools/` and `.alpha-wiki/` before applying. Do not overwrite
modified tools or bootstrap the Alpha-Wiki source checkout over its own
unfinished implementation; preserve and merge those changes deliberately.

After init/upgrade run from the target project:

```bash
python3 .alpha-wiki/run.py -m tools.doctor --project-dir . --platform opencode --refresh
python3 .alpha-wiki/run.py -m tools.status --wiki-dir wiki
python3 .alpha-wiki/run.py -m tools.lint --wiki-dir wiki --config .alpha-wiki/config.yaml --dry-run
```

Resolve a custom wiki directory from the project config/contract, not this example.
Dependencies live under the plugin runtime or `.alpha-wiki/runtime/.venv`, never
the product environment. Shared rules are in `<runtime_root>/references/concept.md`.

## Helpers and optional AgentOps

OpenCode reusable profiles are `.opencode/agents/<name>.md`, with `description`
and `mode: subagent` frontmatter. Use OpenCode's native child-agent mechanism
for an explicitly scoped helper. Do not generate Codex TOML or Claude profiles
as an OpenCode substitute. Inherit the selected model; never change providers,
permissions or model choices merely to install Alpha-Wiki.

Apply the shared bounded prompt, one pinned snapshot, disjoint writers, terminal
evidence and controller-owned deterministic checks. No automatic parallel audit
from a bare skill mention. Optional AgentOps remains out of first run.

## Limits

No OpenCode event-hook automation or scheduler is installed. After authorized
wiki edits the controller explicitly refreshes graph/brief/questions and runs
lint. A discovered skill or passing deterministic test is not proof of live
model reasoning, child-agent execution, runtime acceptance or product release.
OpenCode v1 compatibility is not claimed. Project or explicit config definitions
can override global skill IDs and commands; user permissions still apply.

## Primary references

- https://opencode.ai/v2/docs/skills/
- https://opencode.ai/v2/docs/commands/
- https://opencode.ai/v2/docs/instructions/
- https://opencode.ai/v2/docs/agents/
