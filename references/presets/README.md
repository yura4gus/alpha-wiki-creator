# Presets

Each preset is a YAML file declaring entity types, their required frontmatter and sections,
and cross-reference rules. `bootstrap.py` reads the chosen preset, merges it with an overlay
(if any), and renders templates.

## Available presets

- `software-project.yaml` — default for engineering projects (8 entity types)
- `research.yaml` — OmegaWiki-aligned (9 entity types)
- `product.yaml` — product management
- `personal.yaml` — PARA + Zettelkasten
- `knowledge-base.yaml` — minimal universal (5 entity types)

## Custom

Preset = "custom" triggers interactive entity-type interview in `scripts/interview.py`,
producing an in-memory preset that gets persisted as `target/.alpha-wiki/preset.yaml`.

## Schema

```yaml
name: <preset-name>
description: <one-liner>
entity_types:
  - name: <type>
    dir: <dir-relative-to-wiki>
    frontmatter_required: [<field>, ...]
    frontmatter_optional: [<field>, ...]
    sections_required: [<heading>, ...]
cross_ref_rules:
  - forward: "<source-pattern>"
    reverse: "<reverse-action>"
```
