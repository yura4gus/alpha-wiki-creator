# Hooks design

## L1 — Agent session hooks

Claude Code is wired through `target/.claude/settings.local.json` and `target/.claude/hooks/`.
Codex is wired through `target/.codex/hooks.json` and `target/.codex/hooks/alpha_wiki_hook.py`.
Codex requires the user to review and trust project hooks with `/hooks`.

| Hook | Matcher | Script | Purpose |
|---|---|---|---|
| `session-start` | always | `hooks/session-start.sh` | Loads `<wiki_dir>/graph/context_brief.md` into agent context |
| `subagent-start` | Codex native subagent | `.codex/hooks/alpha_wiki_hook.py` | Adds bounded scope, snapshot, mutability, evidence, and context-brief instructions |
| `pre-tool-use` | Write\|Edit on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/pre-tool-use.sh` | Validates frontmatter + reverse-link |
| `post-tool-use` | Write on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/post-tool-use.sh` | Debounced (5s) `wiki_engine.py rebuild-context-brief` |
| `session-end` | always | `hooks/session-end.sh` | `lint --suggest`, append log entry, echo summary |

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

## Debouncing

`post-tool-use` rebuild is debounced 5s using a lockfile `<wiki_dir>/graph/.rebuild.lock` with timestamp.
If a rebuild is requested within 5s of the previous, the second call exits silently.
