# Feature Contract Example

Purpose: show how Alpha-Wiki summarizes a feature without becoming a product-management system.

```yaml
title: Static HTML Wiki Export
slug: static-html-wiki-export
kind: feature-contract
status: shipped
owner: docs-runtime
belongs_to: "[[alpha-wiki-runtime]]"
implements:
  - "[[render-operation]]"
related_api_contracts: []
related_code_contracts:
  - "[[html-export-output-boundary]]"
source:
  - tools/render_html.py
  - tests/unit/test_graph_exports.py
date_updated: 2026-05-07
```

## Purpose

Produce a read-only HTML snapshot so a reviewer can browse the wiki without Obsidian.

## Expected Behavior

- `render html` writes `index.html`, per-page HTML files, `style.css`, `graph.mmd`, and `graph.dot`.
- Markdown remains the source of truth.
- Existing wikilinks become relative HTML links where the target page exists.

## Risks And Open Questions

- Risk: treating HTML as editable source instead of generated output.
- Open question: whether release snapshots should be tracked in git for every project or only generated on demand.

## Source Links

- `tools/render_html.py`
- `tests/unit/test_graph_exports.py`

