---
title: Alpha-Wiki Product Spec
slug: alpha-wiki-product-spec
kind: product-spec
status: stable
date_updated: 2026-10-19
belongs_to: "[[alpha-wiki-runtime]]"
implements: "[[alpha-wiki-runtime]]"
version: v1
evidence: docs/01-alpha-wiki.md
---
# Alpha-Wiki Product Spec

## Provenance

- Source: docs/01-alpha-wiki.md.
- Closed-loop worker acceptance: owner clarification on 2026-10-19 and the
  maintained DOC-002.1 user stories in `docs/roadmap-execution.md`. Local
  Codex-controller Pilot A passed on 2026-10-19; see roadmap section 18 for
  evidence and limits. Live Claude Pilot C failed at provider access, and
  the maintenance extension is packaged by 0.7, not by 0.6.2. Actual
  publication/install receipts are maintained in roadmap section 20.

## Entities

- Runtime layers: `raw/`, wiki pages, graph artifacts, gated schema contract.
- User operations: 12 core workflows plus optional orchestrate, backlog, handoff, and release-check.
- Deterministic tools: wiki engine, lint, init audit, ingest pipeline, query/search, status/review/rollup, renderers, release audit, and contract/claim sanity checks.
- Presentation layer: Obsidian config plus Mermaid, DOT, and static HTML exports.

## Requirements

- Alpha-Wiki core is standalone; the optional [[agentops-control-layer]] is isolated under `wiki/agentops/`.
- Wiki pages use typed frontmatter, stable slugs, provenance, and wikilinks.
- `ingest`, `query`, and `lint` remain the core Karpathy operations.
- `init` must audit the existing source corpus before migration.
- Initialized projects run deterministic tools through `.alpha-wiki/run.py`,
  with dependencies isolated in `.alpha-wiki/runtime/.venv`. Bootstrap and
  upgrade must not add Alpha-Wiki requirements to product manifests or install
  them in the product virtualenv.
- Graph artifacts are generated from markdown; users should not hand-edit `graph/*`.
- Colors label node roles, while typed links form clusters.
- Product specifications, contracts, decisions, and standards form a small canonical set that is maintained in place.
- Every canonical document edit must have a matching `wiki/log.md` record, and every document-change record must correspond to a real edit.
- New canonical documents require explicit ingest or registration because research notes and temporary analysis do not become standards by location or filename alone.
- `tools.document_worker` enforces document/log pairing at pre-commit and CI boundaries without becoming an autonomous author.
- The 0.7 maintenance extension plans changed source bindings and applies
  bounded, reviewed replacements to existing documents. It preserves identity,
  ownership, status, and provenance metadata; it does not ratify decisions.
- Explicit compaction preserves normative sections and references. Source
  evidence, working candidates, canonical documents, and generated views retain
  distinct roles rather than becoming duplicate standards.
- Successful application journals actual edits once and refreshes graph,
  context, and questions. Checkpoints follow successful refresh; interrupted
  transactions remain pending and unchanged reruns produce no journal noise.
- Maintenance uses local files and the existing isolated runtime. Installing a
  plugin does not start a background author. No server, Temporal, or model SDK
  is required; semantic edits remain the executing agent's responsibility.
- Claude and Codex skills share result-first communication, targeted retrieval,
  exact diagnostics, and checks proportional to the requested acceptance.
- Release decisions use existing project requirements. Blockers cite a concrete
  failure and its affected required step; optional Pages, wiki, or platform
  findings retain their own scope.
- Requirements, accepted contracts, code snapshots, test/review evidence, builds,
  deployment state, and production business acceptance retain separate owners.
  Wiki points to those sources and reconciles drift; it cannot override them.
- Task execution status and verified delivery level are separate. Use the
  shared L1-L6 contract in `references/concept.md`; local-only work has local
  acceptance, while production scope requires actual business-journey evidence.
- Discover interfaces by actual type, not YAML extension. Reuse accepted
  OpenAPI/event/data/configuration/GitOps sources and validators. Structural
  wiki contract checks do not prove API compatibility or live conformance.
- Claude and Codex share the same task/evidence contract. Provider role splits
  and parallel agents are optional. Independent reviews bind to exact source
  snapshots; changed inputs require renewed applicable verification.
- Skills do not invent signing, secrets, owner votes, or approval chains.
  Existing required signing, authentication, tests, and security boundaries
  remain applicable. See `references/concept.md` for the shared rules.

