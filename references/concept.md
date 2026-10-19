# Concept

## Karpathy LLM Wiki (origin)

Three layers, three operations, two service files.

- **Raw** — immutable sources (read-only after capture)
- **Wiki** — LLM-generated markdown with cross-links
- **Schema** — `.alpha-wiki/config.yaml`; existing generated `CLAUDE.md` and
  `AGENTS.md` expose the shared operating contract. 0.7 does not migrate or
  remove user project instructions.

Operations: `ingest`, `query`, `lint`. Service files: `index.md`, `log.md`.

Karpathy's claim: index.md is sufficient up to ~100 sources. RAG/embeddings are not needed
at small/medium scale and obscure understanding.

## OmegaWiki (production extensions)

Same three layers, but with:
- Typed entities (papers, claims, experiments, ...) with required frontmatter and sections
- Typed edge graph (`graph/edges.jsonl`) — `extends`, `contradicts`, `supports`, etc.
- Bidirectional link enforcement (forward write triggers reverse write)
- Auto-generated `graph/context_brief.md` (≤8000 chars compressed context)
- Lint with `--fix` / `--suggest` / `--dry-run`
- GitHub Actions cron (daily-arxiv equivalent in our case: weekly review)

## Alpha-wiki additions

- **Three-layer model = mutability contracts**, not folders
- **Domain presets** (software-project default + 4 alternatives + custom)
- **Architectural overlays** (clean, hexagonal, ddd, layered)
- **Schema evolution** through ingest (new artifact type → config migration)
- **Session-end automation** (lint and document checks; no technical heartbeat log)
- **Sibling skill `wiki:spawn-agent`** for adding subagents

The historical design spec lives at `docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`.

## Execution Discipline

These rules apply to Claude and Codex. The requested deliverable and existing
project instructions determine the scope.

- Answer with the result, decisive evidence, and any required next action in
  the user's language. Follow an explicit output format. Avoid routine narration
  and repeated reports; keep persisted contracts readable and complete.
- Read the brief for orientation, then search and open relevant source sections.
  Read enough to resolve the question; there is no minimum page or agent count.
  Wiki summaries guide retrieval, while current sources establish the facts.
- Preserve exact commands, paths, numbers, units, exit codes, negation, failures,
  skipped checks, and uncertainty when summarizing output. Keep a path to the
  full diagnostic and reopen it when the summary is insufficient.
- Choose checks from the changed behavior and affected shared paths. Reuse
  results only when the relevant code, inputs, and environment still match.
  Broaden checks after relevant changes, failures, or unresolved concerns.
- Stop once the requested acceptance is proven. Suggested polish, another
  review, optional configuration, and new infrastructure need a demonstrated
  connection to that acceptance before they enter the current task.
- Continue authorized work without repeated confirmation. Ask only for a
  missing decision that changes scope or authority. Use subagents only when
  independent material work benefits from them; one helper is valid.

## Project Tool Runtime

After init, run copied tools with `python3 .alpha-wiki/run.py -m tools.<module>`
from the target project. The launcher resolves the project from its own path,
prepares dependencies in `.alpha-wiki/runtime/.venv` with `uv` on first use,
and executes the project's `tools/`, not tools from another plugin version.
It does not install into the product virtualenv or change product dependency
files. A prepared runtime can work without `uv`. Before init, use the installed
plugin environment for bootstrap and initial source discovery.

## Release Decisions

Use these rules only when judging or executing a release-related step:

1. Identify the target: Alpha-Wiki package publication, target-project delivery,
   wiki quality, or docs deployment. Each report applies to its own target.
2. Derive mandatory steps from the user request, existing repository policy,
   branch protection, or actual tool requirements. Keep applicable tests,
   authentication, and established security constraints.
3. A blocker needs the requirement source, concrete failure, affected required
   step, and smallest corrective action. A required check that has not run is
   unverified; a check returning a failure is failed. Label access-blocked only
   when an actual access denial prevents a required step.
4. Do not invent signing keys, certificates, tokens, secrets, owner votes, or
   approval chains. Reuse existing publishing configuration and authentication.
   For a real denial, give its exact error and next action without printing
   credentials. Apply signing when an existing rule or explicit task requires it.
5. Missing optional hooks, an unused platform, cosmetic warnings, or failed
   Pages deployment do not automatically block package publication. A Pages
   failure blocks docs deployment; extend that effect only through an existing
   release requirement. A wiki review verdict is a wiki-quality verdict.
