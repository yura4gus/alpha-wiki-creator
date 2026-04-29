# Obsidian Graph Color Legend

The default `graph.json` color groups for an Alpha-wiki vault:

| Color | Hex | Meaning | Paths matched |
|---|---|---|---|
| 🔴 Red | `#E94B43` | **Service / repo / top-level architectural unit** | `modules/`, `bounded-contexts/`, `adapters/inbound/`, `application/` |
| 🟢 Green | `#4CAF50` | **Module / sub-component within a service** | `components/`, `core/`, `ports/`, `domains/`, `use-cases/` |
| ⚫ Dark grey | `#444B57` | **Document** (decisions, specs, concepts, APIs, entities, papers, summaries, claims, experiments, ideas, features, flows, metrics, personas, projects, areas, resources, journals, goals, sources, etc.) | All non-code page types |
| 🟠 Orange | `#FF7F00` | **Contract** (REST/GraphQL/gRPC/events/webhooks) — special category, lives at service boundaries | `contracts/` |
| ⚪ Light grey | `#A9A9A9` | **People / tasks** — meta layer | `people/`, `tasks/` |

## Reading the graph

- A **red node** with many outgoing dark-grey edges = a service that has accumulated docs (decisions, specs, APIs)
- A **green cluster around a red node** = a service with multiple sub-modules
- An **orange node bridging two red nodes** = a contract owned by one service and consumed by another
- An **isolated red node** = a service with no documented decisions/specs yet (lint flags this as a maintenance gap)

## Customizing

Edit `.obsidian/graph.json` → `colorGroups` array. Each entry is `{ "query": <Obsidian search query>, "color": { "a": 1, "rgb": <decimal> } }`.

Convert hex to decimal: `int("E94B43", 16)` in Python or `parseInt("E94B43", 16)` in JS.

## Why path-based, not tag-based

Alpha-wiki pages don't carry tags by default — they carry frontmatter (`type:`, `status:`, etc.). Obsidian's graph color groups support `path:` queries which match the directory layout we already enforce. Path-based grouping needs zero per-page maintenance.
