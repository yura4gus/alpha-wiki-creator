# Architectural overlays

Overlays modify the macro-structure of `<wiki_dir>/` for the `software-project` preset.
They also add **dependency rules** that lint enforces (🟡 warnings).

## Available

- `none` (default) — flat preset layout, no dependency rules
- `clean.yaml` — Uncle Bob's Clean Architecture
- `hexagonal.yaml` — Ports & Adapters
- `ddd.yaml` — Domain-Driven Design (combinable: ddd+clean, ddd+hexagonal)
- `layered.yaml` — classic 3-tier

## Combinability

Only `ddd` is combinable. `clean+hexagonal` is forbidden (overlapping intent).
`bootstrap.py` validates this at config-resolution time.

## Schema

```yaml
name: <overlay-name>
description: <one-liner>
applies_to: [<preset>, ...]
combinable_with: [<overlay>, ...]    # optional
top_level_dirs: [<path>, ...]
dependency_rules:
  - {from: <pattern>, forbidden_to: [<pattern>, ...]}
  - {from: <pattern>, required_to: [<pattern>, ...]}
extra_cross_ref_rules: [...]
```
