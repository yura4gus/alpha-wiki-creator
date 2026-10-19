---
name: ingest
description: "Convert durable source material into maintained wiki pages with provenance, frontmatter, links, and graph updates. Use for PRDs, ADRs, specs, transcripts, research notes, OpenAPI files, decisions, meeting notes, and any source the project should remember. Do not use for one-off answers or unsupported content that should remain conversational."
---

# wiki:ingest - source to wiki memory

## Mission

Turn durable sources into maintained, typed Markdown memory. Reuse the page that already owns the topic. Not every source needs another page: some are evidence for an existing document, and some should remain working material.

## Name Contract

`ingest` means "persist source knowledge". It is not "summarize and forget". If the result will not be linked, queried, reviewed, or maintained, answer conversationally instead.

## Operating Principles

- Preserve provenance. The page must say where the knowledge came from.
- Keep raw source immutable. Copy or reference source files under `raw/`; do not rewrite source evidence.
- Use the existing schema first. Evolve only when no existing entity type can hold the source cleanly.
- Search the canonical document set before writing. Update the document that already owns the topic instead of creating a dated sibling or a second standard.
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

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

1. Validate inputs:
   - Paths exist or URLs are fetchable by the current environment.
   - Source is not inside `<wiki_dir>/graph/`.
   - Source is not an auto-generated output being recursively ingested.

2. Read the current wiki operating context:
   - `AGENTS.md`
   - `<wiki_dir>/index.md`
   - `<wiki_dir>/graph/context_brief.md`
   - `.alpha-wiki/config.yaml`

3. For each source:
   - Check existing `source_file`/`source_files` bindings before importing. A repeated pipeline call preserves an existing owner; it does not refresh its prose or create a numbered sibling.
   - Run the pipeline only for a requested source import. A narrow repair of an
     existing document needs its applicable checks, not another ingest batch.
     A diagnosis-only request does not authorize import or dependency changes.
   - On an import failure, verify the installed Alpha-Wiki executable and
     module path before choosing a retry. Do not inject its dependencies into
     an unrelated target project or claim an untested runtime path works.
   - Classify and write the first deterministic page with:
     - `python3 .alpha-wiki/run.py -m tools.ingest_pipeline --wiki-dir <wiki_dir> <source>`
   - Use `--slot <dir>` when the target directory is obvious.
   - Use `--belongs-to <slug>` when attaching the page to a service/repo/module cluster.
   - Use `--resume` for interrupted batches; resume state lives in `<wiki_dir>/graph/ingest_state.json`.
   - Preserve pending ingest state after failure. Retry with its original source;
     source/page drift requires explicit reconciliation, not deleting the state.
     Each new page is indexed, journaled and graph-refreshed before its completion
     checkpoint. Already owned pages remain curated maintenance targets.
   - Read enough surrounding wiki pages to avoid duplicates.
   - Extract durable facts, decisions, open questions, risks, contracts, dependencies, dates, owners, and claims.
   - Keep uncertain statements marked as `assumption`, `risk`, or `open`.

4. Write or update pages:
   - Prefer an in-place update to the existing canonical page.
   - Create a new canonical page only when it has an independent owner and lifecycle, no existing page can absorb it, and the expansion is explicitly acknowledged.
   - Required frontmatter first.
   - Body sections according to entity type.
   - Provenance section with raw path, source date if known, and ingest date.
   - Wikilinks for related modules, decisions, contracts, claims, people, tasks, and sources.
   - Status: `draft`, `active`, `accepted`, `stable`, `deprecated`, or `stub` as appropriate.

### Existing Documents And Compaction

Use Engineering Writing for the maintained result: a short purpose, concrete
behavior/contracts, applicable acceptance, open gaps and source links. Retain
all required schema sections. Replace repeated context with references; do not
turn a concise projection into a second specification or omit qualifications.

Use the installed `tools.document_worker plan/apply` capability when available;
older packages may only provide `check/record`. Inspect `--help` before using an
unreleased capability. Do not install dependencies in the product environment.

