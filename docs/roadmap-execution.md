# Alpha-Wiki Product Roadmap And Backlog

Status: canonical development roadmap

Updated: 2026-10-19

Alpha-Wiki is repo-native Markdown memory for AI agents and teams. This file is
the single maintained roadmap and backlog for the Alpha-Wiki product. Dated
plans, audits, case logs, and research notes are evidence for this roadmap, not
competing execution plans.

## 1. Product Boundary

Alpha-Wiki core remains deliberately small:

```text
repository sources
-> maintained Markdown memory
-> deterministic lifecycle tools
-> agent-readable context
-> human-readable docs and lightweight graph
```

Core scope:

- install, init, doctor, ingest, query, lint, status, review, rollup, and render;
- product, architecture, feature, API, code, integration, decision, risk, and
  release memory;
- Claude Code and Codex adapters;
- deterministic graph, HTML, contract, provenance, release, and document checks;
- an optional lightweight AgentOps namespace that is never required for first
  value.

Not core scope:

- RAG, embeddings, SaaS UI, remote control plane, or enterprise workflow engine;
- automatic owner approval, ratification, merge, runtime, staging, or production
  authorization;
- a second issue tracker or a full copy of Spec Kit artifacts;
- a large standalone AgentOps product, universal team-role catalog, or mandatory
  multi-agent execution.

## 2. Authority And Planning Rules

1. `wiki/specs/alpha-wiki-product-spec.md` defines product behavior.
2. This file defines priority, dependency order, and task state.
3. `wiki/log.md` records accepted changes to canonical documents.
4. `CHANGELOG.md` records package and release changes.
5. Dated plans and audits provide evidence. They do not override this roadmap.
6. Source code and tests prove observed behavior. Accepted contracts define
   intended behavior. Wiki pages orient the agent but do not manufacture owner
   decisions or runtime evidence.
7. Update an existing canonical document before creating another one.
8. Use `wiki/agentops/` backlog entities only for an explicitly activated,
   multi-track execution wave. Planning alone stays in this file.

### Engineering Delivery Ownership

The R4 request consolidates earlier R2/R3 work here, not in another plan. The
goal is verified user outcomes; Alpha-Wiki observes and reconciles existing
engineering systems rather than replacing them.

| Concern | Authoritative source |
|---|---|
| Product intent and accepted decisions | Existing canonical specifications and ADRs. |
| Priorities, dependencies, execution state | This roadmap, or the observed project's existing tracker. |
| HTTP/event/data interfaces | Versioned contract or generation source in its owning repository. |
| Configuration and deployment intent | Application schema or existing infrastructure/GitOps repository. |
| Implementation and quality | Exact code snapshot, applicable tests, independent review, CI. |
| What actually runs | Identified build/deployment plus runtime and business-scenario observations. |
| Maintained memory and package history | Wiki journal; package changelog, tags and releases respectively. |

YAML is a serialization format, not an authority class. Discover OpenAPI,
JSON Schema/config, AsyncAPI/events, GraphQL/Protobuf, and Helm/GitOps by their
actual purpose. Reuse the owning toolchain and accepted format/version. Review
compatibility against an identified accepted revision before testing actual
consumers. Existing `tools/contracts_check.py` checks wiki structure; it does
not validate HTTP implementations or resolve semantic truth.

Use `references/concept.md` (Delivery Evidence And Contract Ownership) for the
shared Claude/Codex evidence contract. No mandatory provider split, new service,
tracker, approval chain, schema migration, or deployment follows from R4.

### Shortest Sufficient Path To Release

Choose the smallest complete change that meets the requested outcome. Reuse
existing tools and configuration. Add a mode, dependency, provider, service,
configuration option, or approval step only when the task or existing project
contract requires it.

Use these release rules:

1. State the release scope and required outcome before selecting checks.
2. Check the changed behavior and affected shared paths. A documentation edit
   needs document/link checks; a runtime or packaging change needs the relevant
   executable lifecycle and release checks. Reuse current results against the
   same unchanged inputs; rerun after relevant changes or new failure evidence.
3. For Alpha-Wiki package publication, the minimal evidence is a reviewable
   change, aligned version/changelog, relevant passing tests and smoke, the
   existing package audit, and verification that public installation uses the
   published source. Existing branch protection and repository rules still apply.
4. Treat static docs deployment as a separate outcome. A Pages outage blocks
   docs deployment; it blocks package publication only when the task or an
   existing project rule explicitly requires that dependency.
5. Label a release blocker only when an applicable mandatory step is prevented.
   Give its requirement source, failure evidence, affected step, and smallest
   corrective action. Use a command error, path, or existing CI link; do not add
   another report template or receipt service. Unchecked behavior is unverified,
   not proof of failure.
6. Do not invent signing keys, certificates, tokens, new secrets, extra votes,
   security ceremonies, or approval chains. Use existing authentication and
   publishing mechanisms. Diagnose actual permission errors without exposing
   secret values. If signing is already required, cite the existing requirement.
7. Cosmetic changes, speculative hardening, optional integrations, new config
   systems, and extra dashboards stay outside the current release scope unless
   they resolve an observed acceptance failure.
8. Continue independent work when one external action is unavailable. Existing
   user authorization carries across steps; request only a missing decision that
   materially changes scope or authority.
9. Stop when the applicable acceptance checks pass. Report the result, decisive
   evidence, and any remaining required action briefly.

### Caveman Research And Adoption

Reviewed on 2026-10-15 at upstream commit
`d262ab3882952a59312ff3537cd86d894523c5ab`.

Adopt three practices in existing Alpha-Wiki skills:

- Lead with the result, use the user's language, and remove repeated narrative.
  Preserve exact commands, paths, numbers, errors, negation, and evidence limits.
- Read relevant sections and summarize noisy output while retaining access to
  originals. A summary must preserve the exit code, failures, skipped checks,
  and decisive diagnostics; reopen the original when needed.
- Reuse current verification and stop after the required outcome is proven.
  Do not extend a completed fix with unrelated cleanup or speculative controls.

Canonical specifications, contracts, and source evidence retain complete,
readable language. Reduced token count is a hypothesis to measure against normal
concise operation; upstream savings are not Alpha-Wiki measurements.

The current upstream repository also includes proxy, cloud, routing, and output
compression components. This plan adopts writing and execution practices only.
It does not install those components, add accounts/secrets, or introduce a new
runtime dependency. Existing `doctor`, lint, and release tools remain the
execution path. Any later code reuse must respect the upstream license.

