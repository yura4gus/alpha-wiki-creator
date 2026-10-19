# Schema evolution

`/alpha-wiki:ingest` may encounter artifacts with no matching slot in the current schema.

## Modes

- **gated** (default): pause, propose options, require user confirmation
- **auto**: pick best default and proceed (append `[schema-change]` log entry, allow rollback)

Read `schema_evolve_mode` from config; missing values mean `gated`.
Fresh init persists the chosen mode there. Existing config is preserved:
merge an intended legacy auto mode explicitly, rather than assuming permission
from an old instruction table.

## Options proposed (gated mode)

For an artifact of class `X` with no slot:

1. **New top-level entity type** — e.g. `data/migrations/`
2. **Sub-folder under existing layer** — e.g. `infrastructure/migrations/` (if hexagonal/clean)
3. **Section append in related page** — e.g. `## Migrations` on `entities/users.md`

User picks; `/alpha-wiki:evolve` runs.

## /alpha-wiki:evolve actions

```
1. Update `.alpha-wiki/config.yaml`
   - `entity_types`: add the new type and frontmatter/section rules
   - `cross_ref_rules`: add any new forward/reverse rules
2. Create <wiki_dir>/<dir>/ after validating paths, type shape and duplicates
3. Append <wiki_dir>/log.md:
   ## [YYYY-MM-DD] schema-change | added type: <type> (<path>) | trigger: <trigger>
4. Keep AGENTS.md, Claude adapters and user instructions unchanged
5. Verify lint, affected links and graph after the complete migration
6. Commit only if the user requested it; do not stage unrelated work
```

The deterministic add_entity_type helper owns the config/type/directory/log
addition only. Other cross-reference rules, page moves or templates are explicit
reviewed migration steps, not hidden helper side effects. It reads an explicit
wiki_dir from config; legacy AGENTS/CLAUDE wiki-path metadata remains a read-only
fallback when that field is absent. Other config fields are preserved semantically.

The helper rejects escaping/symlink/generated directories and duplicate types
before writes. It uses atomic file replacement and rolls back ordinary write
failures, without deleting concurrent user files. It does not promise atomicity
across process termination; inspect the actual config/directory/log before retry
after a killed process. No server, schema database or automatic owner approval
is introduced.

## Project-local skill (optional)

`/alpha-wiki:evolve <type> --generate-skill` renders `assets/child-skills/ingest-domain.j2`
into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`. The child skill is a thin
wrapper that pre-classifies into this slot. It lives only in the target.
