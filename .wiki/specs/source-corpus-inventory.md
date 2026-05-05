---
title: Source Corpus Inventory
slug: source-corpus-inventory
kind: source-inventory
status: building
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: raw/docs/source-manifest-2026-05-05.md
---
# Source Corpus Inventory

## Provenance

- Source: raw/docs/source-manifest-2026-05-05.md.

## Entities

- Root project docs.
- Architecture and release docs.
- ADRs.
- Commands.
- Skills.
- References.
- Superpowers archive.

## Requirements

- Run `tools/init_audit.py` during init or before any large migration.
- Raw sources remain immutable evidence.
- Existing live repo contracts can be represented by a raw manifest instead of duplicated blindly.
- Curated `.wiki/**` pages summarize source sets with frontmatter, typed links, and provenance.
- Each future ingest batch should update this inventory or create a more specific spec/decision/module page.

## Current Coverage

Already represented in `.wiki`:

- [[alpha-wiki-runtime]]
- [[codex-adapter-runtime]]
- [[release-readiness-runtime]]
- [[no-embeddings-mvp]]
- [[graph-cluster-semantics]]
- [[codex-skill-adapter-contract]]

Not yet fully represented as individual wiki pages:

- Architecture docs.
- ADRs 001, 002, 004, 005, 006.
- Command manuals.
- Skill manuals.
- Reference docs.
- Superpowers archive.
