# Cross-reference rules

Bidirectional link enforcement is the heart of OmegaWiki-style wikis.
Every forward link must have a reverse — `tools/lint.py` checks this.

## Canonical rules per preset

Defined in YAML under `references/presets/<preset>.yaml` → `cross_ref_rules`.

<a id="folder-navigation-unreleased-gph-0011"></a>

## Folder Navigation (0.8.0 GPH-001.1)

A folder may use `_index.md` as a maintained catalog. Give it a nonempty
`title` and a wiki-wide unique `slug`, such as `contracts-index`.
It remains a scanned page, link target, searchable source and HTML/graph node.
It is not a domain entity merely because it lives under `contracts/` or
`services/`: entity-required fields and mandatory cluster-owner links do
not apply to the catalog. Neighboring entity pages retain all existing checks.

Broken links, duplicate slugs, orphans, dependency rules and explicit typed-link
reverse checks still apply. Link the catalog from the root index or another
maintained page. Do not rename a real entity to `_index.md` to suppress findings.
Use `index.md` only for the existing system indexes excluded from entity scans.

Both `[[contracts-index]]` and vault-relative
`[[contracts/_index|Contract Catalog]]` resolve to that catalog in the tools.
The path form is portable to Obsidian; multiple folders may each have an
`_index.md`, so use qualified paths, not ambiguous bare `[[_index]]`.
An optional `.md` suffix is supported for these catalog paths. Lint, typed
edges and HTML resolve the path to the catalog's stable slug. This is not a
general resolver for arbitrary relative paths, heading fragments or embeds.
See [Obsidian alias links](https://obsidian.md/help/aliases) for its native
target/display-text form.

Catalog body wikilinks support browsing and link validation; exported typed
edges still come from frontmatter. Optional typed links on a catalog are kept,
not interpreted as evidence that an API contract or mixed-role service cluster
exists. Status excludes catalogs from those coverage/cluster metrics while
keeping them in page counts. Colors continue to follow the directory palette,
including in Obsidian; they do not impose entity fields on a catalog.

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
TODO: fill via /alpha-wiki:ingest
```

And appends `log.md`:
```
## [date] stub | <slug> | created from forward link in <source-file>
```
