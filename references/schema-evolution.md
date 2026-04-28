# Schema evolution

`/wiki:ingest` may encounter artifacts with no matching slot in the current schema.

## Modes

- **gated** (default): pause, propose options, require user confirmation
- **auto**: pick best default and proceed (append `[schema-change]` log entry, allow rollback)

## Options proposed (gated mode)

For an artifact of class `X` with no slot:

1. **New top-level entity type** — e.g. `data/migrations/`
2. **Sub-folder under existing layer** — e.g. `infrastructure/migrations/` (if hexagonal/clean)
3. **Section append in related page** — e.g. `## Migrations` on `entities/users.md`

User picks; `/wiki:evolve` runs.

## /wiki:evolve actions

```
1. Update CLAUDE.md
   - "Page Types" table: add row
   - "Frontmatter Templates": append YAML
   - "Cross-Reference Rules": add rules
2. Create assets/frontmatter/<type>.yaml in target
3. mkdir <wiki_dir>/<dir>/
4. Append <wiki_dir>/log.md:
   ## [YYYY-MM-DD] schema-change | added type: <type> (<path>) | trigger: <trigger>
5. git add . && git commit -m "[schema-change] add type: <type>"
6. graph/edges.jsonl: untouched (no edges yet)
```

## Project-local skill (optional)

`/wiki:evolve <type> --generate-skill` renders `assets/child-skills/ingest-domain.j2`
into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`. The child skill is a thin
wrapper that pre-classifies into this slot. It lives only in the target.
