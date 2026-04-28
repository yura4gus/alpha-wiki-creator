---
name: wiki-render
description: Use when the user wants to refresh or regenerate the visual layer of the wiki — Obsidian config or static HTML. Triggers include "refresh obsidian config", "render wiki to html", "regenerate dashboards", "update vault settings". For initial bootstrap, `/wiki-init` already creates the Obsidian config; use this skill for refresh or HTML output.
---

# wiki-render — refresh wiki UI artifacts

## Modes

### `obsidian`

- Reads current preset+overlay config.
- Refreshes `.obsidian/graph.json` colors and filters to match the current page-type set.
- Ensures `community-plugins.json` enables Dataview.
- Idempotent — re-run safe.

### `html`

- Renders a static site to `dist/wiki/`:
  - `index.html` from `<wiki_dir>/index.md`
  - One HTML page per markdown file
  - Graph view via D3 (read from `graph/edges.jsonl`)
- Uses `markdown` Python library with `wikilinks` extension.
- Suitable for GitHub Pages.

## Process

1. Determine mode: `--mode obsidian` (default) | `--mode html`
2. For `obsidian`:
   - Re-render `.obsidian/graph.json` from current config.
   - Update `.obsidian/community-plugins.json` if needed.
3. For `html`:
   - `uv run python tools/render_html.py --wiki-dir <wiki_dir> --out dist/wiki/`
   - Print path to `dist/wiki/index.html`.

## Notes

`tools/render_html.py` is added at v0.2 — initial release ships `obsidian` mode only. The `html` mode is documented here for forward compatibility but the skill should refuse `--mode html` and point to `references/concept.md` until v0.2 lands.
