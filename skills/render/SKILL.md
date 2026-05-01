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

- Red: repos, services, systems, bounded contexts, top-level architectural units.
- Green: modules, domains, components, core, ports, adapters, infrastructure.
- Blue: features, functions, user-facing flows, use-cases, application layer.
- Black: documents, decisions, specs, claims, papers, concepts, metrics, evidence pages.
- Orange: contracts at service boundaries.
- Light grey: people and tasks.

If graph colors look wrong, do not hack colors first. Check whether the page is in the wrong directory/type.

## Graph Reading Contract

The rendered graph should be understandable without reading page bodies:

- Red nodes are the architecture boundary map. A multi-repo project should show each repo/service as a red node.
- Green nodes cluster under red nodes and represent the modules/domains/components that make the service real.
- Blue nodes explain what the system does for users: features, functions, flows, use-cases.
- Black nodes are evidence and thinking: docs, decisions, specs, claims, papers, ideas.
- Orange nodes are contracts crossing boundaries. An orange node should usually touch at least one red owner and one consumer.

If a black document floats alone, the problem is usually missing links. If a module appears black, the problem is usually schema/directory placement. If a service appears green, the repo/service boundary is not explicit enough yet.

Color is not cluster. Do not build or describe one red cluster, one green cluster, one black cluster. A useful cluster normally mixes colors: red service boundary, green modules, blue features, black evidence, and orange contracts connected by typed links.

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
