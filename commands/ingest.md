---
description: "Import sources — turn PRDs, ADRs, specs, transcripts into wiki pages"
argument-hint: "<file-paths…>"
---

Invoke the `ingest` skill from the `alpha-wiki` plugin. Human meaning: import raw evidence into maintained wiki pages:

$ARGUMENTS

Run deterministic ingest first:

`uv run python tools/ingest_pipeline.py --wiki-dir <wiki_dir> $ARGUMENTS`

Use `--resume` for long or interrupted batches. For each path: classify, match a slot or trigger schema-evolve (gated by default), render page(s) with provenance, update log/graph, then surface lint warnings. If deterministic ingest cannot place the source cleanly, stop and surface schema-evolve choices before writing custom structure.
