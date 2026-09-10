# Platform Compatibility Matrix

Date: 2026-09-10

Scope: Alpha-Wiki v0.6.x runtime and Codex adaptation.

## Verdict

Claude Code remains the primary interactive runtime. Current Codex CLI and desktop are supported through one namespaced `alpha-wiki` plugin surface, `AGENTS.md`, project hooks, and the same deterministic repository-local tools. Standalone skills are an explicit compatibility mode, not a parallel default install. Gemini is not packaged.

## Matrix

| Capability | Claude Code | Codex | Gemini |
|---|---|---|---|
| Install | Claude plugin marketplace | Personal Codex plugin via `scripts/install_codex.py`; optional standalone compatibility mode | Not implemented |
| Operation names | `/alpha-wiki:*` | `$alpha-wiki:*`; `$alpha-wiki-*` only in standalone compatibility mode | Not implemented |
| Agent instructions | `CLAUDE.md` | `AGENTS.md` pointing to the shared contract and context brief | Not implemented |
| Deterministic tools | Supported | Supported | Possible manually, not packaged |
| Session hooks | `.claude/settings.local.json` and `.claude/hooks` | `.codex/hooks.json` and `.codex/hooks`; includes `SubagentStart`; explicit trust required | Not supported |
| Git pre-commit hook | Generated when selected | Same generated git hook | Not supported |
| CI templates | Deterministic `tools.lint`, `tools.review`, `tools.rollup` | Same platform-neutral tools; no agent credential required | Not supported |
| Doctor | `--platform claude` | `--platform codex` checks CLI, one 16-skill package, duplicate surfaces, marketplace, `AGENTS.md`, and hooks | No check |
| Ingest/query/lint/status/review | Supported | Supported through plugin/skills and tools | Manual tools only |
| Obsidian/Mermaid/DOT/HTML | Supported | Supported | Manual tools only |
| Spawn wiki-aware subagent | `.claude/agents/*.md` | Native run-now/run-parallel plus optional `.codex/agents/*.toml` profiles | Not supported |
| Optional AgentOps control | Native agents plus summarized Markdown state | Native subagents plus summarized Markdown state; 2-4 agents by default, 6 only by explicit request | Not supported |

## Codex First Run

```bash
python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone
codex
```

Then use:

```text
$alpha-wiki:init
$alpha-wiki:doctor
$alpha-wiki:ingest
$alpha-wiki:query
$alpha-wiki:status
$alpha-wiki:render
```

After init, open `/hooks` once to review and trust the generated project hooks.

## Known Limitations

- Installed plugin changes are discovered reliably in a new Codex task.
- Some Codex surfaces do not load plugins; install the standalone `$alpha-wiki-*` compatibility mode there with `--standalone`, which skips plugin installation.
- `spawn-agent` supports native one-off/parallel runs and Codex custom-agent TOML, but remains outside the first-run path.
- Hook trust is user-controlled and cannot be silently granted by Alpha-Wiki.
- Review/rollup scheduling remains deterministic CI, not background Codex sessions.
- AgentOps is opt-in and uses native platform agents; it is not a second runtime and is not part of first run.
- Gemini packaging is deferred.

## Release Language

- Say: "Claude Code primary; current Codex plugin supported; standalone adapter is an explicit compatibility mode."
- Say: "Codex project hooks require explicit trust."
- Do not say: "all agent platforms supported."
- Do not imply hooks replace lint, tests, or review.
