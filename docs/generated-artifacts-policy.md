# Generated Artifacts Policy

Alpha-Wiki has generated files. They are useful, but they are not the source of truth.

## Source Of Truth

- `README.md`
- `docs/**/*.md`
- `docs/examples/**/*.md`
- `wiki/**/*.md`
- `commands/**/*.md`
- `skills/*/SKILL.md`
- `templates/frontmatter/**`
- frontmatter
- wikilinks
- `.alpha-wiki/config.yaml`
- `CLAUDE.md`

## Generated But Useful Locally

- `wiki/graph/edges.jsonl`
- `wiki/graph/context_brief.md`
- `wiki/graph/open_questions.md`
- `wiki/graph/graph.mmd`
- `wiki/graph/graph.dot`
- `wiki/render/html/**`

For this repository, generated graph and HTML files are tracked only as intentional release/demo snapshots so reviewers can inspect the exported shape without rerunning tools.

For target projects, teams may either:

- track generated snapshots when they are part of release review, or
- ignore them and regenerate locally/CI.

Prefer deployed artifacts for public presentation:

- deploy generated HTML through GitHub Pages or another static host,
- deploy graph render outputs as part of that static site,
- keep large generated bundles out of source history unless they are intentional release evidence.

Do not hand-edit generated files. Rebuild them with:

```bash
uv run python -m tools.render_mermaid --wiki-dir wiki
uv run python -m tools.render_dot --wiki-dir wiki
uv run python -m tools.render_html --wiki-dir wiki
```

Obsidian runtime files such as `wiki/.obsidian/graph.json`, `workspace.json`, `app.json`, `appearance.json`, and `core-plugins.json` are local runtime state and should stay ignored unless a project intentionally publishes its vault settings.

## Public Repo Cleanup Notes

- `wiki/render/html/**`: tracked here as a beta demo snapshot; in most target projects, prefer deploy-only.
- `wiki/graph/**`: tracked here as deterministic graph/context evidence; in target projects, choose track-or-regenerate explicitly.
- `docs/files.zip`: historical uploaded document bundle and release noise. It is not required for install, runtime, docs deployment, or beta validation; remove it in a later cleanup once the original upload trail is no longer needed.
