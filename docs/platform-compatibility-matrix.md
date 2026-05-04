# Platform Compatibility Matrix

Date: 2026-05-04

Scope: Alpha-Wiki standalone plugin.

## Verdict

Claude Code is the primary supported runtime. Codex is supported through prefixed skill adapters plus deterministic repository-local tools. Gemini is not supported for v1.0 packaging unless a real adapter is added and tested.

## Matrix

| Capability | Claude Code | Codex | Gemini |
|---|---|---|---|
| Install plugin/skills | Supported through Claude plugin install | Supported through `scripts/install_codex.py` | Not implemented |
| Operation names | `/alpha-wiki:*` slash commands | `$alpha-wiki-*` skills | Not implemented |
| Deterministic tools | Supported | Supported | Possible manually, not packaged |
| Session hooks | Supported through `.claude/hooks` | Not supported; run explicit commands | Not supported |
| Git pre-commit hook | Supported when generated | Supported if project installs generated git hook manually | Not supported |
| CI templates | GitHub Actions templates use Claude headless commands | Lint/tool-only workflows can be adapted manually | Not supported |
| Doctor check | `tools/doctor.py --platform claude` | `tools/doctor.py --platform codex` | No platform check |
| Ingest/query/lint/status/review | Supported | Supported via prefixed skills and tools | Manual tools only |
| Render Obsidian/Mermaid/DOT/HTML | Supported | Supported via tools | Manual tools only |
| Spawn wiki-aware subagent | Claude-focused | Skill docs available; no native subagent automation | Not supported |

## Codex Operating Model

Codex does not receive Claude slash commands or Claude hooks. The release-safe Codex flow is explicit:

```bash
python3 scripts/install_codex.py
codex
```

Then ask Codex to use:

- `$alpha-wiki-init`
- `$alpha-wiki-doctor`
- `$alpha-wiki-ingest`
- `$alpha-wiki-query`
- `$alpha-wiki-lint`
- `$alpha-wiki-status`
- `$alpha-wiki-review`
- `$alpha-wiki-render`
- `$alpha-wiki-rollup`

## Known Limitations

- Codex has no native session-start/session-end hook equivalent in this repo.
- Codex review/rollup automation is manual unless a user wires their own scheduler around deterministic tools.
- Gemini packaging is deferred; do not claim Gemini support in release notes.
- Headless Claude CI workflows require the user's Claude credentials/secrets and must fail clearly when absent.

## Release Position

For public release language:

- Say: "Claude Code primary; Codex adapter supported."
- Do not say: "all agent platforms supported."
- Do not say: "Codex has equivalent hooks."
