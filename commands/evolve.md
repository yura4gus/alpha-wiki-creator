---
description: "Add wiki type — evolve schema, directory, frontmatter, and rules"
argument-hint: "<type-name> [--generate-skill]"
---

Invoke the `evolve` skill from the `alpha-wiki` plugin. Human meaning: teach the wiki a new kind of page when existing types do not fit.

Arguments: $ARGUMENTS

Collect the type spec interactively (name, dir, required/optional frontmatter, sections, cross-ref rules). Show the proposed CLAUDE.md diff and confirm before writing. Run `scripts/add_entity_type.py`. Commit with `[schema-change]` tag and append to `<wiki_dir>/log.md`. If `--generate-skill` is passed, render `assets/child-skills/ingest-domain.j2` into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`.
