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

## Release Checklist

Every release **must** bump the version. The marketplace source tracks `main`, and `claude plugin update` compares version strings — if the version does not change, installed clients keep serving a stale build even after commits land on `main`.

1. **Bump the version** in all three manifests so they agree:
   - `.claude-plugin/plugin.json` -> `version`
   - `.claude-plugin/marketplace.json` -> `metadata.version` and the `plugins[].version` entry
   - `pyproject.toml` -> `version`
2. **Update `CHANGELOG.md`** with a new `## [x.y.z]` section (keep prior sections; `tests/unit/test_audit_docs.py` asserts historical entries stay present).
3. **Run the gates:**
   ```bash
   uv run pytest -q
   uv run python -m tools.release_audit   # expect: Verdict READY, 0 fail
   claude plugin validate .
   ```
4. **Commit, tag, push:**
   ```bash
   git add .
   git commit -m "release: cut vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```
5. **Optional:** publish a GitHub Release for the tag (the tag alone is enough for the marketplace; a Release page is only for human-facing notes).
6. **Consumers update** with the reinstall flow documented in the README "Updating" section.
