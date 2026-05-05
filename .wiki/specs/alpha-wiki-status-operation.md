---
title: Alpha-Wiki Status Operation
slug: alpha-wiki-status-operation
kind: operation-spec
status: stable
date_updated: 2026-05-05
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/status.md, skills/status/SKILL.md, tools/status.py
---
# Alpha-Wiki Status Operation

## Provenance

- Source: commands/status.md.
- Source: skills/status/SKILL.md.
- Tool source: tools/status.py.

## Entities

- Operation: `/alpha-wiki:status` / `$alpha-wiki-status`.
- Report sections: Status Summary, Gap Check, Cluster Health, Provenance, Freshness, Open Question Follow-Up, Recent Activity, Suggested Next Actions.
- Read model: log, graph artifacts, pages, lint summary.

## Requirements

- Status is read-only for source pages.
- It may refresh generated graph artifacts before reporting.
- The Gap Check is mandatory and cross-cutting.
- The report must show pages, edges, open questions, log entries, provenance score, stale pages, missing metadata, and next actions.
- Thin wiki, noisy wiki, stale wiki, and graph gaps should be named plainly.

## Gates

- Source pages are not edited unless the user explicitly asks to save a report.
- Suggested actions must map to Alpha-Wiki commands.
- Status should prepare the user for [[alpha-wiki-review-operation]] when trust is in question.

