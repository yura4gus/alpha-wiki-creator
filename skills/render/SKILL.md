---
name: render
description: "Refresh the wiki presentation layer: Obsidian graph settings now, and static HTML/Mermaid/DOT exports when those backends are implemented. Use when colors, graph filters, vault settings, or generated visual artifacts are stale. Do not use to change wiki content."
argument-hint: "[obsidian | html | mermaid | dot]"
---

# wiki:render - visual and export layer

## Mission

Make the wiki inspectable. Render translates maintained markdown and graph artifacts into visual tools without becoming the source of truth.

## Name Contract

`render` means "refresh derived presentation". It must not author facts, rewrite pages, or change schema. Source of truth remains markdown/frontmatter plus generated graph artifacts.

## Modes

### `obsidian`

Refresh `.obsidian/` configuration:

- `graph.json`
- `community-plugins.json`
- `hotkeys.json`
- `workspace.json`
- `COLOR-LEGEND.md`

### `html`

Static HTML export target. If backend is not implemented, refuse clearly and point to the planned tool.

### `mermaid`

Graph diagram export target. Useful for PRs/docs snapshots. If backend is not implemented, refuse clearly.

### `dot`

Graphviz export target. Useful for dense graph inspection. If backend is not implemented, refuse clearly.

## Obsidian Color Semantics

Use path-based color groups:

- Red: services, repos, top-level architectural units.
- Green: modules, components, core/domain/ports/use-cases.
- Orange: contracts at boundaries.
- Dark grey: documents, decisions, specs, claims, papers, concepts, features, flows, metrics.
- Light grey: people and tasks.

If graph colors look wrong, do not hack colors first. Check whether the page is in the wrong directory/type.

## Workflow

1. Detect wiki dir and config.
2. Rebuild graph artifacts first:
   - `rebuild-edges`
   - `rebuild-context-brief`
   - `rebuild-open-questions`
3. For `obsidian`:
   - Copy/render Obsidian assets.
   - Ensure color groups match current directory semantics.
   - Preserve user-local customizations when possible; report conflicts.
4. For export modes:
   - Verify backend exists.
   - Refuse unsupported modes with a precise message, not a silent no-op.
5. Run `/alpha-wiki:lint --suggest` if graph data changed.

## Done Criteria

- Obsidian opens with meaningful color groups.
- Graph files are current.
- Unsupported modes fail explicitly.
- User knows whether color problems come from rendering or schema/page placement.

## References

- `assets/obsidian/COLOR-LEGEND.md`
- `assets/obsidian/graph.json`
- `tools/wiki_engine.py`