- Plan one bounded document/domain batch. `plan --document <path>` resolves
  repository-relative `source_file`/`source_files` and pins their content hashes.
- Read the actual sources and prepare JSON `updates` with each `document` and
  full replacement `text`, plus a concise `summary`. Apply only reviewed edits.
- `--compact` requires explicit documents. Preserve frontmatter except
  `date_updated`, all references, and protected normative sections verbatim.
  Use ordinary reviewed refresh for changes to requirements or decisions; neither
  mode provides semantic truth resolution or authority to accept a proposal.
- `apply --plan <json> --edits <json>` updates existing documents, journals actual
  edits once, refreshes graph/brief/questions, and checkpoints success. Repeated
  unchanged inputs need no model run. Apply changed source owners first, then
  re-plan their dependent projections.
- If interrupted, retain the original plan, edits, and pending transaction.
  Resume that apply. Do not reset progress or overwrite concurrent human edits.

Treat the request as one closed-loop job, not a series of operator-owned CLI
steps. Establish scope, authorized writes, relevant sources, acceptance, and
requested final environment. Review the source, plan and apply the bounded
updates, then run governance/lint, current status/review, and a targeted cited
query. Verify no-op replay where maintenance repeatability is in scope. Close
the owning task only after its acceptance passes; an apply checkpoint proves
that batch, not the whole task. If synchronization fails after a source edit,
retain resumable progress and report partial completion. A checked no-change
job creates no document-change journal entry. Report actual writes, checks,
remaining gaps, and local/published/installed capability separately. Use
`references/concept.md` (Delivery Evidence And Contract Ownership) for contract
or delivery work; ingestion does not authorize ratification or deployment.
- Use the project's configured journal. A cross-repository overview links to
  local records instead of copying complete histories. Do not create another
  research report merely to describe a successful maintenance run.

5. Maintain the graph:
   - Run `rebuild-edges`.
   - Run `rebuild-context-brief`.
   - Run `rebuild-open-questions`.
   - Run `/alpha-wiki:lint --suggest`.

6. Update service files:
   - Add discoverable entries to `<wiki_dir>/index.md` if the current index process requires it.
   - Append `<wiki_dir>/log.md`: `## [YYYY-MM-DD] ingest | <source> | <pages>`.
   - Run `python3 .alpha-wiki/run.py -m tools.document_worker check --root . --config .alpha-wiki/config.yaml` so every canonical edit is paired with the global log and every log claim is backed by a real edit.

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
- Document proliferation: keep research as evidence outside the canonical set; promote it only when it becomes an accepted specification, contract, decision, or standard.
- Unknown schema: route to `/alpha-wiki:evolve`.
- Oversized source: deterministic pipeline truncates the excerpt; ingest in sections if omitted material contains decisions, risks, or contracts.
- Interrupted batch: rerun with `--resume`.
- Ambiguous truth: write as assumption/risk/open question with provenance.
- Broken graph: stop and run `/alpha-wiki:lint --fix` before continuing.

## Codex Native Delegation

Use two-phase delegation only when multiple independent sources justify it:

1. The controller pins the active scope and assigns each source or source batch
   to a read-only analyzer.
2. Analyzers return classification, durable facts, provenance, proposed target
   page, candidate links, conflicts, unknowns, and status. They do not edit
   `raw/**`, wiki pages, service files, config, or graph artifacts.
3. The controller rejects duplicate page proposals and schema assumptions.
4. One curator writer applies the accepted batch. A shared page, `index.md`, and
   `log.md` have one writer per wave.
5. The controller runs the deterministic ingest pipeline, graph rebuild, lint,
   and status once after integration.

For one source or one tightly connected document set, stay single-agent. Follow
`references/codex-subagent-orchestration.md`.

## References

- `references/classifier.md`
- `references/schema-evolution.md`
- `references/cross-reference-rules.md`
- `references/concept.md`
- `references/codex-subagent-orchestration.md`
- `tools/ingest_pipeline.py`
