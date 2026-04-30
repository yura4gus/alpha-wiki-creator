---
description: "Import sources — turn PRDs, ADRs, specs, transcripts into wiki pages"
argument-hint: "<file-paths…>"
---

Invoke the `ingest` skill from the `alpha-wiki` plugin. Human meaning: import raw evidence into maintained wiki pages:

$ARGUMENTS

For each path: classify, match a slot or trigger schema-evolve (gated by default), render page(s), update index/log/graph. Surface any schema-evolve choices to the user before writing.
