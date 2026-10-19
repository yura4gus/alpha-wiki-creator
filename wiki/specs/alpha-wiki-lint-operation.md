---
title: Alpha-Wiki Lint Operation
slug: alpha-wiki-lint-operation
kind: operation-spec
status: stable
date_updated: 2026-10-20
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/lint.md, skills/lint/SKILL.md, tools/lint.py
source_files:
  - commands/lint.md
  - skills/lint/SKILL.md
  - tools/lint.py
  - tools/wiki_engine.py
  - references/cross-reference-rules.md
---
# Alpha-Wiki Lint Operation

## Provenance

- Source: commands/lint.md.
- Source: skills/lint/SKILL.md.
- Tool sources: tools/lint.py, tools/wiki_engine.py.
- Navigation contract: references/cross-reference-rules.md.
- GPH-001.1/2 behavior is packaged in 0.8.0; existing user schemas and Obsidian settings remain protected.

## Entities

- Operation: `/alpha-wiki:lint` / `$alpha-wiki:lint`.
- Modes: `--dry-run`, `--suggest`, `--fix`, CI/pre-commit.
- Checks: broken links, missing frontmatter, duplicate slugs, missing reverse links, orphan pages, cluster gaps, dependency-rule violations.

## Requirements

- Lint protects graph integrity, not semantic truth.
- Errors block CI or commit; warnings require review or explanation.
- `--fix` may only apply deterministic safe repairs.
- Graph artifacts are rebuilt after fixes.
- Graph color issues should be diagnosed as type/path or typed-link problems, not visual-only problems.
- Security-memory pages are evidence documents and use the black document role from 0.8.0 (GPH-001.2). Existing ownership links remain required; rendering does not authorize rewriting facts or inventing services.
- Folder `_index.md` catalogs require explicit nonempty title and unique slug, not enclosing entity fields or mandatory ownership links. They stay in scanning, search and exports.
- Broken-link, duplicate-slug, orphan, dependency and typed-reverse checks still apply to catalogs. Neighboring entities retain their complete schema.
- Catalog body links support browsing; exported edges remain frontmatter-derived. Catalogs inherit the directory palette, not a new per-page color scheme.
- Vault-relative catalog paths such as `contracts/_index` with an optional display label resolve to the unique catalog slug in lint, typed edges and HTML. An optional `.md` suffix is supported. Do not collapse multiple catalogs to a bare `_index` target or infer general relative-path/heading support.

## Gates

- Do not create semantic content automatically.
- Do not delete pages.
- Do not silently change status values.
- Users receive concrete next actions after findings.

