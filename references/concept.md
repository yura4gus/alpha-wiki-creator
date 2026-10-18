# Concept

## Karpathy LLM Wiki (origin)

Three layers, three operations, two service files.

- **Raw** — immutable sources (read-only after capture)
- **Wiki** — LLM-generated markdown with cross-links
- **Schema** — `.alpha-wiki/config.yaml`; `AGENTS.md` is the human-readable operating contract

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
- **Session-end automation** (lint + log + context_brief rebuild)
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

## Release Decisions

After init, deterministic tools run through
`python3 .alpha-wiki/run.py -m tools.<module>`. The launcher resolves its project
from its own file path, prepares dependencies in `.alpha-wiki/runtime/.venv`,
and runs the copied project tools. Do not install Alpha-Wiki dependencies in the
product environment or edit product manifests. Before init, use the installed
plugin environment for bootstrap and initial source discovery.

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
