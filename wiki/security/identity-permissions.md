---
title: Identity and Permissions
slug: identity-permissions
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: AGENTS.md, CLAUDE.md, references/hooks-design.md
---

# Identity and Permissions

Alpha-Wiki has no RBAC layer. Every tool and hook inherits filesystem, Git, and
network permissions from the invoking user or agent runtime. The project
contracts in `AGENTS.md` and `CLAUDE.md` limit mutation, but operating-system and
repository permissions remain the enforcement boundary.

Related: [[alpha-wiki-runtime]], [[codex-skill-adapter-contract]].
