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
