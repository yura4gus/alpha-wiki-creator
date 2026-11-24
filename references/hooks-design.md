# Hooks design

## L1 — Agent session hooks

Claude Code routes project events through `.claude/settings.json` or
`.claude/settings.local.json` to `.claude/hooks/`. This repository checks in the
shared settings. Bootstrap uses local settings for initialized projects.
Codex is wired through `target/.codex/hooks.json` and `target/.codex/hooks/alpha_wiki_hook.py`.
Codex requires the user to review and trust project hooks with `/hooks`.

| Hook | Matcher | Script | Purpose |
|---|---|---|---|
| `session-start` | startup, resume, clear, compact | `hooks/session-start.sh` | Loads `<wiki_dir>/graph/context_brief.md` into agent context |
| `subagent-start` | Codex native subagent | `.codex/hooks/alpha_wiki_hook.py` | Adds bounded scope, snapshot, mutability, evidence, and context-brief instructions |
| `pre-tool-use` | Write\|Edit on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/pre-tool-use.sh` | Validates frontmatter + reverse-link |
| `post-tool-use` | Write, Edit, MultiEdit on source wiki Markdown | `hooks/post-tool-use.sh` | Rebuild edges, context brief, and open questions after each matching write |
| `session-end` | always | `hooks/session-end.sh` | `lint --suggest`, check document governance, refresh the brief, and emit a summary within an explicit 10-second budget |

The Codex adapter observes `Bash`, `apply_patch`, `Edit`, and `Write`, including
patch payloads that do not expose a single `file_path`. It applies the same
source/derived boundary and runs graph rebuilds synchronously after source wiki
writes. `SubagentStart` writes plain text to stdout because Codex adds that text
as developer context for the new agent.

## L2 — Git hooks

Wired by `assets/install-hooks.sh` into `.git/hooks/`.

- **pre-commit**: `tools/lint.py --fix`; fail if 🔴 remain after auto-fix; stage auto-fixes.
- **post-commit**: if `<wiki_dir>/**` touched → `wiki_engine.py rebuild-edges`.

## L3 — CI (GitHub Actions)

In `target/.github/workflows/`:

- **wiki-lint.yml** — `uv run python tools/lint.py` on push/PR; fails PR if 🔴.
- **wiki-review.yml** — weekly deterministic `python -m tools.review` → publishes issue.
- **wiki-rollup.yml** — monthly deterministic `python -m tools.rollup` → commits rollup.

## Claude graph refresh and recovery

The post-write hook resolves file paths against the payload's working directory.
It skips generated graph, render, and output paths. On macOS and Linux, matching
Claude post-write refreshes serialize through an advisory lock in
`<wiki_dir>/graph/.rebuild.lock`. Every matching write requests a refresh.
This lock is scoped to Claude post-write hooks and survives as an ignored file.
Keep the file in place while hooks may be running.

For a configured legacy post-write script, preview the checksum-based repair
from the updated Alpha-Wiki source. Run the second command to apply it.

```bash
uv run python -m scripts.bootstrap_cli --target /absolute/project --runtime-only --refresh-hooks --dry-run
uv run python -m scripts.bootstrap_cli --target /absolute/project --runtime-only --refresh-hooks
```

Review existing routing separately. Quote the full
`$CLAUDE_PROJECT_DIR/.claude/hooks/<script>.sh` command path and set
`"timeout": 10` on the Alpha-Wiki `SessionEnd` handler. If both settings files
register the same Alpha-Wiki handlers, keep one definition for each event.
Preserve other handlers and local settings. Start Claude from the target root
and use its debug log to confirm event dispatch and exit status. Doctor's
Claude settings check reports file presence. It does not run user commands.
Use `claude --init-only --debug-file <log>` to inspect startup and shutdown
without a model request. To verify native tool dispatch, run a bounded write in
an isolated project and check both the hook log and the generated graph.

Claude session hooks handle local lifecycle events. xPlan Git webhooks are a
separate integration. Context maintenance and task-state updates are explicit,
reviewed operations.
