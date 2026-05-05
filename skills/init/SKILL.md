---
name: init
description: "Bootstrap Alpha-Wiki project memory into a repo. Use when the user wants persistent LLM-maintained markdown memory, Karpathy-style raw/wiki/schema separation, Obsidian graph support, hooks, CI, or agent memory that compounds across sessions. Do not use for one-off documentation, a static README rewrite, or a summary that will not be maintained."
argument-hint: "[project-description]"
---

# wiki:init - bootstrap project memory

## Mission

Create the smallest safe Alpha-Wiki runtime that can grow over time: immutable raw sources, maintained markdown wiki pages, explicit schema in `CLAUDE.md`, generated graph artifacts, and automation that keeps the memory coherent. The goal is not to make a pretty docs folder. The goal is to install a disciplined memory system that future agents can trust.

## Name Contract

`init` means "establish the wiki runtime and plan the first corpus migration". It is not a bulk content import skill. During bootstrap it must inspect the repo, identify existing durable documents, propose `raw/` placement, propose wiki structure, and produce a processing plan. After bootstrap, hand actual content conversion to `/alpha-wiki:ingest`, health checks to `/alpha-wiki:status`, and graph/visual refresh to `/alpha-wiki:render`.

## Operating Principles

- Follow Karpathy's LLM-Wiki shape: `raw/` is source evidence, `<wiki_dir>/` is maintained markdown memory, `CLAUDE.md` is the operating contract.
- Prefer explicit markdown, frontmatter, wikilinks, and deterministic tools over embeddings or opaque retrieval.
- Preserve existing project files by default. Never silently overwrite `CLAUDE.md`, `README.md`, `pyproject.toml`, `.gitignore`, or `.env.example`.
- Choose `wiki/` by default, including existing codebases, so Obsidian can open the wiki folder directly as a vault.
- Make the first graph usable: `edges.jsonl`, `context_brief.md`, and `open_questions.md` must exist after bootstrap.
- Obsidian colors are path semantics, not decoration: red for top-level services/modules, green for submodules/core/ports/domains, orange for contracts, dark grey for documents, light grey for people/tasks.

## Inputs

- Project root.
- Optional user description.
- Preset: `software-project`, `research`, `product`, `personal`, `knowledge-base`, or `custom`.
- Optional overlay: `none`, `clean`, `hexagonal`, `ddd`, `ddd+clean`, `ddd+hexagonal`, `layered`.
- Hook mode: `all`, `session`, `git`, `none`.
- CI choice.
- Schema evolution mode: `gated` or `auto`.

## Workflow

1. Inspect the repo before asking questions:
   - Detect code markers: `src/`, `package.json`, `pyproject.toml`, `go.mod`, etc.
   - Detect existing `wiki/`, legacy/custom `.wiki/`, `raw/`, `CLAUDE.md`, `wiki/.obsidian/`, legacy root `.obsidian/`, `.claude/`, `.github/workflows/`.
   - If existing project files are present, plan safe-existing mode.
   - Run or emulate `tools/init_audit.py --root <project> --wiki-dir <wiki_dir>` to enumerate durable source documents and exclude generated/runtime folders.
   - Classify candidate docs into root contracts, architecture docs, ADRs, commands, skills, references, specs, API contracts, transcripts, and archives.

2. Build the initial source corpus plan:
   - Show candidate source files already present in the project.
   - Propose whether each source should be copied under `raw/docs/` or referenced by a raw manifest when copying would duplicate live repo contracts.
   - Propose the first wiki directories and page slots that will receive distilled mini-documents.
   - Batch work so the user can approve Batch 1 first instead of trying to ingest the whole repo at once.
   - Mark generated artifacts, previous wiki output, build folders, dependency folders, and raw snapshots as excluded from re-ingest.

3. Interview sequentially:
   - Project name and one-line purpose.
   - Wiki dir, defaulting to visible `wiki/` unless the user explicitly requests a custom hidden path.
   - Preset and overlay.
   - Obsidian config yes/no.
   - Hook mode: explain what each mode installs.
   - CI yes/no.
   - Schema evolution mode, with `gated` as the safer default.
   - Source migration mode: `manifest-only`, `copy-to-raw`, or `mixed`.
   - First processing scope: `Batch 1` or `all batches`.

4. Show a proposed tree before writing:
   - Raw layer.
   - Wiki layer.
   - Graph layer.
   - Schema/runtime files.
   - Hooks and CI files.
   - Protected files that will be preserved.
   - Source corpus report and first ingest queue.

5. Run dry-run when protected files exist:
   - Call bootstrap with `dry_run=True`.
   - Surface `.alpha-wiki/bootstrap-report.md` style conflicts.
   - Continue only when the user accepts preservation/merge behavior.

6. Render the runtime:
   - Call `scripts.bootstrap.bootstrap(target, config)`.
   - Confirm generated `CLAUDE.md` lists all active skills, including `review` and `rollup`.
   - Confirm generated hooks honor `wiki_dir` and selected hook mode.
   - Write a raw source manifest when the user chose manifest or mixed mode.

7. Verify immediately:
   - `tools/init_audit.py --root <project> --wiki-dir <wiki_dir>`
   - `tools/lint.py --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml --dry-run`
   - `tools/wiki_engine.py rebuild-edges --wiki-dir <wiki_dir>`
   - `tools/wiki_engine.py rebuild-context-brief --wiki-dir <wiki_dir>`
   - `tools/wiki_engine.py rebuild-open-questions --wiki-dir <wiki_dir>`
   - `tools/doctor.py --project-dir <project> --wiki-dir <wiki_dir> --platform both --refresh`
   - `/alpha-wiki:status` or `tools/status.py` equivalent.

8. Teach the user the first three moves:
   - Put source material in `raw/`.
   - Run `/alpha-wiki:ingest <path>`.
   - Use `/alpha-wiki:query <question>` and `/alpha-wiki:lint --fix`.

## Files Written

- `CLAUDE.md` unless protected and preserved.
- `<wiki_dir>/index.md`, `<wiki_dir>/log.md`, entity directories, `graph/*`.
- `raw/` directories.
- `raw/docs/source-manifest.md` or a date-stamped source manifest when existing repo sources are discovered.
- `.alpha-wiki/config.yaml` and optional `.alpha-wiki/bootstrap-report.md`.
- `<wiki_dir>/.obsidian/*` if enabled.
- `.claude/hooks/*` and `.claude/settings.local.json` according to hook mode.
- `.github/workflows/wiki-*.yml` if CI is enabled.
- `tools/*.py` copied to the target project.

## Safety Gates

- Ask before `git init`.
- Ask before changing an existing `CLAUDE.md`.
- Do not reset existing graph artifacts on upgrade.
- Do not install hooks the user did not choose.
- Do not invent custom entity types during init unless the user selected `custom`.

## Done Criteria

- Wiki dir exists and matches the selected path.
- `CLAUDE.md` explains mutability, page types, cross-reference rules, graph automation, and all skills.
- Obsidian config exists when requested and uses the color legend semantics.
- Lint runs.
- Graph files exist.
- Existing project sources were audited, and the user has a visible raw/wiki processing plan.
- Source migration mode is recorded: manifest-only, copy-to-raw, or mixed.
- Batch 1 ingest candidates are listed with target wiki slots.
- `log.md` has a bootstrap entry.
- User knows how to ingest the first source.

## References

- `references/concept.md`
- `references/presets/`
- `references/overlays/`
- `references/cross-reference-rules.md`
- `references/hooks-design.md`
- `assets/obsidian/COLOR-LEGEND.md`
