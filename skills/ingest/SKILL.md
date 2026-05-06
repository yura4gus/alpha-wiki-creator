---
name: ingest
description: "Convert durable source material into maintained wiki pages with provenance, frontmatter, links, and graph updates. Use for PRDs, ADRs, specs, transcripts, research notes, OpenAPI files, decisions, meeting notes, and any source the project should remember. Do not use for one-off answers or unsupported content that should remain conversational."
argument-hint: "<file-paths...>"
---

# wiki:ingest - source to wiki memory

## Mission

Turn raw evidence into durable, typed markdown memory. Ingest is the main growth mechanism of Alpha-Wiki: every useful source should become one or more pages that future agents can read, cite, link, lint, and evolve.

## Name Contract

`ingest` means "persist source knowledge". It is not "summarize and forget". If the result will not be linked, queried, reviewed, or maintained, answer conversationally instead.

## Operating Principles

- Preserve provenance. The page must say where the knowledge came from.
- Keep raw source immutable. Copy or reference source files under `raw/`; do not rewrite source evidence.
- Use the existing schema first. Evolve only when no existing entity type can hold the source cleanly.
- Prefer one coherent page over many tiny pages, but split when different entities need independent lifecycle.
- Every new page needs frontmatter, stable slug, status, and cross-links.
- Links are maintenance obligations: if a page links forward, lint must be able to verify reverse links or report a clear fix.

## Classification Discipline

1. Identify artifact type: decision, spec, module, contract, claim, paper, task, feature, flow, persona, source, etc.
2. Match artifact to preset/overlay directories.
3. If multiple slots fit, choose the one with the strongest lifecycle owner.
4. If no slot fits, propose:
   - New entity type via `/alpha-wiki:evolve`.
   - Section append to an existing page.
   - `source` or `resource` page if the source is reference material rather than a domain entity.
5. In `gated` mode, ask before schema evolution.

## Workflow

1. Validate inputs:
   - Paths exist or URLs are fetchable by the current environment.
   - Source is not inside `<wiki_dir>/graph/`.
   - Source is not an auto-generated output being recursively ingested.

2. Read the current wiki operating context:
   - `CLAUDE.md`
   - `<wiki_dir>/index.md`
   - `<wiki_dir>/graph/context_brief.md`
   - `.alpha-wiki/config.yaml`

3. For each source:
   - Classify and write the first deterministic page with:
     - `uv run python -m tools.ingest_pipeline --wiki-dir <wiki_dir> <source>`
   - Use `--slot <dir>` when the target directory is obvious.
   - Use `--belongs-to <slug>` when attaching the page to a service/repo/module cluster.
   - Use `--resume` for interrupted batches; resume state lives in `<wiki_dir>/graph/ingest_state.json`.
   - Read enough surrounding wiki pages to avoid duplicates.
   - Extract durable facts, decisions, open questions, risks, contracts, dependencies, dates, owners, and claims.
   - Keep uncertain statements marked as `assumption`, `risk`, or `open`.

4. Write or update pages:
   - Required frontmatter first.
   - Body sections according to entity type.
   - Provenance section with raw path, source date if known, and ingest date.
   - Wikilinks for related modules, decisions, contracts, claims, people, tasks, and sources.
   - Status: `draft`, `active`, `accepted`, `stable`, `deprecated`, or `stub` as appropriate.

5. Maintain the graph:
   - Run `rebuild-edges`.
   - Run `rebuild-context-brief`.
   - Run `rebuild-open-questions`.
   - Run `/alpha-wiki:lint --suggest`.

6. Update service files:
   - Add discoverable entries to `<wiki_dir>/index.md` if the current index process requires it.
   - Append `<wiki_dir>/log.md`: `## [YYYY-MM-DD] ingest | <source> | <pages>`.

## Graph And Obsidian Discipline

- Red nodes should represent repos, services, systems, or top-level architectural units.
- Green nodes should represent modules, domains, components, adapters, infrastructure, core, or ports.
- Blue nodes should represent features, functions, flows, use-cases, or application-layer behavior.
- Orange nodes should be boundary contracts and must link to owners/consumers.
- Black nodes should be documents/evidence: decisions, specs, claims, papers, concepts, metrics.
- Light grey nodes should be people/tasks.
- Color is not cluster. If a page has the wrong color, the directory/type choice is probably wrong. Fix the slot before ingesting more content.

## Quality Bar

- A future agent can answer "where did this fact come from?"
- A future agent can find the page from `index.md` or `context_brief.md`.
- The page has enough links to sit in the graph, but not so many that everything links to everything.
- Open questions are explicit.
- Contradictions are surfaced, not smoothed over.

## Failure Modes

- Duplicate page: merge or update the existing page instead of creating a sibling.
- Unknown schema: route to `/alpha-wiki:evolve`.
- Oversized source: deterministic pipeline truncates the excerpt; ingest in sections if omitted material contains decisions, risks, or contracts.
- Interrupted batch: rerun with `--resume`.
- Ambiguous truth: write as assumption/risk/open question with provenance.
- Broken graph: stop and run `/alpha-wiki:lint --fix` before continuing.

## References

- `references/classifier.md`
- `references/schema-evolution.md`
- `references/cross-reference-rules.md`
- `references/concept.md`
- `tools/ingest_pipeline.py`
