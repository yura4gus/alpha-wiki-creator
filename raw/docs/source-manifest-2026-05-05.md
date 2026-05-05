# Source Manifest — 2026-05-05

Immutable source inventory for the current Alpha-Wiki creator repository.

This file is raw evidence. Do not rewrite it as a curated wiki page. Distill it into `.wiki/**` pages through Alpha-Wiki ingest/review work.

Init audit rule: future bootstrap/migration runs should produce this kind of source corpus view with `tools/init_audit.py`, then process sources in batches instead of silently treating every existing document as already ingested.

## Root Sources

- `README.md`
- `CHANGELOG.md`
- `CLAUDE.md`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `pyproject.toml`

## Architecture And Release Docs

- `docs/00-architecture.md`
- `docs/01-alpha-wiki.md`
- `docs/02-agentops.md`
- `docs/03-superpowers-adapter.md`
- `docs/04-state-backend-contract.md`
- `docs/README.md`
- `docs/_references.md`
- `docs/alpha-wiki-lifecycle-automation-audit-2026-05-01.md`
- `docs/audit-verified-inventory.md`
- `docs/best-practices-gap-analysis-2026-04-30.md`
- `docs/codex-adapter.md`
- `docs/final-release-hardening-plan.md`
- `docs/final-release-readiness-audit-2026-05-04.md`
- `docs/implementation-plan-2026-04-30.md`
- `docs/karpathy-llm-wiki-compliance-audit-2026-05-01.md`
- `docs/platform-compatibility-matrix.md`
- `docs/quickstart.md`
- `docs/release-smoke-2026-05-05.md`
- `docs/roadmap-execution.md`

## ADRs

- `docs/ADR-001-alpha-wiki-agentops-boundary.md`
- `docs/ADR-002-superpowers-adapter-not-fork.md`
- `docs/ADR-003-no-embeddings-mvp.md`
- `docs/ADR-004-state-backend-abstraction.md`
- `docs/ADR-005-marketplace-topology-deferred.md`
- `docs/ADR-006-spawn-agent-boundary.md`

## Commands

- `commands/doctor.md`
- `commands/evolve.md`
- `commands/ingest.md`
- `commands/init.md`
- `commands/lint.md`
- `commands/query.md`
- `commands/render.md`
- `commands/review.md`
- `commands/rollup.md`
- `commands/spawn-agent.md`
- `commands/status.md`

## Skills

- `skills/doctor/SKILL.md`
- `skills/evolve/SKILL.md`
- `skills/ingest/SKILL.md`
- `skills/init/SKILL.md`
- `skills/lint/SKILL.md`
- `skills/query/SKILL.md`
- `skills/render/SKILL.md`
- `skills/review/SKILL.md`
- `skills/rollup/SKILL.md`
- `skills/spawn-agent/SKILL.md`
- `skills/status/SKILL.md`

## References

- `references/classifier.md`
- `references/concept.md`
- `references/cross-reference-rules.md`
- `references/examples/karpathy-original.md`
- `references/examples/omegawiki-walkthrough.md`
- `references/hooks-design.md`
- `references/overlays/README.md`
- `references/presets/README.md`
- `references/schema-evolution.md`

## Superpowers Archive

- `docs/superpowers/plans/2026-04-28-wiki-creator-implementation.md`
- `docs/superpowers/specs/2026-04-28-predecessor-design-ru.md`
- `docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`

## Distillation Status

- Distilled into `.wiki`: core runtime, Codex adapter, release readiness, no-embeddings decision, graph-cluster decision, Codex adapter contract.
- Not yet fully distilled into `.wiki`: all individual architecture docs, ADRs, commands, skills, references, and Superpowers archive documents.