6. Preserve backend findings verbatim and explain their scope. Do not convert
   a deterministic BLOCKED report into GREEN, or interpret an unrelated report
   as a global release prohibition. Resolve applicability against the sources.
7. Use the existing release path. For Alpha-Wiki package changes, check version
   alignment, affected tests, executable smoke, package audit, and published
   installation as applicable to the requested stage. Do not add a new gate,
   service, config family, signature, or report merely to complete this list.

Examples: an unsigned tag is acceptable when signing is not required; a failed
required runtime test prevents that release; a rejected push prevents publishing
but allows independent local verification; a missing signing key matters only
when signing is required. Stop after the applicable checks pass.

## Delivery Evidence And Contract Ownership

For implementation, integration, and release tasks, identify the requested user
outcome and final environment before choosing checks. Keep the existing task
status separate from the demonstrated delivery level:

| Level | Evidence required within the task scope |
|---|---|
| L1 SPEC_READY | Applicable requirement and interface behavior accepted. |
| L2 CODE_VERIFIED | Attributable implementation and applicable local checks pass. |
| L3 INTEGRATION_VERIFIED | Actual required consumers/integrations pass against the implementation. |
| L4 MERGED_BUILD | Accepted revision merged; identified build artifact exists. |
| L5 DEPLOYED_VERIFIED | That build runs in the named environment; required runtime probes pass. |
| L6 PROD_ACCEPTED | Required production business journey passes with attributable evidence. |

Record the highest level actually proved, plus missing or non-applicable
transitions. A local document job does not require deployment. Unit tests do
not prove a running API, and `/health` returning 200 does not prove a business
journey. The Alpha-Wiki package audit, wiki review, and an observed application's
delivery readiness remain different results.

Use the existing task/journal/handoff for concise evidence, not another tracker.
Include owning repository, exact SHA and dirty-worktree digest when relevant,
contract or generator path/revision, affected consumers, previous accepted
revision, commands and results, observation time, and unresolved gaps. Add
artifact identity, environment, runtime observations, and rollback references
only when those stages apply. Never promote untracked candidates or a passing
test to owner acceptance, merge permission, or production authorization.

Classify a source by behavior, not its `.yaml` extension: OpenAPI for HTTP;
JSON Schema for data; AsyncAPI/events, GraphQL or Protobuf for their interfaces;
application configuration and Helm/GitOps for configuration/deployment. The
owning repository's accepted specification or generation source stays
authoritative. Keep its supported version; no automatic format migration.

For an affected interface, trace the user story, source owner, consumers,
previous accepted contract, compatibility changes, implementation, and actual
integration tests. Inspect existing validators first. A format check alone
does not prove compatibility or runtime conformance. `tools.contracts_check`
checks wiki metadata/links, not OpenAPI compatibility or live API behavior.
`oasdiff` and Schemathesis are optional tools for a demonstrated HTTP need, not
new Alpha-Wiki dependencies. Do not invent a service to make an HTTP pilot pass
when the selected project exposes only CLI or file interfaces.

Claude and Codex use this same contract. Either can implement or review; no
mandatory provider split or agent count applies. For a requested cross-agent
cycle, one writer implements against pinned inputs, an independent reviewer
reviews that snapshot, the writer resolves actionable findings, and the
controller verifies the final snapshot. Changed code invalidates stale approval.
Handoffs carry scope, contracts, diff, checks, findings, and next action, not raw
transcripts. Fixture execution is not a live-provider session.

An unchecked requirement is UNVERIFIED, a tested failure is FAILED, a pending
external operation is WAITING, and an out-of-scope stage is NOT_APPLICABLE.
BLOCKED requires an applicable mandatory gate, concrete failure or unavailable
authorized action, evidence, affected outcome, responsible owner, minimum fix,
and clearing condition. Continue independent work. These evidence labels do not
change existing task-status enums.

## Strict Read-Only Operations

For an explicit no-write audit, use `tools.status --read-only` and
`tools.review --read-only`. They derive edges/questions from current Markdown
without updating exports or saving reports. Query already reads without writes.
Do not run refresh, fix, render, journal, or worker apply during that request.

The Python runtime can also write bytecode or install itself on first use.
Use a prepared Alpha-Wiki environment with `PYTHONDONTWRITEBYTECODE=1` (or
Python `-B`). If the target runtime is cold, use a prepared external environment
for its tools rather than installing into the target during a no-write audit.
Report the runtime used and any check that could not be run read-only.
