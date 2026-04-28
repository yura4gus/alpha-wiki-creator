---
name: evolve
description: Use when the user (or `/alpha-wiki:ingest`) needs to add a new entity type to the wiki schema. Triggers include "add type X to the wiki", "the wiki needs a new category for Y", or auto-invocation when ingest finds a no-match artifact. Pass `--generate-skill` to also produce a project-local skill that pre-classifies into the new slot.
---

# wiki:evolve — add an entity type

## Process

1. Collect type spec interactively (or from `/alpha-wiki:ingest` schema-evolve flow):
   - `name` (slug-friendly, lowercase, hyphenated)
   - `dir` (relative to wiki/, may include subdirs)
   - `frontmatter_required` (list)
   - `frontmatter_optional` (list)
   - `sections_required` (list)
   - Cross-reference rules (forward → reverse pairs, optional)

2. Show the proposed CLAUDE.md diff to the user. Confirm before writing.

3. Run: `uv run python -m scripts.add_entity_type` (calls `add_entity_type(target, spec, trigger)`).

4. Append `assets/frontmatter/<name>.yaml` to the target (so future ingests can use it).

5. Commit:
   ```bash
   git add CLAUDE.md wiki/ assets/frontmatter/
   git commit -m "[schema-change] add type: <name>"
   ```

6. If `--generate-skill <trigger-phrase>`: render `assets/child-skills/ingest-domain.j2` into `target/.claude/skills/wiki-ingest-<name>/SKILL.md`. (This child skill remains prefixed for domain clarity.)

## Modes

- **gated** (default): require explicit confirmation
- **auto**: log and proceed; user can `git revert` if unhappy

## References

- `references/schema-evolution.md`
