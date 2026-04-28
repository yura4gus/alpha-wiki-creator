# Hooks design

## L1 — Claude Code session hooks

Wired in `target/.claude/settings.local.json`. Scripts in `target/.claude/hooks/`.

| Hook | Matcher | Script | Purpose |
|---|---|---|---|
| `session-start` | always | `hooks/session-start.sh` | Loads `<wiki_dir>/graph/context_brief.md` into agent context |
| `pre-tool-use` | Write\|Edit on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/pre-tool-use.sh` | Validates frontmatter + reverse-link |
| `post-tool-use` | Write on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/post-tool-use.sh` | Debounced (5s) `wiki_engine.py rebuild-context-brief` |
| `session-end` | always | `hooks/session-end.sh` | `lint --suggest`, append log entry, echo summary |

## L2 — Git hooks

Wired by `assets/install-hooks.sh` into `.git/hooks/`.

- **pre-commit**: `tools/lint.py --fix`; fail if 🔴 remain after auto-fix; stage auto-fixes.
- **post-commit**: if `<wiki_dir>/**` touched → `wiki_engine.py rebuild-edges`.

## L3 — CI (GitHub Actions)

In `target/.github/workflows/`:

- **wiki-lint.yml** — `uv run python tools/lint.py` on push/PR; fails PR if 🔴.
- **wiki-review.yml** — weekly cron, headless `claude -p "/wiki:review"` → publishes issue.
- **wiki-rollup.yml** — monthly cron, headless `claude -p "/wiki:rollup month"` → commits rollup.

## Debouncing

`post-tool-use` rebuild is debounced 5s using a lockfile `<wiki_dir>/graph/.rebuild.lock` with timestamp.
If a rebuild is requested within 5s of the previous, the second call exits silently.
