# Generated Artifacts Policy

Alpha-Wiki has generated files. They are useful, but they are not the source of truth.

## Source Of Truth

- `wiki/**/*.md`
- frontmatter
- wikilinks
- `.alpha-wiki/config.yaml`
- `CLAUDE.md`

## Generated But Useful

- `wiki/graph/edges.jsonl`
- `wiki/graph/context_brief.md`
- `wiki/graph/open_questions.md`
- `wiki/graph/graph.mmd`
- `wiki/graph/graph.dot`
- `wiki/render/html/**`

For this repository, generated graph and HTML files are tracked as release/demo snapshots so reviewers can inspect the exported shape without rerunning tools.

For target projects, teams may either:

- track generated snapshots when they are part of release review, or
- ignore them and regenerate locally/CI.

Do not hand-edit generated files. Rebuild them with:

```bash
uv run python -m tools.render_mermaid --wiki-dir wiki
uv run python -m tools.render_dot --wiki-dir wiki
uv run python -m tools.render_html --wiki-dir wiki
```

Obsidian runtime files such as `wiki/.obsidian/graph.json`, `workspace.json`, `app.json`, `appearance.json`, and `core-plugins.json` are local runtime state and should stay ignored unless a project intentionally publishes its vault settings.

