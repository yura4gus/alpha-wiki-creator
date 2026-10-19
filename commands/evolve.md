---
description: "Add wiki type — evolve schema, directory, frontmatter, and rules"
argument-hint: "<type-name> [--generate-skill]"
---

Invoke the `evolve` skill from the `alpha-wiki` plugin. Human meaning: teach the wiki a new kind of page when existing types do not fit.

Arguments: $ARGUMENTS

Collect the type spec (name, dir, required/optional frontmatter, sections and
affected cross-reference rules). Show the config diff and obtain confirmation
unless the configured mode is auto. Call `scripts.add_entity_type.add_entity_type`
from the installed plugin environment: it adds the type to config, creates the
validated directory and journals the change. Apply other reviewed rules/moves
explicitly, then verify lint and graph. Never rewrite AGENTS.md or user Claude
instructions as a schema table. Commit only when requested. If
`--generate-skill` is passed, render `assets/child-skills/ingest-domain.j2`
into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`.
