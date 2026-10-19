---
title: Alpha-Wiki Review Operation
slug: alpha-wiki-review-operation
kind: operation-spec
status: stable
date_updated: 2026-10-19
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-product-spec]]"
version: v1
evidence: commands/review.md, skills/review/SKILL.md, tools/review.py
source_files:
  - commands/review.md
  - skills/review/SKILL.md
  - tools/review.py
  - tools/status.py
  - tools/lint.py
  - tools/security.py
  - tools/wiki_engine.py
  - references/concept.md
---
# Alpha-Wiki Review Operation

## Provenance

- Sources: commands/review.md, skills/review/SKILL.md, tools/review.py.
- Shared health, structural, and security-memory checks: tools/status.py, tools/wiki_engine.py, tools/lint.py, tools/security.py.
- Authority and read-only limits: references/concept.md.
- Reviewed against local development sources on 2026-10-19; strict read-only mode is not in public 0.6.2.

## Entities

- Operation: `/alpha-wiki:review` / `$alpha-wiki:review`.
- Inputs: current pages, lint, status, typed ownership, scope manifest, security-memory references, provenance, dates, and questions.
- Output: wiki-quality readiness, structural errors/warnings, gaps, and bounded next maintenance actions.

## Requirements

- Review audits wiki memory quality, not AgentOps team process or actual production behavior.
- The backend checks structure, recorded scope/security memory, ownership, and provenance. Its status snapshot shows stale pages and open questions.
- Default execution refreshes generated graph artifacts before embedding health. `--read-only` computes current links/questions without target writes, even with missing or stale graph exports.
- Reject `--read-only --out`. Use a prepared runtime and suppress bytecode for strict zero-write audits; do not fix, refresh, or save during that request.
- Structural findings and wiki-quality readiness are not semantic contradiction resolution, API conformance, owner approval, or a universal package-release prohibition.
- Missing knowledge routes to [[alpha-wiki-ingest-operation]]; schema gaps route to evolve. A review alone does not authorize repairs.

## Gates

- Do not invent content, security facts, signatures, or approvals.
- Map each suggested action to a command or file and respect the requested report format.
- Save reports only when requested; automated reports remain suitable for existing CI issue bodies.
- Controller runs deterministic checks once; delegate only material independent read-only scopes with pinned inputs, then reconcile their evidence.
