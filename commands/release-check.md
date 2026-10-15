---
description: "Check project release readiness from AgentOps backlog, sessions, handoffs, and wiki lint"
argument-hint: "--version <target> [--write]"
---

Invoke the `release-check` skill from the `alpha-wiki` plugin.

Human meaning: decide whether the target project can advance toward release or
which concrete evidence still blocks it.

Arguments: $ARGUMENTS

This checks the target project's operational evidence. It does not replace the
Alpha-Wiki package's own `tools.release_audit`.

Use the existing release requirements. Preserve the backend verdict and scope;
show requirement, failure, affected step, and smallest fix for each blocker.
Keep missing evidence and optional follow-ups distinct. Do not add new signing,
secrets, or approval requirements. Add `--write` only when persistence is requested.
Apply Release Decisions in `references/concept.md`.
