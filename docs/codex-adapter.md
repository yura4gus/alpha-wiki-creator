# Codex Adapter

Alpha-Wiki is Claude Code-first, but its operational core is portable: skills are Markdown, deterministic tools are Python, and wiki state is plain files. Codex support is implemented as prefixed Codex skills that map back to the same Alpha-Wiki operations.

## Install

Install Codex CLI and sign in:

```bash
npm install -g @openai/codex
codex --login
```

Install Alpha-Wiki skill adapters:

```bash
git clone https://github.com/yura4gus/alpha-wiki-creator
cd alpha-wiki-creator
python3 scripts/install_codex.py
```

By default this writes to `$CODEX_HOME/skills` or `~/.codex/skills` if `CODEX_HOME` is unset.

Custom target:

```bash
python3 scripts/install_codex.py --target ~/.codex/skills
```

Dry run:

```bash
python3 scripts/install_codex.py --dry-run
```

## Command Mapping

| Claude Code | Codex skill |
|---|---|
| `/alpha-wiki:init` | `$alpha-wiki-init` |
| `/alpha-wiki:ingest` | `$alpha-wiki-ingest` |
| `/alpha-wiki:query` | `$alpha-wiki-query` |
| `/alpha-wiki:lint` | `$alpha-wiki-lint` |
| `/alpha-wiki:status` | `$alpha-wiki-status` |
| `/alpha-wiki:evolve` | `$alpha-wiki-evolve` |
| `/alpha-wiki:spawn-agent` | `$alpha-wiki-spawn-agent` |
| `/alpha-wiki:render` | `$alpha-wiki-render` |
| `/alpha-wiki:review` | `$alpha-wiki-review` |
| `/alpha-wiki:rollup` | `$alpha-wiki-rollup` |

## Why Prefixed Names

The repository skills are named `init`, `query`, `status`, etc. Those are good Claude slash-command names but too generic for a global Codex skill namespace. The installer rewrites frontmatter names to `alpha-wiki-*` while preserving the source skill body and adding a short Codex adapter note.

## Operating Notes

- Codex does not use Claude slash commands; ask it to use the corresponding `$alpha-wiki-*` skill.
- Keep the same Alpha-Wiki mutability matrix: source wiki pages are editable, `graph/` is generated, schema changes are gated.
- The Python tools remain the deterministic backend. Codex should prefer `tools/lint.py`, `tools/wiki_engine.py`, `tools/status.py`, `tools/review.py`, and `tools/rollup.py` over ad hoc text rewrites.
- Session hooks are Claude Code-specific. In Codex, run `$alpha-wiki-status`, `$alpha-wiki-lint`, or `$alpha-wiki-review` explicitly until a Codex-native automation layer is added.

## References

- OpenAI Codex CLI getting started: https://help.openai.com/en/articles/11096431
- OpenAI Codex CLI sign-in: https://help.openai.com/en/articles/11381614-codex-cli-and-sign-in-withgpt
