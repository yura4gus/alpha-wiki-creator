# Alpha-Wiki Quickstart

Goal: get from install to a useful, queryable markdown wiki in about 10 minutes.

Shortest path: install, init, doctor, ingest one file, query, status, render HTML. Everything else is optional hardening.

## 1. Install

Version 0.8.0 combines GOV-004/GPH fixes and compact engineering writing;
new AgentOps changes are excluded. Updating the plugin does not migrate an
existing project's runtime or overwrite its user instructions.

Claude Code:

```bash
claude plugins marketplace add yura4gus/alpha-wiki-creator
claude plugins install alpha-wiki
```

Codex:

```bash
npm install -g @openai/codex
codex --login
git clone https://github.com/yura4gus/alpha-wiki-creator
cd alpha-wiki-creator
python3 scripts/install_codex.py --upgrade --remove-legacy --remove-standalone
```

Preferred Codex plugin commands use `$alpha-wiki:*`. The default install exposes one set of 16 skills: 12 core workflows and 4 optional AgentOps workflows. Standalone `$alpha-wiki-*` skills are an explicit compatibility mode (`--standalone`, which skips the plugin) for Codex surfaces without plugin support. Claude commands use `/alpha-wiki:*`.

## 2. Bootstrap A Project

In the target project:

```text
/alpha-wiki:init
```

Codex equivalent:

```text
Use $alpha-wiki:init to bootstrap Alpha-Wiki in this project.
```

Recommended first-run choices:

- Preset: `software-project` unless the project is clearly research/product/personal.
- Wiki dir: `wiki`. Keep it visible so Obsidian can open it directly as a vault.
- Hooks: `all` for Claude and Codex project automation; review Codex hooks with `/hooks`.
- CI: enabled for GitHub projects.
- Obsidian: enabled.

During init, Alpha-Wiki first audits the current project. It should show candidate documents already in the repo, propose `raw/` placement or manifest-only references, propose the initial wiki structure, and split ingest into batches. For an existing repo, approve Batch 1 before trying to process the whole corpus.

## 3. Verify Runtime

Claude:

```text
/alpha-wiki:doctor --platform both --refresh
```

Codex:

```text
Use $alpha-wiki:doctor with platform both and refresh enabled.
```

Expected result: no failures. Warnings are acceptable before the first ingest if they say the wiki has no durable content yet.

### Isolated Runtime (0.6.2)

After init/upgrade, both platforms use the same project-local launcher:

```bash
python3 .alpha-wiki/run.py -m tools.doctor --project-dir . --platform both --refresh
python3 .alpha-wiki/run.py -m tools.status --wiki-dir wiki
```

The first call needs `uv` and installs dependencies under
`.alpha-wiki/runtime/.venv`. Later calls can reuse that environment without
`uv`. Root `pyproject.toml`, `uv.lock`, `requirements.txt`, `package.json`, and
the product's `.venv` remain untouched. Fresh projects do not get a root
Python project merely to host wiki dependencies. Before init, bootstrap still
runs from the installed Alpha-Wiki plugin environment.

Track `.alpha-wiki/run.py`, `.alpha-wiki/runtime/pyproject.toml`, and its
generated `.gitignore`; the runtime environment and local lockfile are build
outputs. For a missing dependency, rerun the repair command printed by the
launcher. Do not install Alpha-Wiki dependencies into the product environment.

## 4. Ingest First Durable Source

Put a source file under `raw/docs/`, for example `raw/docs/project-brief.md`, then run:

```text
/alpha-wiki:ingest raw/docs/project-brief.md
```

Codex:

```text
Use $alpha-wiki:ingest on raw/docs/project-brief.md.
```

Good first sources:

- project brief or PRD
- ADR
- API/OpenAPI spec
- architecture note
- support transcript with decisions or open questions

## 5. Query And Check Status

```text
/alpha-wiki:query "what is this project building?"
/alpha-wiki:status
/alpha-wiki:lint --dry-run
/alpha-wiki:review
```

Codex equivalents:

```text
Use $alpha-wiki:query for "what is this project building?"
Use $alpha-wiki:status.
Use $alpha-wiki:lint in dry-run mode.
Use $alpha-wiki:review.
```