## Closed-Loop Worker Outcome

Local DOC-002.1 acceptance is verified for the three-page Pilot A, with one
Codex controller and separate fresh/brownfield adapter subprocess checks.
This is not whole-corpus freshness, live Claude acceptance, or a claim that
any existing installation was automatically upgraded, or that deterministic
`apply` alone provides the complete loop.

- A worker closes a bounded user request, not merely an edit or a tool call.
  One existing Claude/Codex workflow receives the outcome, scope, permissions,
  and acceptance; it coordinates the necessary source review, edits, memory
  maintenance, checks, and final result without normal tool-by-tool operator
  intervention.
- Authorized canonical-source edits precede re-planned dependent wiki updates.
  Source evidence stays immutable. If source editing succeeds but wiki or
  validation fails, the overall request is still unfinished and resumable.
- Completion requires the requested result, attributable provenance, valid
  ownership/cross-links, meaningful project-journal records for actual edits,
  current applicable graph/context/questions, and passing in-scope checks.
  Retrieval must expose the updated facts with citations. Unrelated gaps stay
  visible without being silently promoted into task blockers.
- A batch checkpoint proves only that batch. The controller closes the owning
  task after the remaining job-level acceptance passes, recording concise
  evidence through the existing backlog/journal/state. Do not create a second
  task tracker or a report per tool invocation.
- A checked no-change result is valid and creates no document-change journal
  entry. Strict read-only requests perform no repository writes or graph refresh.
  CHANGELOG.md records package/release behavior when relevant; wiki/log.md
  records maintained-document changes. Neither is a technical heartbeat stream.
- Deterministic control means pinned inputs, explicit scope, repeat-safe effects,
  recoverable progress, and reproducible acceptance checks. Semantic LLM edits
  still require source review; exact wording is not guaranteed deterministic.
- Read-only status/review can compute current edges and questions in memory
  without refreshing generated files. Zero-write audits additionally require
  a prepared runtime and bytecode suppression; cold setup is a separate write.
- Request-driven source maintenance is not continuous session discovery.
  Missed-event catch-up and an idle zero-model runner remain scoped follow-on
  work, not a capability inferred from hooks or an installed plugin.
- Retrying a completed job must not duplicate pages or journal entries. A retry
  after interruption preserves actual progress, refuses observed concurrent
  edits, and does not claim completion until the remaining acceptance passes.
- Commit, push, publication, and deployment are part of completion only when
  included in the authorized user outcome. No server, Temporal, scheduler,
  extra model SDK, or mandatory multi-agent wave is required for this target.

The canonical user stories, pilot scopes, outcome definitions, and Definition
of Done are maintained once in `docs/roadmap-execution.md`, section 17.

## Next Delivery Acceptance

The next task specifications are maintained in roadmap section 19, not separate
documents per worker or session. They preserve the following product boundaries:

- A release candidate must include the complete functional dependency slice;
  excluding pending schema/AgentOps work must not silently break maintenance.
- Source-bound maintenance closes the selected user outcome and reports its
  remaining unchecked coverage; it does not manufacture whole-wiki freshness.
- Agent scenario checks distinguish static/fixture verification from actual
  provider execution. A configured provider failure retains its own scope.
- Interface and CI evidence identify the real owning repository and revision.
  HTTP conformance requires an actual service; a CLI-only project needs no
  invented HTTP server, OpenAPI document, or GitLab mirror.
- A published package is accepted through its tested artifact and real install
  paths. Production-service acceptance applies only to service delivery scope.
- Optional catch-up starts as an explicit bounded local operation over known
  sources. It does not authorize a daemon, implicit transcript ingestion, or
  background model calls. Its detailed acceptance remains a P2 candidate.

## Operation Pages

- [[alpha-wiki-init-operation]]
- [[alpha-wiki-ingest-operation]]
- [[alpha-wiki-query-operation]]
- [[alpha-wiki-lint-operation]]
- [[alpha-wiki-status-operation]]
- [[alpha-wiki-review-operation]]

## Links

- Runtime module: [[alpha-wiki-runtime]]
- Canonical roadmap and backlog: `docs/roadmap-execution.md`
- Source migration: [[source-corpus-inventory]]
- No embeddings decision: [[no-embeddings-mvp]]
- Graph semantics decision: [[graph-cluster-semantics]]