Sources: [Caveman README](https://github.com/juliusbrussee/caveman/blob/d262ab3882952a59312ff3537cd86d894523c5ab/README.md),
[voice rules](https://github.com/juliusbrussee/caveman/blob/d262ab3882952a59312ff3537cd86d894523c5ab/skills/caveman/SKILL.md),
[lean-build](https://github.com/juliusbrussee/caveman/blob/d262ab3882952a59312ff3537cd86d894523c5ab/skills/lean-build/SKILL.md),
[verify-and-stop](https://github.com/juliusbrussee/caveman/blob/d262ab3882952a59312ff3537cd86d894523c5ab/skills/verify-and-stop/SKILL.md).

## 3. Standard Backlog Model

### Priority

| Priority | Meaning |
|---|---|
| P0 | Blocks the next maintenance release or can make normal use unsafe. |
| P1 | Required for a credible v1.0 candidate or for reliable real-project use. |
| P2 | Valuable after pilots; must not delay the current release. |
| P3 | Research candidate with no delivery commitment. |

### Status

| Status | Meaning |
|---|---|
| DONE | Acceptance verified for the stated task scope; publication is required only for a publication task. |
| IN_REVIEW | Implemented locally or partially, but not yet accepted/published. |
| READY | Agreed and sufficiently specified to execute. |
| BLOCKED | Cannot progress without a named external action or accepted dependency. |
| CANDIDATE | Useful proposal; needs evidence or a scope decision before execution. |
| DEFERRED | Explicitly outside the current delivery horizon. |
| REJECTED | Conflicts with the product boundary or duplicates another system. |

### Required Task Fields

Every executable task must have:

- stable ID and domain;
- user or product outcome;
- bounded scope and explicit non-scope;
- implementation subtasks;
- acceptance criteria;
- verification evidence;
- dependencies and owner;
- priority, status, and release target.
- required final environment and evidence level; actual demonstrated level and
  earliest unmet applicable transition.

An implementation, a passing import, `--help`, a CI badge, a wiki status, and an
owner vote are different evidence types. None substitutes for another.

Keep task status separate from delivery evidence. L1 SPEC_READY, L2
CODE_VERIFIED, L3 INTEGRATION_VERIFIED, L4 MERGED_BUILD, L5 DEPLOYED_VERIFIED,
and L6 PROD_ACCEPTED use the definitions in `references/concept.md`. A local
document pilot can close at L2; a production feature requiring a live business
journey cannot close at L2 or from a health probe alone. Record NOT_APPLICABLE
for irrelevant stages, UNVERIFIED for unchecked behavior, and FAILED for an
observed failed check. BLOCKED additionally needs the mandatory gate, failure
evidence, impact, owner, minimum fix and clearing condition. These labels do
not migrate existing task enums or optional AgentOps statuses.

## 4. Consolidated Decision Ledger

| Topic | State | Consolidated decision |
|---|---|---|
| Repo-native Markdown memory | ACCEPTED | Plain files remain the primary memory and review surface. |
| Karpathy core operations | ACCEPTED | `ingest`, `query`, and `lint` remain the conceptual center. |
| Graph semantics | ACCEPTED | Typed links form clusters; color labels node role, not cluster membership. |
| Canonical document lifecycle | IN_REVIEW | Finite canon, one ownership parent, separate evidence/candidates/projections; local worker plans source deltas, applies reviewed edits, preserves normative sections during compaction, journals and checkpoints. Not published in 0.6.2. |
| Claude and Codex | ACCEPTED | Both are supported; platform differences must remain explicit. |
| Agent task priority | ACCEPTED | The requested deliverable overrides generic skill choreography. A skill mention does not imply fan-out. |
| Concise communication | ACCEPTED | Result first, exact technical facts, bounded context, and a short verification result. Apply through WF-004; token savings remain unmeasured. |
| Proportionate release checks | ACCEPTED | Use applicable existing requirements, prove blockers, and stop after sufficient verification. Do not invent signing, secrets, approvals, or speculative release gates. Implement alignment through REL-003. |
| Wiki authority | ACCEPTED | Wiki is orientation and maintained memory; exact source, Git snapshot, runtime, and owner authority outrank stale summaries. |
| Native subagents | ACCEPTED | Use only for independent material scopes with a pinned snapshot, bounded permissions, one writer, and controller synthesis. |
| Model routing | CANDIDATE | Lower-cost models may handle narrow mechanical/read-heavy work when the runtime supports explicit selection; decisive security, authority, and release judgments stay with the controller. |
| Optional AgentOps | ACCEPTED | Keep the lightweight namespaced control layer optional and outside first-run. |
| Standalone enterprise AgentOps | REJECTED | The old multi-repo, many-role product plan is not the Alpha-Wiki roadmap. |
| Spec Kit source adapter | CANDIDATE | Consider a read-only source adapter after the maintenance release and real-project pilots. |
| Spec Kit workflow clone | REJECTED | Do not reproduce specify/plan/tasks/implement/converge inside Alpha-Wiki. |
| Semantic search / embeddings | DEFERRED | Revisit only after file search and optional BM25 fail at measured scale. |
| Hosted/SaaS product | REJECTED for current scope | No evidence justifies moving the memory source of truth out of the repo. |

## 5. Observations Converted Into Requirements

| Observation | Product requirement | Backlog link |
|---|---|---|
| A bare `spawn-agent` mention caused premature parallel wiki review. | Delegation requires explicit mode plus independent scope; the controller continues the user's main deliverable. | WF-001 |
| Helpers found useful facts but delayed the primary task. | Fan-out is optional optimization, not a mandatory phase; wait only when the next decision needs the result. | WF-001, WF-003 |
| A stale wiki page can conflict with exact versioned sources. | Expose the gap and provenance; never stop the task merely to make wiki and source agree. | EVI-001 |
| Existing target repos may not contain `click`, Jinja2, or PyYAML. | Alpha-Wiki tools run from one declared runtime without modifying target dependencies. | RUN-001 |
| In-process smoke and `--help` did not prove target execution. | Release smoke must use separate processes and brownfield dependency fixtures. | QA-002 |
| Generic 17-section audit output conflicted with a requested A-G report. | User output contract and strict read-only permissions override a default report skeleton. | WF-002 |
| Untracked or missing sources were treated too confidently. | Attribute every snapshot to a repository and label unversioned material as candidate/unknown. | EVI-002 |
| CI, owner acceptance, merge, runtime, and production were conflated. | Store and report these gates separately. | EVI-001 |
| Session-end hooks appended technical heartbeat noise. | Hooks report maintenance gaps; only meaningful document changes enter the global log. | DOC-001 |
| Dated plans accumulated and competed for priority. | One canonical roadmap; supporting documents are labelled historical, research, or case evidence. | GOV-002 |
| Repeated narrative and broad output can consume context without improving the result. | Result-first answers, targeted reads, source-preserving output summaries, and a clear stop condition. | WF-004 |
| Speculative hardening can grow a release into extra config, secrets, signatures, and approvals. | Every mandatory release condition must trace to the task, existing repository rules, or an observed failure of a required step. | REL-003 |

## 6. Domain Map

| Domain | Prefix | Outcome | Current focus |
|---|---|---|---|
| Governance and scope | GOV | One product boundary, roadmap, and canonical document set. | Reconcile the dirty baseline and retire competing priority claims. |
| Runtime and installation | RUN | Tools start reliably without contaminating target dependencies. | Dependency-aware launcher and executable diagnostics. |
| Document and memory lifecycle | DOC | Memory stays compact, current, traceable, and non-duplicative. | Accept and publish document worker behavior. |
| Agent workflow | WF | Agents follow the task, use context efficiently, and delegate only when useful. | Task-first skill contracts and adaptive output. |
| Evidence and trust | EVI | Statuses and claims remain source-backed and authority-aware. | Gate vocabulary, provenance, freshness, unknowns. |
| Graph and presentation | GPH | Humans and agents can orient quickly without graph complexity. | Real-project cluster QA and artifact consistency. |
| Quality and pilots | QA | Release claims are backed by isolated and real-project evidence. | Case replays, subprocess smoke, 15-minute pilot. |
| Packaging and release | REL | Public source, tag, installed plugin, docs, and tested SHA agree. | Compatible maintenance release. |
| Upgrade safety | UPG | Updates preserve user-owned files and expose active version/path. | Managed-file inspection and repeatability. |
| Optional integrations | INT | External processes contribute sources without taking over Alpha-Wiki. | Spec Kit adapter decision after pilots. |
| Optional AgentOps | AOP | Multi-track execution state remains bounded and optional. | Compatibility/status hardening only. |

## 7. Delivery Waves

```text
Wave 0: reconcile baseline and canonical plan
  -> Wave 1: runtime + task-first behavior + evidence fixes
  -> Wave 2: isolated proof + public maintenance release
  -> Wave 3: real-project pilots and v1.0 quality
  -> Wave 4: optional integrations selected from evidence
```

No Wave 3 or Wave 4 item may become a maintenance-release blocker unless a
pilot exposes a data-loss, security, install, or core lifecycle failure.

## 8. Wave 0 - Baseline And Governance

| ID | P | Status | Outcome | Subtasks | Acceptance / evidence | Depends |
|---|---|---|---|---|---|---|
| GOV-001 | P0 | DONE | Isolate a reviewable 0.7 delivery boundary. | Candidate codex/release-0.7.0 starts at published 36df49e; both worker modules, additive governance, ingest recovery, read-only reports and necessary adapters/tests are included. | Local L2: 288 tests, smoke/audit and archive checks pass. All 380 preserved primary files are unchanged. Entity schema, AgentOps and runtime-only upgrade remain compatible; see section 20. | None |
| GOV-002 | P0 | IN_REVIEW | Make this file the only active roadmap. | Replace legacy mixed Alpha-Wiki/AgentOps phases; update docs index and product links; mark dated plans as supporting evidence; keep rejected work out of active tasks. | Document worker passes; docs index names one canonical roadmap; no second active priority list. | GOV-001 for commit |
| DOC-001 | P0 | IN_REVIEW | Enforce finite canonical documents and bidirectional change records. | Fix NUL-delimited Git paths and custom wiki/index slugs; validate record/check, explicit registration, ownership hierarchy, and meaningful journal records. | Regression tests and cross-platform lifecycle must pass on the current implementation. Existing broad worktree remains unpublished; no new release authorized by this task. | GOV-001 |
| GOV-003 | P1 | READY | Define idea-to-task promotion without document proliferation. | Keep hypotheses in this roadmap; require owner/outcome/acceptance/dependency before READY; create AgentOps task files only for an activated wave. | No one-file-per-idea backlog; active wave can be projected deterministically when needed. | GOV-002 |
| OPS-001 | P0 | IN_REVIEW | Attribute hosted CI and Pages correctly. | New 12fd58d plugin-ci run 39271869745 and docs-pages 39271869737 failed before execution. Check annotation confirms GitHub account billing lock; main is unprotected. | Hosted results are not green. Existing local/package publication succeeded independently under actual branch rules. Owner must restore GitHub Actions billing to rerun hosted CI/docs deployment. | GOV-001 |

## 9. Wave 1 - Runtime, Workflow, And Trust

### Runtime And Installation

| ID | P | Status | Outcome | Subtasks | Acceptance / evidence | Depends |
|---|---|---|---|---|---|---|
| RUN-001 | P0 | DONE | One dependency-aware launcher for project tools. | Published separately as 0.6.2 at 36df49e; remote main verified at that SHA on 2026-10-18. This dirty primary checkout remains on 0.6.1 plus pending work; do not confuse it with the released tree. | Release-specific public/install proof belongs to 0.6.2. The document worker and pending schema/AgentOps work were excluded. | GOV-001 |
| RUN-002 | P0 | DONE | Keep selected 0.7 hooks operational through runtime changes. | Retained stale-cwd behavior and runtime-only upgrade; actual fresh/brownfield hooks pass. Restored four already-configured but absent primary Claude scripts from published assets without overwriting settings. | Primary doctor: 27 pass, 1 optional workflow warning, 0 fail; SessionEnd exits 0. Runtime-only repair of missing configured scripts remains a measured follow-on under UPG-001. | RUN-001 |
| RUN-003 | P1 | CANDIDATE | Machine-readable runtime and capability inspection. | Report package version, runtime path, active skill surface, config, hooks, managed files, and supported features through existing doctor/install interfaces. | JSON or structured output is stable and does not add a broad management command family. | RUN-001 |

### Task-First Agent Workflow

| ID | P | Status | Outcome | Subtasks | Acceptance / evidence | Depends |
|---|---|---|---|---|---|---|
| WF-001 | P0 | READY | Skills assist the task instead of replacing it with wiki work. | Remove conflicting default modes/counts; bare skill mention does not imply fan-out; stale wiki becomes a gap; controller continues independent work. | Ratification replay starts candidate/source work and does not launch unsolicited parallel wiki audits. | GOV-001 |
| WF-002 | P1 | IN_REVIEW | Audit and review adapt to the user's output and write contract. | Added explicit status/review `--read-only`, fresh in-memory counts, no `--out`, and prepared-runtime/bytecode guidance for both platforms. | Local no-write regressions cover missing/stale graph and CLI subprocesses. Full A-G model replay remains unverified; required L2. | WF-001 |
| WF-003 | P1 | READY | Native subagents are economical, bounded, and reusable. | Pin one snapshot per repo; label repository on every receipt; avoid repeated remote polling; reuse coherent workers; choose model only after scope; controller verifies decisive evidence. | One-worker, explicit parallel, stale snapshot, partial result, and unavailable worker cases pass. | WF-001, EVI-002 |
| WF-004 | P1 | DONE | Keep communication and context proportional to the task. | Published in v0.6.1 at 89f77f2: 16 skills, shared references, generated contract, and affected Claude wrappers. | Public clone: 204 tests, smoke PASS, audit READY; installed Codex 0.6.1 skill copies matched release. Token savings unmeasured; live Claude model replay remains unverified after OAuth expiry. | Broader dispatch cases remain under WF-001 |

### Evidence And Status

| ID | P | Status | Outcome | Subtasks | Acceptance / evidence | Depends |
|---|---|---|---|---|---|---|
| EVI-001 | P0 | IN_REVIEW | Separate execution progress from acceptance and release authority. | Shared evidence levels L1-L6 and scope-specific DoD accepted in product/concept/roadmap; distinguish UNKNOWN/UNVERIFIED/FAILED from real blockers. Optional AgentOps migrations remain separate. | Required L2 for instruction replays. No production or owner acceptance inferred from local checks. Broad model replay remains unverified. | GOV-001 |
| EVI-002 | P1 | IN_REVIEW | Every delivery conclusion has attributable provenance. | Shared contract identifies repository, SHA/worktree, source/generator, consumers, accepted prior revision, compatibility, checks, time, and applicable artifact/environment/runtime. | Local repository/remote and GitLab access inspected; multi-repo A-G replay still unverified. Required L2 for evidence extraction, not L6 deployment. | EVI-001 |
| EVI-003 | P1 | CANDIDATE | Surface memory quality without semantic overclaims. | Consolidate provenance, freshness, open-question owner/timebox, source drift, and contract links in status/review. | Deterministic fields only; reports explain limits and do not claim semantic truth resolution. | EVI-001, pilots |

## 10. Wave 2 - Integrated Proof And Maintenance Release

| ID | P | Status | Outcome | Subtasks | Acceptance / evidence | Depends |
|---|---|---|---|---|---|---|
| QA-001 | P0 | IN_REVIEW | Replay task, permission and evidence failures. | Twelve held-out native Codex response replays were compared with existing expectations; all matched. Backend no-write/recovery/upgrade tests pass in subprocesses. | L2 for observed Codex responses and deterministic backends only. Real external operations were not executed by the replay; live Claude remains under WF-003.1. | RUN-001, WF-001, EVI-001 |
| QA-002 | P0 | DONE | Verify selected 0.7 fresh/brownfield lifecycle in separate processes. | Clean public clone at 12fd58d: 288 passed in 66.07s; four isolated Claude/Codex scenarios cover runtime, maintenance, hooks, graphs/HTML and product environment preservation. | Local/runtime L2 plus published-source verification accepted for this release. External-corpus and production integration remain outside scope. | RUN-001, DOC-001 scoped 0.7 implementation |
| QA-003 | P1 | READY | Prove graph and HTML remain useful on real data. | Mixed-role cluster snapshot; orphan detection; relative HTML links; source-owned service/module/feature/contract grouping; Obsidian vault instructions. | Deterministic graph agrees with frontmatter; no color-only clustering or graph-root confusion. | QA-002 |
| REL-001 | P0 | DONE | Publish the accepted 0.7 package. | Source commit 12fd58df2043ecccca8f7553c9c6dbe32e7299a4 pushed normally to GitHub main; annotated v0.7.0 and public release/source artifact published. | L4 package evidence: clean public clone 288 tests, smoke PASS, audit READY; artifact uploaded and public source/install verified. Hosted CI billing failure remains separately reported. | GOV-001, scoped QA-001/QA-002, actual repository rules |
| REL-002 | P0 | DONE | Verify public 0.7 installation and active Codex discovery. | Codex installed 0.7.0+codex.local-20261019144933, enabled, one 16-skill surface; fresh CLI session read the new ingest skill. Claude package updated 0.5.0 to 0.7.0; its existing disabled preference was preserved. | Installed files match public 12fd58d. Both adapters pass fresh/brownfield runtime fixtures. This is not a live Claude model-cycle claim; existing desktop sessions still require restart. | REL-001 |
| REL-003 | P1 | DONE | Align release guidance with the shortest sufficient path. | Published in v0.6.1 at 89f77f2; actual signing/auth requirements remain applicable, optional findings retain their scope. | Public clone and Codex installation verified; backend verdicts retained. CI/Pages jobs for that SHA did not start because GitHub reported a billing lock; live Claude model replay was not verified. | None |

## 11. Wave 3 - Pilots And v1.0 Quality

| ID | P | Status | Outcome | Acceptance trigger | Depends |
|---|---|---|---|---|---|
| PILOT-001 | P1 | READY | Measure first useful memory on one greenfield and one brownfield project. | Both reach install -> init -> doctor -> ingest one source -> query -> status -> HTML in under 15 minutes or produce classified friction. | REL-002 |
| PILOT-002 | P1 | READY | Measure agent onboarding quality. | New agent answers purpose, scope, modules, contracts, risks, forbidden changes, status, and next action with citations and bounded context. | PILOT-001 |
| DOC-002 | P1 | IN_REVIEW | Maintain source-bound documents incrementally and compact redundant prose without erasing evidence. | Local plan/apply, bounded batches, source/config/document hashes, cooperative writer lock, resumable transactions, no-op checkpoints, four-layer guidance, and source drift notices. Verify unit regressions, fresh/brownfield Claude/Codex subprocess flows, and a self-pilot. The large screenshot corpus remains uninspected; external-corpus compaction is unverified. | DOC-001, RUN-001; external pilot before wider rollout |
| DOC-002.1 | P1 | DONE | Prove a closed-loop local worker job on the existing retrieval/health domain. | Pilot A closed by the Codex controller on 2026-10-19 at L2: three source-bound pages reviewed/applied/journaled, graph reconciled, cited retrieval and zero-job/no-op verified. Recovery/compaction/stale-input tests and four isolated platform/runtime scenarios pass. See section 18 for evidence and limits; live Claude remains a separate Pilot C failure. | Local acceptance only; DOC-002, publication and external-corpus acceptance are not implied |
| DOC-002.2 | P1 | DONE | Reconcile ingest memory without expanding the canonical set. | Source-reviewed existing ingest page applied through pinned worker transactions; per-page recovery, portable bindings, reimport identity and controller acceptance are documented. | Local L2: cited retrieval, governance/lint and no-op pass; selected plan has zero jobs. Four bound pages are current, 34 inventory documents remain unchecked. | DOC-002.1 |
| EVI-002.1 | P1 | IN_REVIEW | Trace one real interface from requirement through executing implementation. | Pilot B uses this repository, as selected by the user. Inspect real contracts and reuse validators; verify an existing CLI operation locally. No HTTP service or OpenAPI source exists here, so HTTP/deployed conformance is NOT_APPLICABLE to this scope, not manufactured proof. Required L2 for local CLI behavior; real HTTP L3+ requires a service-bearing scope. | EVI-001, EVI-002 |
| WF-003.1 | P1 | BLOCKED | Prove one bounded live Claude/Codex implementation and review cycle. | Pilot C's actual Claude call failed on 2026-10-19: `API Error: 402 insufficient balance, please top up at /panel`. Existing CLI authentication was inspected; no source proposal was produced. Required live writer step cannot run through the configured provider. Operator restores existing provider access, then controller retries the same bounded test task. Required L2; all local work continues independently. | WF-003, QA-002; configured Claude provider must accept the live request |
| DOC-003 | P2 | CANDIDATE | Catch up registered maintenance scopes without idle model calls. | Pilot D: reuse hook/source-drift primitives; inspect missed events, multiple worktrees, interruption/recovery, and idle NO_CHANGE. Current worker is request-driven, not a session-discovery daemon. Add only minimal local recoverable state after an observed need; no server or Temporal. | DOC-002, scoped pilot authorization |
| EVI-004 | P1 | CANDIDATE | Add alias/glossary support only for observed rename/synonym failures. | At least two pilot failures come from unresolved aliases; deterministic lookup solves them. | PILOT-002 |
| EVI-005 | P2 | CANDIDATE | Add small/medium/large context profiles. | Measured context cost or truncation harms onboarding; profiles preserve answer quality. | PILOT-002 |
| UPG-001 | P1 | IN_REVIEW | Preserve user-owned project state through upgrades. | Retained and tested runtime-only dry-run/upgrade, user docs/contracts/config/routing and product dependency preservation. Added explicit managed-tool replacement guidance and packaged maintenance quickstart. | Local L2 fixtures pass; real public install result remains under REL-002. Broader modified-managed-tool detection is not claimed. | RUN-001, REL-002 |
| GPH-001 | P1 | READY | Close remaining graph quality gaps from real projects. | Pilots show correct mixed-color clusters, understandable labels, bounded isolated nodes, and deterministic rebuilds. | PILOT-001 |
| V1-001 | P1 | READY | Decide v1.0 from evidence, not feature count. | Two pilots pass core journey; release/install receipts are repeatable; docs are honest; no open P0. | All Wave 3 P1 required items |

## 12. Wave 4 - Optional Integrations

| ID | P | Status | Outcome | Start condition | Non-scope |
|---|---|---|---|---|---|
| INT-001 | P2 | CANDIDATE | Detect `.specify/` and `specs/` as an external source family. | Maintenance release stable plus one real project using both products. | Never edit Spec Kit sources or mirror every task. |
| INT-002 | P2 | CANDIDATE | Project one active feature into concise linked memory. | INT-001 proves source versions/digests and idempotency. | No Spec Kit workflow engine inside Alpha-Wiki. |
| INT-003 | P3 | DEFERRED | Optional explicit Spec Kit sync extension. | Two successful combined pilots and demonstrated demand. | No silent writes or mandatory AgentOps. |
| AOP-001 | P2 | CANDIDATE | Harden optional AgentOps status/evidence compatibility. | A real multi-track Alpha-Wiki project uses the namespace. | Not part of first-run or core v1.0 gate. |
| AOP-002 | P3 | DEFERRED | Additional orchestration roles/templates. | Repeated real demand that native subagents plus current control layer cannot meet. | No universal nine-role team by default. |

## 13. Hypothesis Ledger

| ID | Hypothesis | Validation | Decision rule | State |
|---|---|---|---|---|
| H-001 | Task-first skill contracts reduce detours and total context. | Replay the ratification, Work 3, and A-G audit cases; compare tool calls, elapsed steps, and deliverable fidelity. | Adopt if correctness is retained with fewer irrelevant reads/fan-outs. | testing planned |
| H-002 | A deterministic document worker prevents standards drift without process overhead. | Run in fresh/brownfield pilots; measure false positives and extra operator steps. | Keep blocking pre-commit/CI only if false positives stay low and recovery is clear. | local implementation |
| H-003 | Explicit provenance/freshness fields improve trust more than semantic contradiction tooling. | Ask agents to resolve stale/conflicting cases with and without fields. | Promote EVI-003 if answers become more accurate and source-backed. | candidate |
| H-004 | Lower-cost subagents reduce cost for bounded work without weakening decisions. | Use only runtime-supported explicit model selection on extraction/comparison fixtures; controller verifies outputs. | Document profiles only if quality and savings are measurable. | candidate |
| H-005 | Context budget profiles improve multi-agent onboarding. | Measure token use, truncation, and answer completeness on pilot wikis. | Implement EVI-005 only after observed need. | candidate |
| H-006 | A read-only Spec Kit adapter reduces duplicate reading and preserves cross-feature memory. | One combined project, one active feature, repeated ingest, source drift. | Start INT-002 only if summary remains concise and idempotent. | deferred until pilots |
| H-007 | BM25 is needed before embeddings. | Measure file search miss rate on large real wikis. | Add BM25 only after repeatable search failures; embeddings require a separate decision. | deferred |
| H-008 | Result-first communication and proportionate checks reduce context and release effort without losing correctness. | Compare WF-004/REL-003 replays against ordinary concise behavior: input/output tokens where available, tool calls, acceptance accuracy, and invented blockers. | Adopt instructions when exact facts and real failures remain visible, unsupported blockers disappear, and work is measurably reduced. No fixed saving percentage promised. | evaluation planned |

## 14. Deferred And Rejected Inventory

Deferred until a measured trigger:

- PDF/DOCX/web ingestion;
- BM25 and embeddings;
- multi-project memory;
- richer semantic contradiction analysis;
- hosted docs beyond static deployment;
- broader agent/platform catalogs;
- automatic model routing;
- advanced graph UI.

Rejected from the Alpha-Wiki core roadmap:

- SaaS knowledge platform;
- enterprise knowledge graph;
- autonomous daemon that edits standards without an explicit task;
- duplicate task tracker for every external task;
- full codebase parser;
- full Spec Kit or Superpowers clone;
- owner votes, ratification, merge, or production authorization inferred from
  wiki, CI, or agent output.

## 15. Legacy Roadmap Disposition

| Previous area | Disposition |
|---|---|
| Phase 0 audit | Completed historically; current regression facts live in tests and this backlog. |
| Phase 1a Alpha-Wiki hardening | Mostly delivered; remaining runtime/workflow/release work is normalized into Waves 0-2. |
| Phase 1b standalone AgentOps MVP | Superseded by the optional lightweight AgentOps boundary; not active. |
| Phase 2 Alpha-Wiki/AgentOps integration | Reduced to optional AOP candidates after core pilots. |
| Phase 3 Superpowers integration | Historical/optional; not an active Alpha-Wiki dependency. |
| Phase 4 automation | Core hook/CI work retained under RUN, DOC, QA, and REL. |
| Phase 5 packaging | Current release tasks retained under REL and UPG. |
| Phase 6 advanced | Moved to the hypothesis/deferred inventory with evidence triggers. |

## 16. Promotion And Completion Policy

Idea flow:

```text
observation -> hypothesis -> candidate -> ready task -> active wave
-> verified implementation -> accepted/public state -> done
```

Rules:

1. Observations do not become tasks until they have an outcome and evidence gap.
2. Candidates do not enter an active wave without acceptance and dependencies.
3. A task becomes DONE only when its acceptance evidence exists at the required
   state: local, merged, public, installed, or runtime.
4. Documentation changes update this file and `wiki/log.md`; do not create a new
   roadmap for each review.
5. When a wave needs parallel execution, project only that wave into the optional
   AgentOps backlog with the same IDs. The controller remains the owner of shared
   files, gates, and synthesis.
6. Close or reclassify tasks after every release and pilot. Do not preserve stale
   READY items merely because they were once proposed.

## 17. Immediate Execution Order

1. Preserve the dirty primary checkout. Its published runtime baseline is
   0.6.2 at 36df49e; reconcile release-only differences separately, not by
   overwriting pending migration or AgentOps changes.
2. Preserve DOC-002.1's verified local acceptance and source-pinned checkpoints.
   Do not repeat completed work unless its relevant inputs change. DOC-001 and
   DOC-002 still require acceptance of their wider unpublished delivery scope.
3. GOV-001's selected 0.7 boundary is now locally verified; use section 20 for
   current release execution. Wider unfinished schema/AgentOps work is excluded.
4. DOC-002.2 is locally complete. Preserve its checkpoints; execute the remaining
   publication/install acceptance. Section 19 keeps the task contracts, not a
   competing current-state report.
5. Resume WF-003.1 after the operator restores existing Claude provider access.
   Continue independent work in the meantime. Inspect any later supplied HTTP
   project or external corpus before extending its pilot claims.
6. Release, push, plugin installation,
   schema migration, and AgentOps publication require their own authorized scope.
7. Consider an existing scheduler only after the explicit maintenance run is
   useful. A server/API/Temporal adapter needs a demonstrated durable-execution
   requirement; none is required for this implementation.

### DOC-002.1 - Closed-Loop Worker Contract And Pilot A

Status: DONE for the bounded local Codex-controller pilot on 2026-10-19.
Owner: the executing controller; product owner: Alpha-Wiki maintainer. The
requirements below remain the acceptance contract. Results and limits are in
section 18; this is not acceptance of all DOC-002 or live Claude behavior.

Historical planning baseline on 2026-10-19: the existing ingest-page maintenance
plan has zero pending jobs, one source-bound document, and 37 unmapped canonical
documents. That is bounded coverage, not proof that the complete wiki is fresh.
The previous 2026-10-18 implementation run recorded 274 passing tests and a
passing release smoke; those runs are historical evidence, not a new test run
for this planning edit.

The outcome is a completed user request, not successful invocation of a helper.
The current `plan/apply` backend supplies important deterministic stages, but
does not independently interpret a user request, author reviewed semantic
changes, run all job acceptance checks, or close the owning task. Treat that
controller/worker integration as an agent-owned workflow, not an autonomous
backend. This local pilot verified that workflow; publication and wider
operating cases remain distinct. Product requirements are maintained in
`wiki/specs/alpha-wiki-product-spec.md` (Closed-Loop Worker Outcome).

#### User Stories And Acceptance Cases

| ID | User story | Observable acceptance |
|---|---|---|
| US-DOC-01 | As a project owner, I want to submit a document-maintenance task once and receive a checked outcome without manually coordinating every tool. | Given explicit scope, sources, permissions, and acceptance, one existing Claude/Codex workflow carries the job through its applicable stages and reports DONE, NO_CHANGE, NEEDS_INPUT, or FAILED with evidence. It does not stop at a plan, proposed text, or `apply` exit code. |
| US-DOC-02 | As a developer, I want a changed specification to remain consistent with the wiki and linked project entities. | Given an authorized change to a canonical source, update its existing owner first, pin the resulting source, then refresh dependent wiki pages and generated graph/context. If synchronization fails, the overall job remains unfinished even when the source edit succeeded. Raw evidence is never rewritten. |
| US-DOC-03 | As an operator with an overgrown corpus, I want repeated explanations consolidated without losing requirements or generating more standards. | Given a bounded set of existing documents, classify canon/evidence/candidates/generated views, identify actual redundancy, and compact reviewed prose in place. Preserve requirements, contracts, decisions, risks, open questions, provenance, identity, and hierarchy. Do not manufacture a new research report or claim semantic completeness from a size reduction. |
| US-DOC-04 | As an operator, I want a meaningful shared history instead of technical heartbeat noise. | Actual canonical edits receive one concise attributable project-journal record per coherent batch. Use CHANGELOG.md only for a package/release behavior change when applicable. A query or unchanged rerun creates no document-change entry. The record identifies affected documents, reason, and source evidence. |
| US-DOC-05 | As a user, I want interrupted work to resume without losing human edits or duplicating output. | Stop the job after an intermediate write or before final validation, then resume from its recorded step. Preserve completed work, detect changed inputs/concurrent edits, avoid repeated journal entries, and never mark the overall task DONE while synchronization or required checks remain incomplete. |
| US-DOC-06 | As a new agent or engineer, I want to find the current answer and its authoritative source quickly. | After the job, retrieve the changed facts through targeted query and the current brief; follow valid ownership/cross-links to sources. Separate accepted facts, local implementation, published behavior, and unresolved gaps. Zero pending work for selected pages must not imply freshness for unbound documents. |
| US-DOC-07 | As a user asking only for an audit or answer, I want the workflow to respect read-only scope. | A strict read-only request produces an answer and evidence without repository writes, log entries, graph refreshes, task-state edits, or implicit import. Use suitable read-only tools; do not invoke a write-producing backend merely because it is normally part of maintenance. |

#### Closed-Loop Job Contract

Reuse the existing skill/controller entry point and backend operations. Do not
add another public command family, server, scheduler, model SDK, or AgentOps
control plane merely to demonstrate a worker. A worker may be one agent using
deterministic tools; the pilot does not require multiple agents.

At intake, bind a task reference (the existing backlog subtask is sufficient),
the requested outcome, repository and allowed paths, input evidence, write
permissions, applicable acceptance checks, and a stop condition. An explicit
task is sufficient authorization within its scope; ask only for a missing
decision, source, or permission that actually prevents completion.

One user-visible run carries these internal stages:

1. Inspect the scoped inputs and recover an existing pending job if present.
2. Resolve the current canonical owner, provenance, hierarchy, and dependencies.
3. Prepare and review the smallest edits that satisfy the requested outcome.
4. Apply authorized source-owner edits first when required; then re-plan and
   apply dependent projections against the resulting hashes. Do not place a
   changing owner and its dependent in the same stale-input batch.
5. Record actual document changes and refresh the applicable wiki, index if
   navigation changed, typed links, graph, brief, and open questions. Refresh
   static exports only if they are part of the task's declared output.
6. Verify the requested result through relevant structural checks and retrieval.
   Pre-existing unrelated gaps remain visible without hijacking the task.
7. Persist the minimal successful job outcome and update the owning backlog
   subtask when it is part of the write scope. Only then report completion.
8. Return a concise result: outcome, changed paths, decisive checks, unresolved
   gaps, and any next required action. Do not produce another standalone report.

The journal records meaningful changes, while checkpoints record technical
progress; neither substitutes for checking the user's outcome. Reuse local
worker state and the existing backlog/journal rather than inventing a second
task tracker. A successful batch checkpoint is not proof that the whole job is
complete. Determinism means pinned inputs, explicit transitions and permissions,
repeat-safe effects, and reproducible checks; LLM wording and semantic judgment
are not guaranteed to be deterministic.

Intended job outcomes (not a migration of AgentOps status enums): DONE means all
applicable acceptance passed; NO_CHANGE means the same acceptance passed and
needed no content edits; NEEDS_INPUT identifies the exact missing prerequisite; FAILED
records the failing step and recovery action. An interrupted job remains pending
at its last durable step. Partial progress, an open transaction, unresolved
in-scope acceptance, or a plan alone is never DONE.

#### Pilot Workers And Owned Scope

Pilot A is one maintenance worker/controller job in this repository. Its source
pages remain the existing three-page domain:

- `wiki/specs/alpha-wiki-query-operation.md`
- `wiki/specs/alpha-wiki-status-operation.md`
- `wiki/specs/alpha-wiki-review-operation.md`

Pilot B now names the R4 contract-lifecycle pilot, not the earlier proposed
external-document batch. The user selected this local repository on 2026-10-19.
Use its real CLI/file interfaces; an HTTP endpoint/OpenAPI/deployment is absent.
Do not add a server just to satisfy that example. An external large-corpus
document test remains a separate DOC-002 follow-on, with no inspected corpus yet.

Pilot C is the bounded live cross-agent cycle under WF-003.1. Pilot D remains
the optional catch-up/recovery/idle experiment under DOC-003. Pilots validate
user outcomes, not headcount. Query/status/review pages remain Pilot A's corpus;
their user-facing operations are also checked for the requested write contract.

If the pilot exposes missing job-level coordination, adjust the existing shared
ingest/controller instructions, affected Claude wrapper, and focused regression
tests only as needed. Add a narrowly scoped backend change only for an observed
acceptance failure. Keep source-page review, source-owner edits, and tool-runtime
changes attributable; do not hide schema migration or AgentOps work inside this
pilot. Pilot A exposed the strict read-only gap and verified the bounded local
fix; later runs must assess their own inputs rather than generalizing that proof.

Subtasks, in order:

1. Inspect each page's existing provenance against its command, skill, and
   backend (`tools/wiki_search.py`, `tools/status.py`, `tools/review.py`). Read
   only relevant shared helpers. Distinguish current local behavior, accepted
   requirements, and published 0.6.2 behavior.
2. Add verified repository-relative `source_files` to these existing pages.
   Preserve stable slugs, ownership, and status. Register this metadata change
   in the project journal; do not infer source authority from filenames alone.
3. Align the existing worker/controller entry point with the intake, closure,
   evidence, and recovery contract above. Prefer existing skill orchestration;
   do not create a new provider runner just to automate a sequence the active
   agent can execute. Identify any remaining real runtime capability gap.
4. Plan one bounded worker batch. Review requirements, output sections,
   source-page versus generated-artifact mutability, and source-drift limits.
   Apply only evidence-backed corrections. Compact only demonstrated redundant
   prose; do not force a token-reduction target or change protected requirements
   through compact mode.
5. Verify document governance, lint, status/review, targeted retrieval, and
   graph/context consistency. Replay apply without changes and confirm no
   additional page, journal entry, or changed checkpoint. Reuse previous
   runtime tests unless relevant code or execution inputs change.
6. Close the overall scoped job only after its acceptance checks pass. Record
   the bounded result in the existing task and meaningful journal, keeping
   unresolved source gaps explicit. Do not mark parent tasks DONE solely
   because this pilot passes.

#### Definition Of Done

- A single invocation of the existing Claude/Codex workflow has carried the
  bounded job from intake to checked outcome, without operator hand-running
  the normal plan/edit/apply/journal/refresh/check sequence. A genuine ambiguity
  may end in NEEDS_INPUT, but that is not successful task completion.
- Each applicable user story above has a concrete acceptance result and source
  evidence. Claude and Codex behavior are checked separately; simulated workflow
  or subprocess tests are not described as live model-session proof.
- All three selected pages have checked source bindings and one clear existing
  ownership parent; references resolve without ownership cycles.
- Selected pages reflect reviewed source behavior. `date_updated` changes only
  after substantive review, never as a bulk freshness reset.
- No new canonical document, source-evidence rewrite, dependency injection,
  unrelated migration, or AgentOps change occurs.
- Actual edits have matching journal records. Generated graph/context files
  are rebuilt by tools, not hand-edited.
- The requested facts can be retrieved with citations. Required in-scope checks
  pass before the task is closed; baseline or unrelated findings are separately
  attributed. A checked source edit with failed wiki synchronization is partial
  progress, not DONE.
- A second apply is unchanged, and a fresh plan for the selected pages has zero
  pending jobs. Unmapped or stale documents outside the batch remain visible.
- Resume after interruption without duplicate edits or logs; reject observed
  stale sources and concurrent human changes without overwriting them. A
  repeat of the completed job creates no new canonical document or log entry.
- The final result names completed scope, actual writes, checks, and remaining
  gaps. The owning subtask reflects that result; no broader completion is
  inferred. Commit, push, release, and deployment are required only when the
  requested outcome includes them and authorization exists.
- Local implementation, published package, and installed plugin capabilities
  remain separately labelled.

Pilot acceptance order: normal changed-input run; checked no-change run;
interruption and recovery; stale/concurrent-input refusal; strict read-only
request; cited retrieval and remaining-gap check. Exercise both fresh and
existing-project Claude/Codex execution where the changed workflow requires it.

Follow-on order: select one explicitly supplied external corpus and validate
DOC-002 on it; review GOV-001's focused delivery boundary; verify UPG-001 and
QA-002 for that boundary; then execute REL-001/REL-002 only when publication and
installation are requested. Missing external paths do not block the local pilot
or unrelated work. The external pilot is not retroactively a gate for 0.6.2.

Apply the release rules above throughout execution. WF-004 and REL-003 were
published in 0.6.1; keep their behavior while reviewing further changes. They
add no prerequisite service, new secret, approval flow, or benchmark campaign
to publishing the existing compatible fixes.

The next release is a maintenance release only if the accepted diff remains
backward-compatible. The version is chosen from actual scope during REL-001; this
roadmap does not pre-authorize a tag, merge, or publication.

## 18. R4 Local Verification - 2026-10-19

Owner: Alpha-Wiki maintainer, with the current Codex controller executing the
authorized local work. This is acceptance evidence in the existing roadmap,
not a new report or tracker. Published package and installed-plugin state are
not changed by this local result.

### Baseline And Source Authority

- Primary checkout: `89f77f2d7cfc17da90090dec894c85ce5a461379`, dirty, behind
  `origin/main` by one commit. Remote main was read directly at
  `36df49efb6b14a07734e4336978ae0b60bba17a2` (published 0.6.2).
- Origin is `https://github.com/yura4gus/alpha-wiki-creator.git`. GitLab
  `value8.dev` authentication succeeds as `George_Gus`; accessible project
  search did not locate Alpha-Wiki. Existing GitLab processes can be reused
  after identifying the owning project; no mirror, CI project, or remote was
  invented. That absence does not block the local pilot.
- Installed Codex package remains `0.6.2+codex.local-20261018153031`, 16 skills,
  plugin-only. New worker/read-only/evidence instructions remain unpublished.
- Pre-R4 work was preserved in `/tmp/alpha-wiki-before-r4-20261019.tar.gz`.
  Comparison found no unexpected changes to existing files; both raw evidence
  files and the previously dirty HTML snapshots were preserved.

### Pilot Results

| Scope | Required / observed evidence | Result and limits |
|---|---|---|
| A: DOC-002.1 | L2 local document acceptance / L2 verified | Current Codex job completed intake, source review/binding, bounded plan/apply, journal/graph refresh, lint/governance, cited retrieval and no-op. Three existing operation pages changed; no new canonical page. |
| B: EVI-002.1 | Local CLI L2 / L2 verified; HTTP and deployment NOT_APPLICABLE here | User selected this repository. Existing status/review CLI plus Markdown/file inputs are the actual interface; command/skill/backend ownership is pinned by the Pilot A plan. Compared the published 0.6.2 backend: defaults still refresh graph; new `--read-only` is additive. Existing default and new failure-path/subprocess tests pass. No production HTTP endpoint, OpenAPI source, accepted API migration, or deployed service was fabricated. Original HTTP integration remains unverified outside this scope. |
| C: WF-003.1 | Live writer/reviewer cycle L2 / not attained | Claude Code 2.1.220 reports authenticated, but the configured provider rejected the bounded test-source request with HTTP 402. No implementation, review/fix cycle or live Claude completion is claimed. Restore existing provider access and rerun; do not add secrets or billing controls to Alpha-Wiki. |
| D: DOC-003 | Optional catch-up/recovery/idle experiment / not run | Request-driven source-drift/recovery primitives exist. Session discovery, periodic catch-up and multi-worktree coordination are not implemented by this pass. No daemon, scheduler or Temporal added. |

### Reproducible Acceptance Evidence

- `.venv/bin/python -m pytest`: **283 passed in 196.21s**. This includes
  `tests/unit/test_document_worker.py` for protected compaction, interruption,
  recovery, stale/config/concurrent changes and no-op; and
  `tests/integration/test_isolated_runtime.py` for fresh/brownfield projects
  under Claude and Codex adapters. Product dependencies remain untouched.
  These subprocess flows are not live model-session evidence.
- `tests/unit/test_read_only_reports.py`: nine new cases cover absent/stale
  graph, current edge/question counts, rejection of `--read-only --out`, and
  status/review/query subprocesses with zero target changes.
- Primary prepared-runtime status/review/query were also executed with
  `PYTHONDONTWRITEBYTECODE=1`. Before/after comparison of 4,778 filesystem
  entries, including file content and modification times, found zero target
  mutations. Query `strict zero-write` retrieved all three updated operation
  pages with line citations. Status/review reported 31 pages and 57 edges;
  review had zero errors/warnings and wiki-quality READY.
- Generated maintenance evidence: `.alpha-wiki/maintenance/r4-operations-plan.json`
  and `r4-operations-edits.json`. The plan pins config, source and document
  hashes. Replay returns `status=unchanged`; pages, graph, journal and checkpoint
  remain unchanged. A fresh plan for these three pages has zero jobs/deferred
  work and no hierarchy/source gaps. State/proposals remain local ignored
  artifacts, not another canonical specification.
- `tools.document_worker check`: PASS. `tools.lint --dry-run`: zero errors and
  warnings. Four edited skills pass the skill frontmatter validator.
- `tools.release_smoke`: PASS, including Mermaid/DOT/HTML exports.
  `tools.release_audit --root .`: READY, 8 pass, 0 warn/fail, **local metadata
  version 0.6.1**. This checks the dirty local package layout, not publication
  of the pending worker changes.
- `tools.doctor --platform both --refresh`: 26 pass, 2 warn, 0 fail. The
  primary checkout lacks installed Claude hook scripts and generated wiki
  CI workflows; isolated generated-project hook execution passes. Those
  warnings do not prove live-provider access or block this local document job.

### Remaining Scope And Next Slice

Only four canonical documents currently have source bindings; 34 inventory
documents remain unmapped. One previously bound ingest page became pending
after its skill/quickstart sources changed outside Pilot A. This bounded result
does not establish whole-wiki freshness or external-corpus compaction quality.

EVI-001/EVI-002 retain IN_REVIEW: the shared instructions and ownership model
are consolidated, but broad multi-repo/model replays are not complete.
EVI-002.1 retains IN_REVIEW for the original HTTP contract-lifecycle outcome;
the selected local CLI sub-scope is verified. QA-002's local subprocess proof
does not accept the broad unpublished migration or authorize publication.

Next executable slice: under GOV-001, isolate a reviewable maintenance boundary
against published 0.6.2 while preserving schema/AgentOps work, then execute the
applicable existing release checks only when publication is requested. In
parallel, the operator can restore the configured Claude provider for WF-003.1.
GitLab CI adoption needs a verified owning-project path, not a new control plane.

## 19. Next Task Specifications

Specified on 2026-10-19. This section refines existing backlog items; it does not
start their implementation, authorize publication, or change their status by
description alone. Section 18 remains the previous execution evidence.

### Shared Execution Contract

- Product owner: Alpha-Wiki maintainer. Executor: the active controller;
  independent reviewers receive bounded read-only scopes when useful.
- Intake records the requested outcome, source repository/snapshot, allowed
  paths, accepted constraints, final environment, and required evidence level.
  Reuse the current runtime, task IDs, source bindings, journal, and checkpoints.
- A task closes only after the outcome, applicable checks, canonical/wiki
  synchronization, and concise evidence are complete. Preserve interrupted
  transactions and concurrent human changes; checked no-change creates no
  document journal entry. Update this roadmap's task row, not a second tracker.
- The DoD for this specification pass is unambiguous inputs, scope/non-scope,
  steps, acceptance, dependencies, and owner for each next task. An implementation
  task's L2 or higher acceptance is not satisfied merely by writing this section.
- Use existing tests proportional to the changed surface. A fixture replay is
  not a live model, deployed API, public-install, or production proof. Record
  missing decisions as NEEDS_INPUT/UNVERIFIED unless a mandatory action has an
  observed failure. Do not invent credentials, approvals, or infrastructure.

### GOV-001 - Isolate The Next Reviewable Delivery Boundary

**User story:** As the maintainer, I can review and release one coherent change
without losing pending work or accidentally shipping schema/AgentOps changes.

**Target:** Local preparation, L2. Existing status remains IN_REVIEW.
**Inputs:** Dirty primary checkout, published 0.6.2 reference, current tests and
the existing preservation evidence. Inspect any suitable managed worktree before
creating another. Pin repository/SHA plus dirty digest before classification.

**Steps:** Compare actual files/hunks with 0.6.2; classify released runtime,
document maintenance, shared instructions, schema migration, optional AgentOps,
and generated snapshots. Trace imports, templates, bootstrap and test dependencies.
Select the smallest functional slice and retain excluded changes in the original
checkout and a recoverable backup. Record the inclusion/exclusion rationale here.

**DoD:** The selected tree can be reproduced from the published base, contains
every required dependency, passes its relevant tests/smoke/audit, and preserves
unrelated work byte-for-byte. No staged-file surprise or unrelated generated
output enters the slice. If worker code needs pending schema/bootstrap changes,
identify that dependency and resolve the boundary explicitly; do not promise
independence or copy a broken subset. Commit/push/tag/install are not this task.

### DOC-002.2 - Bring Existing Ingest Memory Current

**User story:** As an agent resuming work, I retrieve the current import and
maintenance workflow, rather than instructions already superseded by source edits.

**Target:** This repository, L2. READY; can run independently of release preparation.
**Inputs/scope:** `wiki/specs/alpha-wiki-ingest-operation.md` and its existing
`source_files`. Read current pending state; the previous count is evidence, not
a reason to skip fresh planning. Source owners are read-only in this task.

**Steps:** Review the actual skill, worker, import pipeline and quickstart;
plan the existing page; prepare the smallest reviewed replacement; apply;
run governance/lint and a cited query for closed-loop task acceptance. Inspect
the remaining coverage report without adding guessed or self-referential sources.

**DoD:** The page distinguishes import from refresh, controller task acceptance
from apply checkpoints, and local capability from public 0.6.2. Identity,
ownership, status and provenance survive. Journal and generated views match
actual edits; replay is unchanged and the selected fresh plan has zero jobs.
Unmapped documents remain explicitly unchecked; authoritative root documents
are not assigned fabricated source bindings to improve a percentage. No new
canonical page, raw rewrite, bulk date reset, runtime or provider change.

### QA-001 With WF-001/WF-002/EVI-001/EVI-002 - Replay Task And Evidence Rules

**User story:** As an operator, my requested deliverable and permissions survive
skill invocation, stale memory, delegation, and incomplete external evidence.

**Target:** L2 local regression evidence. QA-001 remains READY; linked items
retain their existing state until their own acceptance is proved.
**Inputs:** Existing case evidence, shared skills/references, current test
fixtures, and a pinned snapshot. Do not manufacture owner votes or service state.

**Cases:** Ratification plus bare spawn-agent mention does not launch unsolicited
wiki auditors; stale wiki routes to current sources without replacing the task;
an A-G no-write audit preserves its output contract and target files; an explicit
bounded helper has one owner and no nested fan-out; unversioned sources remain
candidates; passing CI is not merge, ratification, deployment or production.

**Steps:** Reuse existing deterministic tests, add only missing behavior cases,
and inspect affected Claude wrappers and Codex skills. For semantic instruction
behavior, run a bounded native-provider replay when available; do not substitute
keyword assertions for an observed model outcome. Controller checks final facts.

**DoD:** Each case records expected/actual outcome, writes, snapshot, diagnostics,
and terminal result. Fix only demonstrated discrepancies and rerun affected
checks. Label static/fixture and live-provider evidence separately. A missing
live replay stays unverified and does not block independent backend work.

### WF-003.1 - Finish The Live Cross-Agent Cycle

**User story:** As a maintainer, I can distinguish real independent implementation
and review from one agent simulating both roles.

**Target:** One isolated local change, L2. BLOCKED by the recorded provider 402
until existing access works; operator owns access, controller owns the pilot.
**Inputs:** A pinned implementation, one bounded regression-test task, existing
Claude/Codex adapters and credentials. Do not change billing, tokens, or providers.

**Steps:** Check the configured access once; Claude produces the scoped change;
Codex reviews its exact snapshot; Claude resolves actionable findings if any;
controller runs final tests and reconciles the owning task. Invalidate stale
approval after source changes. No artificial bug is required to force a fix cycle.

**DoD:** Evidence attributes each actual provider step, diff, finding/disposition
and final checked snapshot. Zero actionable findings is valid. Another provider
failure retains the exact error and unfinished scope; no fake implementation,
role switch, retry loop, merge or deployment is claimed.

### EVI-002.1 And OPS-001 - Bind Real Contracts And Hosted Processes

**User story:** As a developer, I can trace an actual interface and its CI results
to the owning repository without confusing a local check with a deployed service.

**Target:** Local CLI L2 is already verified. HTTP integration needs an explicitly
selected service/operation and L3 evidence; deployment levels apply only when
requested. Existing task states remain unchanged by this specification.
**Inputs:** Current Alpha-Wiki origin remains GitHub. GitLab work needs the
verified `value8.dev` group/project path; authenticated access alone is not a
project mapping. A service-bearing repository is required for the HTTP variant.

**Steps:** Read existing contract/generation sources, owner, consumers and
accepted prior revision. Reuse its validator and compatibility/consumer tests;
query existing MR/CI jobs read-only with exact SHA. Run against the actual
implementation in the authorized environment. Synchronize only the useful
contract summary and evidence into existing memory.

**DoD:** CLI, HTTP, CI, artifact, deployment and business acceptance are separately
labelled. HTTP proof includes actual request/auth/error/response and applicable
consumer results, not just schema validation or health 200. No fabricated server,
OpenAPI migration, GitLab mirror/project, new pipeline or remote change. An
unidentified project/operation is NEEDS_INPUT, not a global release blocker.

### REL-001/REL-002 And UPG-001 - Publish And Prove The Accepted Slice

**User story:** As a user, updating Alpha-Wiki loads the tested skills/tools and
preserves my project documents, settings and product dependencies.

**Target:** Published artifact and clean install, L4 for this package; a hosted
service deployment or L6 is not applicable. Execute only after publication is
requested and GOV-001's slice plus applicable checks are accepted.

**Steps:** Choose version from actual compatibility; align existing metadata and
changelog; use normal repository review/push rules; verify the exact public
revision in a clean clone and isolated Claude/Codex fresh/brownfield installs.
Inspect active version/path and one skill surface; test one maintained-document
operation, hook behavior, graph/HTML and repeat upgrade. Keep Pages separate.

**DoD:** Source, version, tag/artifact and installed runtime identify the accepted
release. Modified user-owned files are preserved or explicitly surfaced, and
no product dependency changes or duplicate fallback skills appear. Record
real CI/auth failures with their own scope. Do not require a live Claude model
or docs deployment for package publication unless an applicable release
requirement makes that evidence mandatory. No force push or unsolicited install.

### DOC-003 - Candidate For One-Shot Catch-Up, Not A New Service

**User story:** As an operator, I can catch missed source changes and resume a
bounded maintenance job without a model running while nothing changed.

**Target:** P2 CANDIDATE; specification only, not a commitment to a daemon.
**Start condition:** An observed missed-event/repeated-maintenance case and an
explicitly selected repository/worktree. Reuse existing plan/apply first.

**Proposed first slice:** One explicit local scan of registered source bindings;
pin repository/worktree/source identity; report bounded pending jobs; invoke
reviewed writing only within the authorized task; finish the shared closed loop.
Multiple worktrees have separate input snapshots and must not share stale
approval/checkpoints. Test recovery and contention before scheduling anything.

**DoD for a later implementation:** Changed-source, missed-hook, interrupted,
concurrent-edit and two-worktree cases pass; idle repetition has zero model
calls, canonical writes, journal entries or report proliferation. Source/event
discovery is read-only and allowlisted; do not scan all home directories or
ingest private transcripts implicitly. No server, API, broker, Temporal, mandatory
scheduler or new tracker. Session discovery and scheduling remain separate
future scope unless the pilot demonstrates a need.

### Dispatch Order

1. GOV-001 reviewable boundary; DOC-002.2 may run independently with disjoint writes.
2. QA-001 and linked WF/EVI cases on the selected snapshot. Keep EVI-002.1's
   local proof; extend to GitLab/HTTP only after the required target is identified.
3. Resume WF-003.1 when configured provider access works. It does not block
   unrelated local maintenance or automatically become a package-release gate.
4. REL-001/REL-002/UPG-001 only after a publication request and applicable checks.
5. DOC-003 only after its measured start condition; it must not delay that release.

GOV-001 was the first implementation entry point for this specification.
Its selected 0.7 result and next release action are maintained in section 20.

## 20. Release 0.7 Execution

Observed on 2026-10-19. This execution receipt supersedes the earlier
primary-checkout planning state for the selected release only. Wider pending
schema/AgentOps work remains preserved, not accepted by implication.

### Boundary And Authority

- Source base: published 0.6.2 at 36df49efb6b14a07734e4336978ae0b60bba17a2.
  Candidate branch: codex/release-0.7.0 in a dedicated managed worktree.
- Primary checkout remains at 89f77f2 with its unfinished work. Backup:
  /tmp/alpha-wiki-before-release-070-20261019.tar.gz. Comparison found all 380
  non-cache baseline files unchanged, including raw sources and dirty HTML.
- Included: both document-worker modules; source-binding/ownership policy;
  source-pinned maintenance/recovery/compaction; portable, resumable ingest;
  strict read-only status/review; necessary bootstrap/preset/hook/CI/installer
  integration, source memory, tests and aligned 0.7.0 metadata.
- Excluded: AgentOps fields/status changes, entity-schema migration, removal of
  CLAUDE.md generation, evolution-helper changes, unrelated navigation-schema
  exemptions, dated research additions and existing dirty HTML snapshots.
  Additive document_governance does not alter entity_types/cross_ref_rules.
- Published runtime launcher, bootstrap --runtime-only and its preservation
  tests are retained. Existing configs opt into maintenance explicitly; no
  full bootstrap is required to replace user schema.

### Verification And Findings

- Final local suite: 288 passed. Fresh/brownfield Claude/Codex subprocess
  scenarios cover actual isolated runtime, hooks, source maintenance, rendering
  and repeat upgrades without changing product dependencies.
- The partial-ingest failure reproduced in normal and resume modes. Per-page
  pending finalization now precedes completion checkpoints; crash retries and
  stale/concurrent refusal have focused regressions.
- Independent review identified relocated absolute bindings and historical
  slug deduplication. New relative bindings, explicit legacy gaps and transaction
  identities were implemented; relocation and retire/reimport governance tests
  pass. These findings are resolved by runtime evidence, not waived.
- Package inspection found private ignored maintenance payloads in source
  builds. Explicit source-distribution exclusions and a clean-copy canary
  regression now prevent them. Both 0.7 build formats are produced; the Git
  source/plugin remains the supported complete bootstrap distribution.
- Smoke PASS; release audit READY, 8 pass/0 warn/0 fail; Claude manifest
  validation PASS. Mermaid/DOT/HTML exports are exercised by smoke/tests.
- Strict status/review/query comparison covered 1,518 target entries with zero
  mutations. Four bound documents have zero pending jobs; 34 canonical inventory
  documents remain unchecked, not declared fresh. Cited ingest retrieval passes.
- Twelve native Codex responses to existing case inputs matched held-out
  expectations: bounded docs, supplied research, mandatory test/signing failure,
  authorized publication, access denial, optional Pages/hooks, ratification
  without automatic fan-out, A-G read-only provenance, missing click and wiki
  versus runtime authority. The replay did not execute external scenario
  commands or prove real production behavior. Live Claude remains unaccepted:
  one availability call returned API Error: 402 insufficient balance.
- GitHub main is unprotected and has no required-check protection. The latest
  inspected check at 36df49e never started: "The job was not started because
  your account is locked due to a billing issue." Local checks are not labelled
  hosted CI; current provider/billing configuration is not changed.

### Publication And Installation

- Accepted package source: 12fd58df2043ecccca8f7553c9c6dbe32e7299a4, normal
  GitHub main push. Annotated tag v0.7.0 resolves to that exact commit.
- Public release: https://github.com/yura4gus/alpha-wiki-creator/releases/tag/v0.7.0.
  Complete source asset alpha_wiki-0.7.0.tar.gz is uploaded with SHA-256
  bea030de5bc4ff635890d8a4feb64a1ca30f0f7e5a3e71e51228f65f1e606b43.
- A new public GitHub clone resolved to 12fd58d; uv sync --dev --locked installed
  0.7.0. Its full suite passed: 288 tests in 66.07s. Smoke PASS, audit READY,
  and governance against the 0.6.2 source base PASS.
- Codex manager/cache version: 0.7.0+codex.local-20261019144933, enabled.
  Sixteen adapted skills, no commands/ or standalone duplicate surface.
  Tools/assets/references/quickstart match published source bytes. A fresh
  ephemeral native CLI session discovered the exact cached ingest skill and
  quoted its closed-loop acceptance instruction; this was not inferred from
  a repository README. Existing desktop sessions must restart to reload.
- Claude user package updated from 0.5.0 to 0.7.0. Enabled=false was preserved.
  Cached tool/skill/assets match public source; no billing/auth/provider route
  was changed. A live Claude model implementation remains unverified (402).
- The package update exposed four configured but missing primary Claude hook
  scripts. Only those absent files were restored from published assets;
  settings and unfinished source work were preserved. Actual SessionEnd
  returned 0; primary doctor now reports 27 pass/1 warn/0 fail. Its remaining
  warning concerns absent optional generated wiki workflows, not plugin failure.
- New hosted plugin-ci and docs-pages runs are 39271869745 and 39271869737.
  GitHub again reports jobs did not start because the account is locked for
  billing. These are failed/unavailable hosted gates, not local test failures
  or CI success. Restore existing Actions billing and rerun; no new secrets,
  GitLab mirror, signature or approval flow is introduced.
- This post-publication receipt is documentation only. It does not move the
  existing release tag or change the accepted 0.7 code, package or skill content.

### 0.8 Boundary

DOC-003 remains P2 CANDIDATE. Existing plan/apply already supports an explicit
bounded one-shot catch-up; no new scheduler/server is justified by this release.
PILOT-001/PILOT-002 remain the wider real-project adoption target. This run
already measured one bounded UPG-001 follow-on: runtime-only upgrade does not
restore absent scripts even when existing Alpha-Wiki routing explicitly names
them. Next candidate: repair only missing, already-configured Alpha-Wiki hook
paths; preserve existing scripts, schema, settings/routing and product
dependencies. Required acceptance: stale/missing hook fixture, unrelated hook
untouched, dry-run zero writes and repeat upgrade unchanged. The actual primary
case was repaired locally, not silently presented as a new packaged capability.

Native Codex also warned that the existing four defaultPrompt entries exceed
its supported maximum of three. Skill discovery/execution still succeeds;
metadata cleanup is a non-blocking follow-on, not a reason to retag 0.7.
Other unrelated local MCP startup warnings are not Alpha-Wiki release gates.
No 0.8 feature or release is claimed from these observations. External HTTP
integration still requires its owning service/operation; it is not a synthetic
gate for the completed CLI/package release.
