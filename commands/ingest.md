---
description: "Import sources — turn PRDs, ADRs, specs, transcripts into wiki pages"
argument-hint: "<file-paths…>"
---

Invoke the `ingest` skill from the `alpha-wiki` plugin. Human meaning: import raw evidence into maintained wiki pages:

$ARGUMENTS

Run the deterministic pipeline for a requested source import:

`python3 .alpha-wiki/run.py -m tools.ingest_pipeline --wiki-dir <wiki_dir> $ARGUMENTS`

Use `--resume` for interrupted batches. Classify sources, reuse existing pages,
preserve provenance, and update applicable log/graph artifacts. An existing
document repair needs only its applicable checks; a diagnostic request does not
authorize an import. A launch failure calls for checking the known Alpha-Wiki
runtime and import path, not adding dependencies to an unrelated product.
Schema evolution follows the existing project mode and authorized scope.

For already-owned sources, preserve the existing page. When the installed tool
supports it, use `document_worker plan/apply` from the shared skill for reviewed
source updates or explicitly scoped compaction. Do not create numbered copies,
overwrite curated content with an excerpt, or treat hook execution as a running
background author.
