---
description: "Start wiki memory — bootstrap Alpha-Wiki into this project"
argument-hint: "[project-description]"
---

Invoke the `init` skill from the `alpha-wiki` plugin. Human meaning: start durable project memory here.

Project description (optional, free text from the user): $ARGUMENTS

First inspect the existing project with `uv run python -m tools.init_audit --root . --wiki-dir <wiki_dir>`. Use that report to show:

- candidate source documents already in the repo;
- proposed `raw/` placement or manifest-only references;
- proposed wiki structure;
- processing batches for gradual ingest into small wiki pages.

Then walk the user through preset/overlay choice, render the scaffolding, run doctor/lint/status as sanity checks, and commit. Honor the full process described in the skill.
