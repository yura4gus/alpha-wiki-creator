---
title: Alpha-Wiki Ingest Operation
slug: alpha-wiki-ingest-operation
kind: operation-spec
status: stable
date_updated: 2026-10-19
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/ingest.md, skills/ingest/SKILL.md, tools/ingest_pipeline.py
source_files:
  - skills/ingest/SKILL.md
  - tools/ingest_pipeline.py
  - tools/document_worker.py
  - tools/document_maintenance.py
  - docs/quickstart.md
---
# Alpha-Wiki Ingest Operation

## Provenance

- Shared workflow: `skills/ingest/SKILL.md`; Claude wrapper: `commands/ingest.md`.
- Import backend: `tools/ingest_pipeline.py`.
- Local maintenance backend: `tools/document_worker.py`, `tools/document_maintenance.py`.
- Operator procedure: `docs/quickstart.md` (Maintain Existing Documents).
- Release boundary: plan/apply, compaction and strict read-only reports require Alpha-Wiki 0.7; existing 0.6.2 installations need an explicit upgrade.

## Entities

- Operation: `/alpha-wiki:ingest` / `$alpha-wiki:ingest`.
- Inputs: durable local PRDs, ADRs, specifications, transcripts, API files, and research evidence.
- Layers: canonical documents, immutable evidence, working candidates, and generated views.
- Outputs: maintained typed pages, meaningful project journal records, and derived graph/context/questions.

## Requirements

- Preserve provenance and keep raw evidence immutable. Wiki summarizes and links to canonical sources; it does not replace API schemas or contracts.
- Search the existing canonical set before creating a page. A new document needs a distinct lifecycle and explicit ingest or registration.
- Repeated ingest of a bound source preserves its existing page instead of creating a numbered sibling or overwriting curated text.
- Use existing schema, stable slugs, status, and source metadata. Route repeated schema gaps to evolve.
- Keep one `belongs_to` ownership parent where applicable. Other typed links express contracts, dependencies, evidence, and affected entities; they do not confer decision authority.
- For maintenance, plan a bounded batch against `source_file`/`source_files`; pin source, target, and configuration hashes. The agent reads sources and supplies reviewed replacement text.
- Explicit compaction removes redundant prose while preserving metadata, references, and recognized normative sections, including nested requirements. Structural checks do not prove semantic truth.
- Apply source-owner changes before dependent projections and re-plan dependencies. Reject observed stale inputs or concurrent edits.
- Journal actual canonical edits once, then rebuild `edges.jsonl`, `context_brief.md`, and `open_questions.md`. Checkpoint only after refresh succeeds.
- Resume an interrupted transaction using its original plan and edits. Unchanged successful reruns create no new pages or journal noise; partial batches remain pending.

- The controller owns intake, source review, reviewed edits, apply, journal/graph reconciliation, governance/lint, cited retrieval and final task acceptance. An apply checkpoint proves only its batch; partial synchronization is not DONE.
- A checked no-change job creates no document journal entry. Strict no-write audits use a prepared environment, bytecode suppression and status/review read-only mode.
- Import captures a pending page before writing and finalizes its index, journal and graph before checkpointing. Retry preserves original pending inputs and refuses observed source or page drift; a later source failure does not strand earlier successful pages.

- Store new in-project bindings as repository-relative paths. Legacy moved/external absolute bindings are explicit maintenance gaps, never guessed remaps or automatic approval; unrelated hierarchy checks can still run.
- Journal deduplication identifies the pending import transaction, not every historical use of a slug. An explicitly retired page can be registered again by a new import.

## Gates

- Schema evolution follows the configured mode and authorized scope.
- Ambiguous claims remain assumptions, risks, or open questions. Maintenance does not ratify proposals, promote status, delete evidence, or archive documents automatically.
- Check canonical document/log pairing in both directions and validate ownership hierarchy.
- Preserve identity, status, ownership, and source bindings during maintenance; only `date_updated` may change. Explicit contract/status changes use a separate reviewed edit.
- Source bindings without checkpoints require review; missing bindings are unchecked coverage, not proof that all memory is fresh.
- Use the isolated project launcher for both Claude and Codex. No server, Temporal, model SDK, or implicitly running background author is required.