The status report must always show a `Gap Check`. Treat gaps as work routing, not as failure noise.

## 6. Render HTML And Graph

Render a read-only HTML snapshot first:

```text
/alpha-wiki:render html
```

Optional graph exports:

```text
/alpha-wiki:render mermaid
/alpha-wiki:render dot
```

Graph rule:

- Color is node role: red service/repo, green module/domain, blue feature/flow, black document/evidence, orange contract.
- Cluster is typed relationship: `belongs_to`, `service`, `implements`, `affects`, `owned_by`, `defined_in`.
- A healthy service cluster can contain mixed colors. A color-only cluster is a modeling mistake.

The 0.8.0 GPH-001.2 export fix also groups a standalone green module root
and its typed ownership descendants. It does not require a fabricated red
service. Security-memory pages are black evidence documents. Existing Obsidian
customizations are not overwritten; deliberately merge the `path:security/`
default color rule if needed. A large single-root graph remains a single
cluster until the source documents describe real ownership subdivisions.

From 0.8.0, folder catalogs may use `_index.md`
with an explicit `title` and unique `slug` (for example `contracts-index`).
They remain linkable/exported pages, not API contracts requiring transport,
owner and consumers. Link them from the root index or another page. Broken
links, duplicate slugs and dependency rules still apply; ordinary neighboring
pages keep their entity schema. Catalogs alone do not prove useful contract
coverage or a healthy service cluster. Use vault-relative paths such as
`[[contracts/_index|Contract Catalog]]` for Obsidian; tools resolve those
catalog paths to the unique slug as well. Do not use ambiguous bare
`[[_index]]` when multiple folders have catalogs. See
[navigation rules](../references/cross-reference-rules.md#folder-navigation-unreleased-gph-0011).

## Maintain Existing Documents (0.7)

### Compact Engineering Documents (0.8.0)

Fresh project instructions and all skills carry the same writing rule for
Claude and Codex. No personal caveman skill is required. Write short technical
statements; use scope, behavior/interface, acceptance, gaps and sources where
useful. Keep required schema sections; use tables or flows only when clearer.
Link shared context and update the existing document instead of adding reports.

Compaction removes repetition, not requirements, exceptions, evidence or
unresolved questions. Review the result against the source; retain exact paths,
commands, units, diagnostics and provenance. Pass this rule into helper prompts.
Existing user instructions are preserved; merge it deliberately during upgrade.
There is no automatic prose rewriter, semantic-quality gate or measured token
saving. See references/concept.md (Engineering Writing) in the plugin source.

<a id="contract-and-schema-migration-unreleased-gov-004"></a>

### Contract And Schema Migration (0.8.0 GOV-004)

This section describes 0.8.0; 0.7.1 uses the older generated contracts.
Fresh init generates one Alpha-Wiki operating contract in `AGENTS.md`.
`.alpha-wiki/config.yaml` owns entity types, cross-reference rules and the
new explicit `wiki_dir` and `schema_evolve_mode` fields. Claude's tiny `.claude/CLAUDE.md` imports
`@../AGENTS.md`; it is a runtime adapter, not another specification. Codex
reads `AGENTS.md` natively.

For an existing project, run full bootstrap from the updated plugin environment:

```bash
uv run python -m scripts.bootstrap_cli --target /absolute/project --upgrade --dry-run
uv run python -m scripts.bootstrap_cli --target /absolute/project --upgrade
```

Review the dry-run before applying it. Existing `AGENTS.md`, root
`CLAUDE.md`, occupied import adapters, config, wiki pages, graph snapshots,
hook scripts, routing, CI and Obsidian files are preserved. Missing adapters
are created. If an existing contract lacks the Alpha-Wiki section or an occupied
adapter lacks the import, merge that section/import explicitly and run doctor.
Do not delete user Claude instructions. Managed Alpha-Wiki backends and the
isolated runtime can be updated; preserve intentional backend customizations
before upgrading. Product dependency manifests remain untouched.

Existing schema is reused, not regenerated from the selected preset. A configured
`wiki_dir` takes precedence; legacy AGENTS/CLAUDE wiki-path metadata is a
fallback when that field is absent. Pass `--wiki-dir` only for an intentional
path selection. Missing `schema_evolve_mode` means gated; explicitly merge
an intended legacy auto mode into config. Runtime-only upgrade does not perform this contract migration.
For an accepted new entity type, follow `references/schema-evolution.md`;
the helper updates config/directory/journal together on ordinary write failure,
not instruction files. YAML formatting/comments may change during that explicit
schema edit; unrelated config values are retained.

Start Claude from the project root and use `/context` to confirm that
`AGENTS.md` was imported. Claude 2.1.220 was verified this way with both fresh
and existing instructions. Starting that version from a nested directory skipped
the parent adapter's import. Do not infer loading from file existence or change
global trust settings automatically. Direct AGENTS support in newer Claude
versions is conditional; the import adapter avoids relying on it. See
[Claude memory](https://code.claude.com/docs/en/memory) and the
[compatibility matrix](platform-compatibility-matrix.md).

### Document Maintenance

This extends the optional document worker in 0.7; older 0.6.2 installations need
an upgrade. Use `document_worker --help` to inspect the available version.
It needs no server, Temporal, or model SDK. The agent prepares semantic edits;
the deterministic worker validates and applies them. Installation does not
start a background author.

Fresh software-project setup enables the canonical-document policy. Other
presets and existing configurations do not silently gain one. Runtime-only
upgrade preserves the user's config, contracts, wiki and hook routing:

```bash
uv run python -m scripts.bootstrap_cli --target /absolute/project --runtime-only --dry-run
uv run python -m scripts.bootstrap_cli --target /absolute/project --runtime-only
```

Run those from the installed plugin environment, not the target product's
environment. To opt an existing project into maintenance, deliberately merge
only the following policy into its existing config, using its actual wiki path:

```yaml
document_governance:
  enabled: true
  global_log: wiki/log.md
  canonical_files: [README.md, AGENTS.md]
  canonical_roots: [wiki]
  excluded_files: [wiki/index.md, wiki/log.md]
  excluded_roots: [wiki/graph, wiki/render, wiki/agentops]
```

Do not replace existing entity_types, cross_ref_rules or dependency_rules.
Extend the canonical set to the project's accepted specifications only.
Runtime-only upgrade replaces managed Alpha-Wiki tools and the isolated launcher;
inspect its dry-run and preserve intentional managed-tool customizations first.
Existing hook files are never overwritten or chmodded, including custom or stale
scripts. Missing bundled hooks are restored only when explicitly referenced by
project routing in `.claude/settings.json`, `.claude/settings.local.json`, or
`.codex/hooks.json`. Unconfigured scripts stay absent. Settings, schema, agent
contracts, wiki documents and product dependencies are preserved.

Recovery recognizes bundled script paths as direct commands or arguments to
`bash`/`sh` (Claude) or `python`/`python3` (Codex), with project-relative or absolute
paths and the generated project-root expressions. It does not execute commands
or guess custom wrappers. Symlinks and occupied non-file paths are preserved and
reported. Invalid routing JSON stops the upgrade before writes; fix that routing
deliberately rather than replacing it with a generated default.

Dry-run reports only actual pending writes and creates nothing. Repeating an
unchanged upgrade reports zero writes and preserves file contents, modes and
modification times. This recovery behavior is available in 0.7.1 (UPG-001);
0.7.0 does not include it. Updating a plugin does not silently upgrade existing
projects: run the explicit runtime-only command against each intended target.

Keep four layers separate: canonical specifications/contracts maintained in
place; immutable source evidence; unaccepted research/candidates; and generated
wiki/graph/HTML projections. A maintained wiki page is not a competing API spec.
Use one `belongs_to` parent where ownership exists. Dependency and evidence
links remain separate. Root documents need no invented parent.

For automatic source-drift routing, add `source_file: docs/product.md` or a
`source_files` list to the existing page's frontmatter. Paths are repository
relative; absolute in-repository legacy bindings are accepted. Missing bindings
are reported as unchecked coverage, not proof of freshness. Register new
canonical documents explicitly through ingest or `document-register` first.

From the project root, plan one existing document:

```bash
python3 .alpha-wiki/run.py -m tools.document_worker plan \
  --document wiki/specs/product.md --output .alpha-wiki/maintenance/plan.json
```

The plan pins source, document, and configuration hashes. The default batch
limit is 10. Review the actual sources and prepare
`.alpha-wiki/maintenance/edits.json` with this shape:

```json
{
  "summary": "Reflect the reviewed source change without duplicating the spec",
  "updates": [
    {"document": "wiki/specs/product.md", "text": "FULL reviewed Markdown, including existing frontmatter"}
  ]
}
```

The text above is a placeholder, not an executable replacement. Keep identity,
status, source bindings, and ownership metadata unchanged; only `date_updated`
may change. Apply an explicit contract/schema/status change outside maintenance
and log it normally. To compact redundant prose, plan with `--compact` and
explicit `--document` scope. That mode rejects growth, lost references, and
changes to protected normative sections, including nested subsections.

```bash
python3 .alpha-wiki/run.py -m tools.document_worker apply \
  --plan .alpha-wiki/maintenance/plan.json --edits .alpha-wiki/maintenance/edits.json
python3 .alpha-wiki/run.py -m tools.document_worker check
python3 .alpha-wiki/run.py -m tools.status --wiki-dir wiki
```

`apply` edits existing canonical documents only, appends one project journal
record for actual edits, refreshes graph/context/questions, and checkpoints
success. An unchanged second apply creates no new entry. A reviewed no-change
replacement can acknowledge an already accurate page without journal noise.
Partial batches leave other jobs pending. Update a source owner before its
dependent projections, then re-plan; do not update both against stale inputs.

The executing Claude/Codex agent owns the complete requested outcome: scope and
source review, bounded apply, governance/lint, status/review, and a cited query
of the changed facts. A batch checkpoint is not task acceptance. Close the
owning task only after the relevant checks pass; preserve partial progress when
source edits succeed but memory synchronization fails. A local document job
does not require a deployment, and this workflow does not ratify decisions.

For a strict read-only audit of an already prepared runtime:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 .alpha-wiki/run.py -m tools.status --wiki-dir wiki --read-only
PYTHONDONTWRITEBYTECODE=1 python3 .alpha-wiki/run.py -m tools.review --wiki-dir wiki --config .alpha-wiki/config.yaml --read-only
```

These modes compute current edges/questions without updating graph files and
reject `--out`. Do not cold-install a runtime, save a report, or run refresh/fix
commands during a zero-write audit. A prepared external Alpha-Wiki interpreter
can run target tools with `-B` when the target runtime is not installed. These
new modes require 0.7; they are not available in 0.6.2.

After an interruption, rerun the same apply with its original files. Preserve
`pending.json`; it records unfinished work. Observed concurrent changes stop
recovery without overwriting them. A crashed process may leave `worker.lock`;
verify its PID has stopped before removing that lock. Do not discard a pending
transaction as a shortcut. State is local and ignored; losing it causes a fresh
source review, not an assumption that memory is synchronized.

For regular maintenance, run status/plan after a source batch or through an
existing explicitly configured scheduler. This command does not schedule itself.
No automatic deletion, archival, owner ratification, or semantic truth resolution
is provided. A shared multi-repo overview should link to local journals, not
duplicate their contents.

## 7. Release Gate For This Plugin

Plugin maintainers should run:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m tools.release_smoke
.venv/bin/python -m tools.release_audit --root .
.venv/bin/python -m pytest
```

Expected current release-audit verdict: `READY`.

## Optional: Controlled Multi-Track Delivery

Skip this section for ordinary wiki use. For a substantial project with
independent tracks, explicitly initialize AgentOps:

```bash
python3 .alpha-wiki/run.py -m tools.orchestrate init \
  --wiki-dir wiki \
  --goal "Prepare the project for release" \
  --objective "Close verified release gaps"
```

Then use `$alpha-wiki:orchestrate`, `$alpha-wiki:backlog`,
`$alpha-wiki:handoff`, and `$alpha-wiki:release-check`. All execution state is
kept under `wiki/agentops/`; raw logs are not stored.
