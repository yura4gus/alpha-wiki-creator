---
title: Alpha-Wiki Lint Operation
slug: alpha-wiki-lint-operation
kind: operation-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/lint.md, skills/lint/SKILL.md, tools/lint.py
---
# Alpha-Wiki Lint Operation

## Provenance

- Source: commands/lint.md.
- Source: skills/lint/SKILL.md.
- Tool source: tools/lint.py.

## Entities

- Operation: `/alpha-wiki:lint` / `$alpha-wiki-lint`.
- Modes: `--dry-run`, `--suggest`, `--fix`, CI/pre-commit.
- Checks: broken links, missing frontmatter, duplicate slugs, missing reverse links, orphan pages, cluster gaps, dependency-rule violations.

## Requirements

- Lint protects graph integrity, not semantic truth.
- Errors block CI or commit; warnings require review or explanation.
- `--fix` may only apply deterministic safe repairs.
- Graph artifacts are rebuilt after fixes.
- Graph color issues should be diagnosed as type/path or typed-link problems, not visual-only problems.

## Gates

- Do not create semantic content automatically.
- Do not delete pages.
- Do not silently change status values.
- Users receive concrete next actions after findings.

