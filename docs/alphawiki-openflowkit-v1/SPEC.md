# AlphaWiki xPlan Harness² OpenFlowKit — Engineering Canvas v1.0

**Document class:** proposed integration specification and acceptance contract. **Not** an implementation/release receipt.

## Decisions

- OpenFlowKit (MIT; application v2.2.0; CLI/MCP npm v0.3.0) is the chosen **architecture discovery and visualization layer**. It is not the workflow engine, runtime truth provider, task database, or a release arbiter.
- xPlan is the operational authority for issues, owners, dependencies and transitions.
- AlphaWiki is the repository-native authority for accepted specs, ADRs, constraints, provenance and governance. Its existing Mermaid/DOT/graph is preserved.
- Git and CI are authoritative for changed code, reviews, test/build/deployment evidence. Runtime claims require separate observed evidence.
- Claude Code and Codex are native implementation workers. OpenCode Go / DeepSeek Flash is independent reviewer; corrective writes require separate owned worktree and authorization.
- Google Harness² is a bounded **offline optimizer** of prompts/skills/tools. Never source-of-truth or an automatic production skill publisher.
- cmux is a visual terminal shell, not persistent state or task execution authority.

## Two distinct architecture representations

1. **Repo-observed view** (`openflowkit discover <clean-checkout>`) is an auto-generated draft of one specific Git SHA. Each edge may contain file/line discovery evidence. Promoted after validation into a repo-owned `docs/architecture/architecture.ofk` (or existing canonical architecture location). Run OpenFlowKit `drift` **only against this repo-scoped model**. Static discovery cannot prove runtime behavior.
2. **Cross-stack curated view** (`architecture/architecture.ofk` in this package) connects xPlan, AlphaWiki, CI, Harness², agents, OpenCode and cmux. Its connections are a **target interface design**, not something OpenFlowKit can discover from a single checkout. It is checked by schema/ownership contracts and review, **not** `drift` of any one repository.

Do not compare a cross-repo system diagram to a single repository or drift will generate false positives. Do not replace canonical AlphaWiki graph artifacts with a manual drawing. Existing Mermaid/DOT may be imported into editable diagrams with documented conversion loss; keep them as source if they are still authoritative for their scope.

## Suggested views and ownership

| View | Input authority | Viewer / edit rights | Freshness check |
| --- | --- | --- | --- |
| Repo structure | Git local checkout, manifests, imports, IaC | OpenFlowKit discover/map | SHA + repo drift against reviewed model |
| Service and event topology | Accepted OpenAPI/AsyncAPI/schema + actual code | Curated `.ofk` with source links | Contract validation and review |
| Data lineage | Pipeline definitions + table schemas + verified lineage | Curated flow/architecture diagrams | DAG/schema/test evidence, not static discovery alone |
| Engineering lifecycle | xPlan workflow + AlphaWiki AGENTS/ADR + Git CI | Lifecycle view in this package | Task quality gate and xPlan readback |
| Runtime health | Observability/CI evidence | Optional status overlay | TTL and observation time; never infer health from diagram |
| Skills optimization | Harness² experiment receipts | Separate laboratory overlay | Baseline vs candidate vs holdout, review before adoption |

## Minimal projection contract (for a future local adapter)

Inputs: `{project_id, repo_root, git_sha, task_id?, xplan_revision?, contracts[], evidence_refs[], harness_run_id?}`. All file references must point into explicit allowlisted checkout roots or local evidence directories. Redact secrets. No automatic transcript export.

Outputs:
- `discovery.ofk`: machine-suggested diagram; include source SHA and discovery summary.
- `curated.ofk`: reviewed repo diagram and source references.
- `report.json`: `PASS | DRIFT | UNKNOWN` plus grounded findings, scope, exact source hashes, rules checked, and one next action.
- `site/`: local static site, optional. Avoid publishing private diagrams externally.

A review receipt MUST distinguish `OBSERVED` (static code evidence), `DECLARED` (approved contract), `INFERRED` (unverified model inference), and `RUNTIME_VERIFIED` (actual observations). The Canvas cannot upgrade an `INFERRED` edge to `OBSERVED` by being drawn.

## Required gates

G0 — **Security/source pin**: authorized, clean worktree (or a separate explicit dirty policy), reproducible tool version, no credentials, no external upload by default.
G1 — **Syntax**: `openflowkit validate ... --strict`, render/save/reopen, no silent conversion loss for required links.
G2 — **Provenance**: nodes/edges trace to files/line or accepted contracts; missing data is `UNKNOWN`.
G3 — **Drift**: only compare repo-scoped model to that repository; renamed services reported as possible rename, not automatically removed/deployed.
G4 — **Task binding**: xPlan issue revision/status is an overlay, not written by Canvas; updates only through approved guarded task transition.
G5 — **Delivery**: model reviewer acceptance is advisory; `DONE` requires real requested DoD (merge/deploy if requested).

## Security and scale

- Keep the first pilot local, against a chosen sanitized or non-sensitive repo. Use local checkout for private GitLab; browser GitHub Map does not support GitLab.
- Local MCP over stdio is preferred. MCP exposes **write-capable tools** and the live pairing bridge: use separate privileges/capabilities for independent reviewer versus diagram author. Do not give review-only OpenCode an unrestricted editing tool set.
- Use a source-pinned model and require human approval to publish architecture diagrams with internal hostnames, customer data or authentication paths.
- The discovery CLI has a default `--max-files 2000`; verify coverage and split large repositories. Large code graphs are better explored through `map --depth detailed` than one giant diagram.
- Map mode is static, no watcher. Model matching is name/tech, not semantic contracts. Use an explicit controller to request rescans on changed Git SHA; zero idle model calls.
- Avoid installing a new database, vector store, broker, server or creating a parallel task tracker.

## Phased delivery

**CAN-001 (P0):** Run the pinned CLI, discover/map one real local repo, validate/preview.
**CAN-002 (P0):** Promote one reviewed repo diagram and demonstrate intentional drift detection.
**CAN-003 (P0):** Bind one real accepted contract or ADR to curated graph and check its source references.
**CAN-004 (P1):** Add a bounded read-only OpenCode/Flash architecture review packet; deterministic findings override model conjecture.
**CAN-005 (P1):** Link the view from one existing xPlan issue, with state readback but **no** status mutation.
**CAN-006 (P1):** Run the same workflow for a second architecture class (e.g., data pipeline or API events); measure fidelity/cost/performance.
**CAN-007 (P2):** Optional cmux status, static internal site, PR diagram checks after pilots pass.

## Launch gate

One real repository, pinned SHA, discovered diagram, observed file/line proof, verified parser/render, manual edit round-trip, meaningful drift report, and preserved source. Until these are observed in the operator's environment the state is **SPEC READY / LOCAL PILOT NOT VERIFIED**.
