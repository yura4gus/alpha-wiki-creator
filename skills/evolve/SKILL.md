---
name: evolve
description: "Add or refine wiki schema when real sources no longer fit existing entity types. Use when ingest repeatedly needs a new durable category, when a page type has different lifecycle/frontmatter needs, or when graph/color semantics require a new directory. Do not use for one-off pages or cosmetic taxonomy churn."
---

# wiki:evolve - grow the schema

## Mission

Let the wiki schema evolve from actual use. Alpha-Wiki should start small and grow only when the corpus proves a new type is needed.

## Name Contract

`evolve` means "change the operating schema". It is a gated schema operation, not normal content editing. Treat it like a small migration.

## When To Evolve

Use evolve when:

- A source cannot be represented honestly by existing entity types.
- A recurring concept needs its own lifecycle, required frontmatter, or required sections.
- Graph color semantics would be wrong if the content stayed in an existing directory.
- Lint/review repeatedly finds the same structural gap.

Do not evolve when:

- One page could be added as `source`, `resource`, `decision`, or `concept`.
- The user only wants a prettier folder name.
- The type would duplicate an existing type with different wording.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

Apply `references/concept.md` (Engineering Writing) to replies, authored
documents and helper prompts: short technical statements, compact sections,
no duplicated context, and no loss of requirements, exact diagnostics,
uncertainty or sources. Keep required schema; link shared context.

1. Read current schema:
   - `.alpha-wiki/config.yaml`
   - `AGENTS.md` for workflow, never as a second page schema.
   - `references/presets/` and `references/overlays/` if relevant.

2. Propose the type:
   - `name`: lowercase, slug-friendly.
   - `dir`: relative to `<wiki_dir>/`.
   - Purpose and lifecycle.
   - Required frontmatter.
   - Optional frontmatter.
   - Required sections.
   - Cross-reference rules.
   - Expected Obsidian color group by path.

3. Check conflicts:
   - Existing type names.
   - Existing directories.
   - Existing slugs.
   - Overlap with preset/overlay semantics.
   - Whether color grouping will be misleading.

4. Produce migration plan:
   - Pages that should move.
   - Pages that should stay.
   - Frontmatter fields to add.
   - Links that need reverse relations.
   - Index and graph rebuild requirements.

5. Gate the change:
   - Show the proposed schema diff.
   - Read `schema_evolve_mode` from config (default `gated` when absent). Ask for confirmation unless it is `auto`; do not infer permission from old instruction tables.

6. Apply:
   - Use `scripts.add_entity_type.add_entity_type` from the installed runtime to validate the new type, update config, create its wiki directory and append `schema-change`.
   - Preserve existing instructions and unrelated config fields. Invalid/escaping paths and duplicate types must fail before writes. Ordinary I/O failures roll back the call; abrupt process termination is not a multi-file atomic transaction.
   - Add a frontmatter template or change cross-reference rules only if the accepted migration explicitly needs them; these are not automatic helper outputs.
   - Rebuild graph.
   - Run lint.

7. Optional child skill:
   - Generate a project-local ingest helper only when the new type has a recurring ingestion workflow.

## Color Semantics

- Top-level service/module directories should map to red.
- Sub-component/core/domain/ports/use-case directories should map to green.
- Contracts should map to orange.
- Documents should map to dark grey.
- People/tasks should map to light grey.

If a new type does not fit these semantics, document whether `render` must update Obsidian color groups.

## Codex Native Delegation

Schema ownership stays with the controller. For repeated gaps across independent
domains, read-only subagents may collect:

- examples that do not fit the current schema;
- candidate existing types that were rejected and why;
- migration impact by directory or domain;
- graph/color and cross-reference consequences.

Subagents do not edit `AGENTS.md`, config, adapters, templates, directories, or pages.
The controller merges evidence into one proposed schema diff, requests the
required owner decision, and applies one migration. Run graph rebuild and lint
once after the final change. Follow
`references/codex-subagent-orchestration.md`.

## Done Criteria

- Schema diff is explicit.
- Migration plan exists even if no pages move.
- New type has frontmatter rules and section expectations.
- Graph rebuild and lint pass or produce known follow-ups.
- User can explain why the type exists.

## References

- `references/schema-evolution.md`
- `references/cross-reference-rules.md`
- `references/codex-subagent-orchestration.md`
- `assets/obsidian/COLOR-LEGEND.md`
