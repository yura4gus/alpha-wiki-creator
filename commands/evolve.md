---
description: "Add a new entity type to the wiki schema (updates CLAUDE.md, creates dir, logs schema-change)"
argument-hint: "<type-name> [--generate-skill]"
---

Invoke the `evolve` skill from the `alpha-wiki` plugin to add a new entity type to the wiki schema.

Arguments: $ARGUMENTS

Collect the type spec interactively (name, dir, required/optional frontmatter, sections, cross-ref rules). Show the proposed CLAUDE.md diff and confirm before writing. Run `scripts/add_entity_type.py`. Commit with `[schema-change]` tag and append to `<wiki_dir>/log.md`. If `--generate-skill` is passed, render `assets/child-skills/ingest-domain.j2` into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`.
