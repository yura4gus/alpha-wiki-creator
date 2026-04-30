---
name: evolve
description: "Add or refine wiki schema when real sources no longer fit existing entity types. Use when ingest repeatedly needs a new durable category, when a page type has different lifecycle/frontmatter needs, or when graph/color semantics require a new directory. Do not use for one-off pages or cosmetic taxonomy churn."
argument-hint: "<type-name> [--generate-skill]"
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

1. Read current schema:
   - `CLAUDE.md`
   - `.alpha-wiki/config.yaml`
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
   - Ask for confirmation unless schema evolution mode is `auto`.

6. Apply:
   - Update `CLAUDE.md`.
   - Create directory.
   - Add frontmatter template.
   - Update config/schema files.
   - Append log entry: `schema-change`.
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

## Done Criteria

- Schema diff is explicit.
- Migration plan exists even if no pages move.
- New type has frontmatter rules and section expectations.
- Graph rebuild and lint pass or produce known follow-ups.
- User can explain why the type exists.

## References

- `references/schema-evolution.md`
- `references/cross-reference-rules.md`
- `assets/obsidian/COLOR-LEGEND.md`
