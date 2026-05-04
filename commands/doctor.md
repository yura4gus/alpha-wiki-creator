---
description: "Verify Alpha-Wiki install/runtime health: Python, tools, wiki dir, graph artifacts, hooks, CI, Codex/Claude adapters"
argument-hint: "[--refresh] [--strict] [--platform claude|codex|both|auto]"
---

Invoke the `doctor` skill from the `alpha-wiki` plugin. Human meaning: run one deterministic install and lifecycle health check before deeper wiki work.

Flags from the user (if any): $ARGUMENTS

Run: `uv run python tools/doctor.py --project-dir . $ARGUMENTS`

Report PASS/WARN/FAIL checks. Treat FAIL as blocking. Treat WARN as non-blocking unless `--strict` was requested. If `--refresh` was used, mention that graph artifacts were rebuilt before verification.
