# Obsidian Graph Color Legend

The default `graph.json` color groups for an Alpha-wiki vault:

Default graph filter: `path:.wiki/ OR path:wiki/`. This keeps the global graph focused on maintained wiki pages when the whole repository is opened as an Obsidian vault. Raw sources, command manuals, skill source files, tests, and generated exports remain searchable in Obsidian, but they are not part of the default trust graph. Color groups match three layouts: root vault with `.wiki/...`, root vault with `wiki/...`, and a vault opened directly inside the wiki directory.

| Color | Hex | Meaning | Paths matched |
|---|---|---|---|
| 🔴 Red | `#E94B43` | **Repo / service / top-level architectural unit** | `services/`, `repos/`, `repositories/`, `systems/`, `bounded-contexts/`, `applications/` |
| 🟢 Green | `#16A34A` | **Module / domain / sub-component inside a service** | `modules/`, `components/`, `core/`, `ports/`, `domains/`, `adapters/`, `infrastructure/` |
| 🔵 Blue | `#2563EB` | **Feature / function / user-facing flow** | `features/`, `flows/`, `use-cases/`, `application/` |
| ⚫ Black | `#111111` | **Document / evidence page** (decisions, specs, concepts, APIs, entities, papers, summaries, claims, experiments, ideas, metrics, personas, projects, areas, resources, journals, goals, sources, etc.) | All non-code page types |
| 🟠 Orange | `#F97316` | **Contract** (REST/GraphQL/gRPC/events/webhooks) — special category, lives at service boundaries | `contracts/` |
| ⚪ Light grey | `#A9A9A9` | **People / tasks** — meta layer | `people/`, `tasks/` |

## Reading the graph

- A **red node** = a separate repo/service/system boundary. In a multi-repo architecture, red nodes are the first thing to orient by.
- A **green cluster around a red node** = modules, domains, or components that live inside that service.
- A **blue node connected to green nodes** = a feature/function/flow implemented by one or more modules.
- A **black node attached to red/green/blue nodes** = documentary evidence: decisions, specs, claims, papers, ideas, metrics.
- An **orange node bridging two red nodes** = a contract owned by one service and consumed by another
- An **isolated red node** = a service with no documented decisions/specs yet (lint flags this as a maintenance gap)
- A **black island** = a document that has not been attached to the architecture yet; link it or archive it.

If the graph shows README/SKILL/source-manifest/old docs scattered everywhere, the graph filter is off or the vault was opened with an older `.obsidian/graph.json`. Restore the default search filter above and keep unresolved links hidden.

## Color is not cluster

Do not interpret one color as one cluster. Obsidian layout clusters should emerge from typed wikilinks and shared architecture boundaries. Color answers "what kind of node is this?", not "which subgraph does this belong to?"

Good graph shape:

- One service cluster can contain red, green, blue, black, and orange nodes.
- One color can appear in many different clusters.
- Cross-service contracts are orange bridges, not a separate orange island.
- A black document cluster with no red/green/blue attachment is usually a documentation gap.

## Grouping rule

Use the directory to express the graph layer:

1. Repo/service boundary → red.
2. Internal module/domain/component → green.
3. Feature/function/flow → blue.
4. Evidence document → black.
5. Integration contract → orange.
6. Work/people metadata → light grey.

Do not recolor individual pages as a workaround. If a node has the wrong color, move it to the correct semantic directory or evolve the schema.

## Customizing

Edit `.obsidian/graph.json` → `colorGroups` array. Each entry is `{ "query": <Obsidian search query>, "color": { "a": 1, "rgb": <decimal> } }`.

Convert hex to decimal: `int("E94B43", 16)` in Python or `parseInt("E94B43", 16)` in JS.

## Why path-based, not tag-based

Alpha-wiki pages don't carry tags by default — they carry frontmatter (`type:`, `status:`, etc.). Obsidian's graph color groups support `path:` queries which match the directory layout we already enforce. Path-based grouping needs zero per-page maintenance and makes color a schema signal, not decoration.
