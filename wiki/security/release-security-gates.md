---
title: Release Security Gates
slug: release-security-gates
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: tools/release_audit.py, tools/release_smoke.py, .github/workflows/plugin-ci.yml
---

# Release Security Gates

Before publishing Alpha-Wiki, validate a clean diff, scan changed files for
committed credentials, run the full test suite, run release smoke and release
audit, validate plugin metadata, and verify a clean public clone. Hooks and
installer changes require explicit review because they execute with user
permissions.

Related: [[release-readiness-runtime]], [[alpha-wiki-runtime]].
