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

- Follow Karpathy's LLM-Wiki shape: `raw/` is source evidence, `<wiki_dir>/` is maintained markdown memory, and `CLAUDE.md`/`AGENTS.md` expose the operating contract to Claude Code/Codex.
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
   - Detect existing `wiki/`, legacy/custom `.wiki/`, `raw/`, `CLAUDE.md`, `AGENTS.md`, `wiki/.obsidian/`, legacy root `.obsidian/`, `.claude/`, `.codex/`, `.github/workflows/`.
   - If existing project files are present, plan safe-existing mode.
   - Run or emulate `uv run python -m tools.init_audit --root <project> --wiki-dir <wiki_dir>` to enumerate durable source documents and exclude generated/runtime folders.
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
   - In a fresh Codex project, resolve the installed runtime path from the Codex Adapter section and use:
     `uv run --project <runtime_root> python -m scripts.bootstrap_cli --target <project> --project-name "<name>" --description "<purpose>" --preset <preset> --overlay <overlay> --hooks <mode> --ci`.
   - Use the same command with `--dry-run` before writing when protected project files already exist.
   - Confirm generated `CLAUDE.md` lists all active skills, including `review` and `rollup`.
   - Confirm generated `AGENTS.md` points Codex to the context brief, mutability rules, and namespaced plugin skills.
   - Confirm generated hooks honor `wiki_dir` and selected hook mode.
   - For Codex, confirm `.codex/hooks.json` and `.codex/hooks/alpha_wiki_hook.py` exist when session hooks are enabled; tell the user to review them with `/hooks`.
   - Write a raw source manifest when the user chose manifest or mixed mode.

7. Verify immediately:
   - `uv run python -m tools.init_audit --root <project> --wiki-dir <wiki_dir>`
   - `uv run python -m tools.lint --wiki-dir <wiki_dir> --config .alpha-wiki/config.yaml --dry-run`
   - `uv run python -m tools.wiki_engine rebuild-edges --wiki-dir <wiki_dir>`
   - `uv run python -m tools.wiki_engine rebuild-context-brief --wiki-dir <wiki_dir>`
   - `uv run python -m tools.wiki_engine rebuild-open-questions --wiki-dir <wiki_dir>`
   - `uv run python -m tools.doctor --project-dir <project> --wiki-dir <wiki_dir> --platform both --refresh`
   - `/alpha-wiki:status` or `tools/status.py` equivalent.

8. Teach the user the first three moves:
   - Put source material in `raw/`.
   - Run `/alpha-wiki:ingest <path>`.
   - Use `/alpha-wiki:query <question>` and `/alpha-wiki:lint --fix`.

## Files Written

- `CLAUDE.md` unless protected and preserved.
- `AGENTS.md` unless protected and preserved.
- `<wiki_dir>/index.md`, `<wiki_dir>/log.md`, entity directories, `graph/*`.
- `raw/` directories.
- `raw/docs/source-manifest.md` or a date-stamped source manifest when existing repo sources are discovered.
- `.alpha-wiki/config.yaml` and optional `.alpha-wiki/bootstrap-report.md`.
- `<wiki_dir>/.obsidian/*` if enabled.
- `.claude/hooks/*` and `.claude/settings.local.json` according to hook mode.
- `.codex/hooks.json` and `.codex/hooks/*` according to hook mode.
- `.github/workflows/wiki-*.yml` if CI is enabled.
- `tools/*.py` copied to the target project.

## Safety Gates

- Ask before `git init`.
- Ask before changing an existing `CLAUDE.md` or `AGENTS.md`.
- Do not reset existing graph artifacts on upgrade.
- Do not install hooks the user did not choose.
- Do not invent custom entity types during init unless the user selected `custom`.

## Codex Native Delegation

Keep normal init single-controller. For a large corpus or multi-repo project,
the controller may spawn read-only inventory agents, one per repository or
durable source class.

- Pin repository SHAs before fan-out when remote freshness matters.
- Inventory agents only classify sources, boundaries, candidate owners, and
  exclusions. They do not create `raw/`, wiki pages, manifests, or config.
- The controller deduplicates candidates, presents one source plan, and owns all
  bootstrap writes.
- Do not spawn agents for a small single-repo bootstrap.
- Run deterministic init audit, bootstrap, graph rebuild, lint, and doctor once
  in the controller after integration.

Follow `references/codex-subagent-orchestration.md`.

## Done Criteria

- Wiki dir exists and matches the selected path.
- `CLAUDE.md` explains mutability, page types, cross-reference rules, graph automation, and all skills.
- `AGENTS.md` gives Codex the startup reading order and shared runtime rules.
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
- `references/codex-subagent-orchestration.md`
- `assets/obsidian/COLOR-LEGEND.md`
