---
title: Secrets and Environment
slug: secrets-env
kind: security
status: stable
date_updated: 2026-09-10
belongs_to: "[[alpha-wiki-runtime]]"
evidence: scripts/install_codex.py, tools/doctor.py, .github/workflows/plugin-ci.yml
---

# Secrets and Environment

Core Alpha-Wiki tools require no API keys or hosted credentials. Environment
variables configure local runtime and install paths only. Source files may still
contain secrets, so sensitive material must be excluded before copying or
ingesting it into `raw/` or `wiki/`.

Related: [[alpha-wiki-runtime]], [[codex-skill-adapter-contract]].
