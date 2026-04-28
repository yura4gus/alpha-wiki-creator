# Cross-reference rules

Bidirectional link enforcement is the heart of OmegaWiki-style wikis.
Every forward link must have a reverse — `tools/lint.py` checks this.

## Canonical rules per preset

Defined in YAML under `references/presets/<preset>.yaml` → `cross_ref_rules`.

## Overlay-specific rules

Defined in YAML under `references/overlays/<overlay>.yaml` → `extra_cross_ref_rules`.

## Enforcement

1. **Write time** (`pre-tool-use` hook): validates frontmatter; if forward link added, calls `tools/wiki_engine.py add-edge --bidirectional` to write reverse.
2. **Lint time** (`tools/lint.py --check missing-reverse`): scans whole wiki, reports/fixes missing reverses.
3. **Edge graph** (`wiki_engine.py rebuild-edges`): regenerates `graph/edges.jsonl` from frontmatter — never hand-authored.

## Stub creation

If a forward link points to a nonexistent page, `pre-tool-use` creates a stub:

```markdown
---
title: <inferred-from-link>
slug: <link-target>
status: stub
---
# <inferred-title>
TODO: fill via /wiki:ingest
```

And appends `log.md`:
```
## [date] stub | <slug> | created from forward link in <source-file>
```
