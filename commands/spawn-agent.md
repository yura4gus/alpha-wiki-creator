---
description: "Create wiki helper agent — maintainer, reviewer, or domain-specific"
argument-hint: "<name> <role>"
---

Invoke the `spawn-agent` skill from the `alpha-wiki` plugin. Human meaning: create a wiki-aware helper that follows Alpha-Wiki boundaries.

Arguments: $ARGUMENTS

Resolve `create-profile`, `run-now`, or `run-parallel` from the actual request.
A bare skill mention inside an engineering task does not create a helper scope.
For a requested profile, reuse supplied role details and create the native agent
file; record actual profile creation in the wiki log. For a one-off wiki task,
choose the smallest useful delegation. Preserve explicitly frozen reviewed
documents and their hashes. Commit only when authorized. Return concise results
and the actual activation or next action, if one is needed.
