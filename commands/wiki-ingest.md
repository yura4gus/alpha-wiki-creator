---
description: "Add raw sources (PRDs, ADRs, OpenAPI specs, transcripts, etc.) into the wiki"
argument-hint: "<file-paths…>"
---

Invoke the `ingest` skill from the `alpha-wiki` plugin to ingest the following raw artifacts into the wiki:

$ARGUMENTS

For each path: classify, match a slot or trigger schema-evolve (gated by default), render page(s), update index/log/graph. Surface any schema-evolve choices to the user before writing.
