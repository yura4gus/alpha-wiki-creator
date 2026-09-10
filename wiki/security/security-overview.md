---
title: Security Overview
slug: security-overview
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: README.md, pyproject.toml, references/hooks-design.md
---

# Security Overview

Alpha-Wiki is a local, repo-native documentation tool. It reads and writes files
with the permissions of the current operator or agent and has no hosted runtime,
account database, or secret store.

Primary risks are executing unreviewed project hooks and ingesting sensitive
source material into tracked markdown. Operators must review hooks and source
scope before enabling automation.

Related: [[alpha-wiki-runtime]], [[codex-skill-adapter-contract]].
