---
title: API Trust Boundaries
slug: api-boundaries
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: pyproject.toml, scripts/install_codex.py, .codex-plugin/plugin.json
---

# API Trust Boundaries

The deterministic Alpha-Wiki runtime has no application network API. Public
GitHub, Claude Code, Codex, npm, and `uv` operations are initiated explicitly by
the operator and remain outside Alpha-Wiki's data model. Generated hooks invoke
local project tools and must be reviewed before trust is granted.

Related: [[alpha-wiki-runtime]], [[codex-skill-adapter-contract]].
