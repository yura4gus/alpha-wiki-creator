# Platform Compatibility Matrix

Date: 2026-10-20

Scope: 0.8.0 (GOV-004, GPH and compact engineering writing). Existing projects
need an explicit runtime upgrade and deliberate merge of user-owned contracts.

## Verdict

Claude Code remains the primary interactive runtime. Current Codex CLI and desktop are supported through one namespaced `alpha-wiki` plugin surface, `AGENTS.md`, project hooks, and the same deterministic repository-local tools. Standalone skills are an explicit compatibility mode, not a parallel default install. Gemini is not packaged.

## Matrix

| Capability | Claude Code | Codex | Gemini |
|---|---|---|---|
| Install | Claude plugin marketplace | Personal Codex plugin via `scripts/install_codex.py`; optional standalone compatibility mode | Not implemented |
| Operation names | `/alpha-wiki:*` | `$alpha-wiki:*`; `$alpha-wiki-*` only in standalone compatibility mode | Not implemented |
| Agent instructions (GOV-004) | `.claude/CLAUDE.md` imports the shared `AGENTS.md`; existing user Claude instructions stay | Native `AGENTS.md`; user overrides remain user-controlled | Not implemented |
| Deterministic tools | Supported | Supported | Possible manually, not packaged |
| Session hooks | `.claude/settings.local.json` and `.claude/hooks` | `.codex/hooks.json` and `.codex/hooks`; includes `SubagentStart`; explicit trust required | Not supported |
| Git pre-commit hook | Generated when selected | Same generated git hook | Not supported |
| CI templates | Deterministic `tools.lint`, `tools.review`, `tools.rollup` | Same platform-neutral tools; no agent credential required | Not supported |
| Doctor | `--platform claude` | `--platform codex` checks CLI, one 16-skill package, duplicate surfaces, marketplace, `AGENTS.md`, and hooks | No check |
| Ingest/query/lint/status/review | Supported | Supported through plugin/skills and tools | Manual tools only |
| Obsidian/Mermaid/DOT/HTML | Supported | Supported | Manual tools only |
| Spawn wiki-aware subagent | `.claude/agents/*.md` | Native run-now/run-parallel plus optional `.codex/agents/*.toml` profiles | Not supported |
| Source-bound maintenance | Reviewed plan/apply when governance is configured | Same deterministic worker and full task acceptance | Not packaged |
| Engineering writing (0.8.0) | Shared skill rules and generated AGENTS import; passed to helpers | Same rules in native plugin and essential inline fallback guidance | Not packaged |
| Optional AgentOps control | Native agents plus summarized Markdown state | Bounded native scopes; no mandatory count or automatic fan-out | Not supported |

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

- GOV-004 native discovery was checked with Codex CLI 0.162.1 from a nested
  directory in fresh and existing projects. Claude 2.1.220 `/context` and
  `InstructionsLoaded` receipts confirm the imported AGENTS contract from
  both project roots, without a model call. That Claude version skipped the
  parent adapter's import on nested-directory startup: launch from repo root
  and verify `/context`. These checks prove discovery, not a live writer/reviewer
  implementation cycle or every managed-policy configuration.
- [Claude memory](https://code.claude.com/docs/en/memory) documents direct
  AGENTS support from 2.1.277, conditional on settings and existing Claude
  instruction files. The import adapter supports older versions without
  relying on direct AGENTS discovery. Occupied user adapters require explicit
  merge; doctor does not silently rewrite them.

- Installed plugin changes are discovered reliably in a new Codex task.
- Some Codex surfaces do not load plugins; install the standalone `$alpha-wiki-*` compatibility mode there with `--standalone`, which skips plugin installation.
- `spawn-agent` supports native one-off/parallel runs and Codex custom-agent TOML, but remains outside the first-run path.
- Hook trust is user-controlled and cannot be silently granted by Alpha-Wiki.
- Review/rollup scheduling remains deterministic CI, not background Codex sessions.
- AgentOps is opt-in and uses native platform agents; it is not a second runtime and is not part of first run.
- Gemini packaging is deferred.
- Fresh/brownfield subprocess tests verify tools and adapters, not live provider
  reasoning. The configured Claude provider returned HTTP 402 on 2026-10-19;
  the live cross-agent implementation/review pilot remains unaccepted.
- Runtime-only upgrades preserve the existing config. Maintenance requires an
  explicit document_governance policy; do not replace user schema to enable it.

## Release Language

- Say: "Claude Code primary; current Codex plugin supported; standalone adapter is an explicit compatibility mode."
- Say: "Codex project hooks require explicit trust."
- Do not say: "all agent platforms supported."
- Do not imply hooks replace lint, tests, or review.
