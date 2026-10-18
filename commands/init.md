---
description: "Start wiki memory — bootstrap Alpha-Wiki into this project"
argument-hint: "[project-description]"
---

Invoke the `init` skill from the `alpha-wiki` plugin. Human meaning: start durable project memory here.

Project description (optional, free text from the user): $ARGUMENTS

Before init, inspect the target with `tools.init_audit --root <absolute-project> --wiki-dir <wiki_dir>` from the installed plugin environment. After init, run project tools through `python3 .alpha-wiki/run.py -m tools.<module>`. Do not add wiki dependencies to the product. Use the audit report to show:

- candidate source documents already in the repo;
- proposed `raw/` placement or manifest-only references;
- proposed wiki structure;
- processing batches for gradual ingest into small wiki pages.

Then walk the user through preset/overlay choice, render the scaffolding, run doctor/lint/status as sanity checks, and commit. Honor the full process described in the skill.
