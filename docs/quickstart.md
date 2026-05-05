# Alpha-Wiki Quickstart

Goal: get from install to a useful, queryable markdown wiki in about 10 minutes.

## 1. Install

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
python3 scripts/install_codex.py
```

Codex commands are skills with the `$alpha-wiki-*` prefix. Claude commands use `/alpha-wiki:*`.

## 2. Bootstrap A Project

In the target project:

```text
/alpha-wiki:init
```

Codex equivalent:

```text
Use $alpha-wiki-init to bootstrap Alpha-Wiki in this project.
```

Recommended first-run choices:

- Preset: `software-project` unless the project is clearly research/product/personal.
- Wiki dir: `wiki`. Keep it visible so Obsidian can open it directly as a vault.
- Hooks: `all` for Claude, `git` or `none` when operating mainly through Codex.
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
Use $alpha-wiki-doctor with platform both and refresh enabled.
```

Expected result: no failures. Warnings are acceptable before the first ingest if they say the wiki has no durable content yet.

## 4. Ingest First Durable Source

Put a source file under `raw/docs/`, for example `raw/docs/project-brief.md`, then run:

```text
/alpha-wiki:ingest raw/docs/project-brief.md
```

Codex:

```text
Use $alpha-wiki-ingest on raw/docs/project-brief.md.
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
Use $alpha-wiki-query for "what is this project building?"
Use $alpha-wiki-status.
Use $alpha-wiki-lint in dry-run mode.
Use $alpha-wiki-review.
```

The status report must always show a `Gap Check`. Treat gaps as work routing, not as failure noise.

## 6. Read The Graph

Open the generated `wiki/` folder itself in Obsidian or render exports:

```text
/alpha-wiki:render mermaid
/alpha-wiki:render dot
/alpha-wiki:render html
```

Graph rule:

- Color is node role: red service/repo, green module/domain, blue feature/flow, black document/evidence, orange contract.
- Cluster is typed relationship: `belongs_to`, `service`, `implements`, `affects`, `owned_by`, `defined_in`.
- A healthy service cluster can contain mixed colors. A color-only cluster is a modeling mistake.

## 7. Release Gate For This Plugin

Plugin maintainers should run:

```bash
.venv/bin/python tools/release_smoke.py
.venv/bin/python tools/release_audit.py --root .
.venv/bin/python -m pytest
```

Expected current release-audit verdict: `READY`.
