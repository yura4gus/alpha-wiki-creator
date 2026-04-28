# Sample Wiki

Preset: software-project
Overlay: none
Wiki dir: `wiki/`

## Mutability Matrix
- L1 Raw: `raw/**` — human only
- L2 Wiki: `wiki/**` excluding `wiki/graph/**` — LLM-mutable
- L3 Derived: `wiki/graph/**` — auto-generated
- L4 Schema: `CLAUDE.md`, `.claude/**` — gated

## Page Types
| Type | Dir | Required frontmatter |
|---|---|---|
| module | `modules/` | title, slug, status |
| decision | `decisions/` | title, slug, status, date |
| contract | `contracts/<transport>/` | title, slug, transport, service, status |

## Cross-Reference Rules
- module `depends_on: [[X]]` → X.dependents adds source
- contract `service: [[M]]` → M.## Provides adds contract
- decision `affects: [[X]]` → X.## Decisions adds decision

## Skills
- /wiki:init, /wiki:ingest, /wiki:query, /wiki:lint, /wiki:evolve, /wiki:spawn-agent, /wiki:render, /wiki:status
