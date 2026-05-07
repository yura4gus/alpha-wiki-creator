# Docs Publishing

Alpha-Wiki docs are repo-native. Markdown stays the source of truth; generated HTML is a readable deployment artifact.

## Source Of Truth

- `README.md`
- `docs/*.md`
- `docs/examples/*.md`
- `wiki/**/*.md`
- `commands/*.md`
- `skills/*/SKILL.md`
- `templates/frontmatter/**`
- `.alpha-wiki/config.yaml`

Agents should read the source markdown, not the deployed HTML, when they need durable project memory.

## Generated Output

Generated output is useful for humans and reviewers:

- static HTML docs site
- Mermaid and DOT graph snapshots
- rendered public documentation

Do not make generated HTML the source of truth. Rebuild it from markdown with:

```bash
python -m tools.render_html --wiki-dir wiki --out _site
```

## GitHub Pages

This repository uses a minimal GitHub Pages workflow that:

1. checks out the repo,
2. installs Alpha-Wiki,
3. renders `wiki/` to `_site`,
4. deploys `_site` through GitHub Pages.

GitHub Release objects are optional for Alpha-Wiki beta. The release tag is useful; a GitHub Release page is not required.

If Pages is not enabled yet, use repository Settings -> Pages -> Source: GitHub Actions, then run the `docs-pages` workflow.
