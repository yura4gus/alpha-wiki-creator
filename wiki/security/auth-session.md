---
title: Auth and Session Model
slug: auth-session
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: pyproject.toml, scripts/install_codex.py, references/hooks-design.md
---

# Auth and Session Model

Alpha-Wiki does not issue tokens, authenticate users, or create application
sessions. Claude Code, Codex, GitHub, and the local operating system own their
authentication and session lifecycles. Alpha-Wiki tools receive only local file
paths and command inputs.

Related: [[alpha-wiki-runtime]], [[codex-skill-adapter-contract]].
