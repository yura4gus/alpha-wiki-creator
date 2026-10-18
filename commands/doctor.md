---
description: "Verify Alpha-Wiki install/runtime health: Python, tools, wiki dir, graph artifacts, hooks, CI, Codex/Claude adapters"
argument-hint: "[--refresh] [--strict] [--platform claude|codex|both|auto]"
---

Invoke the `doctor` skill from the `alpha-wiki` plugin. Human meaning: run one deterministic install and lifecycle health check before deeper wiki work.

Flags from the user (if any): $ARGUMENTS

If the existing wiki has no `.alpha-wiki/run.py`, run the runtime-only upgrade from the installed plugin environment first; do not install dependencies into the product. Then run: `python3 .alpha-wiki/run.py -m tools.doctor --project-dir . $ARGUMENTS`

Report counts and decisive diagnostics concisely. A FAIL blocks only the required
operation that depends on the failed capability. WARN stays non-blocking unless
strict mode is requested or required by existing policy. If `--refresh` was
used, mention that graph artifacts were rebuilt. Apply Release Decisions in
`references/concept.md` for release judgments.
