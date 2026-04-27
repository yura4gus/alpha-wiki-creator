# wiki-creator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `wiki-creator` Claude Code plugin: a 7-skill bundle that bootstraps a Karpathy/OmegaWiki-inspired LLM-maintained wiki into any target project, plus the deterministic Python engine (`tools/`) and Jinja templates (`assets/`) that drive it.

**Architecture:** Mono-plugin with 7 sibling skills (one meta `wiki-init` + 6 ops). A shared deterministic core (`tools/wiki_engine.py`, `tools/lint.py`, `tools/classify.py`) is callable from any skill and from session/git/CI hooks. Bootstrap is a Python+Jinja render pipeline: interview → resolve preset×overlay YAML → render templates → copy assets → post-render checks. The three-layer mutability model (raw / wiki / schema) is enforced by lint, not directory naming.

**Tech Stack:** Python 3.12 + uv package manager · Jinja2 templates · pytest (+ pytest-snapshot) · PyYAML · Claude Code skills format · GitHub Actions for plugin CI · Obsidian (target-side, no plugin runtime dep).

**Spec reference:** [docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md](../specs/2026-04-28-wiki-creator-skill-design.md)

---

## File Structure

Plugin tree with per-file responsibility:

```
wiki-creator/
├── plugin.json                                # Plugin manifest (name, skills list, version)
├── pyproject.toml                             # uv project: deps (jinja2, pyyaml, click), pytest config
├── README.md                                  # Plugin overview + install + usage examples
├── .gitignore                                 # .venv, __pycache__, .pytest_cache, etc.
│
├── skills/
│   ├── wiki-init/SKILL.md                     # Bootstrap interview + render
│   ├── wiki-ingest/SKILL.md                   # raw → wiki page generation
│   ├── wiki-query/SKILL.md                    # Synthesize answers from wiki
│   ├── wiki-lint/SKILL.md                     # Wraps tools/lint.py CLI
│   ├── wiki-evolve/SKILL.md                   # Add a new entity type
│   ├── wiki-spawn-agent/SKILL.md              # Generate .claude/agents/<name>.md
│   └── wiki-render/SKILL.md                   # Refresh .obsidian/ or render HTML
│
├── tools/                                     # Deterministic engine (no LLM, pure Python)
│   ├── __init__.py
│   ├── _env.py                                # Loads ~/.env and ./.env
│   ├── wiki_engine.py                         # CLI: add-edge, rebuild-context-brief, rebuild-open-questions, rebuild-edges
│   ├── lint.py                                # CLI: --fix / --suggest / --dry-run; all checks
│   ├── classify.py                            # Artifact classifier (extension first, LLM fallback stub)
│   └── _models.py                             # Dataclasses: Page, Edge, LintFinding, etc.
│
├── assets/                                    # Copied/rendered into target project at bootstrap
│   ├── claude-md.j2                           # → target/CLAUDE.md
│   ├── readme.j2                              # → target/README.md
│   ├── index-md.j2                            # → target/<wiki_dir>/index.md
│   ├── log-md.j2                              # → target/<wiki_dir>/log.md
│   ├── pyproject.j2                           # → target/pyproject.toml (target-side uv project)
│   ├── gitignore.j2                           # → target/.gitignore
│   ├── env.example                            # → target/.env.example
│   ├── frontmatter/                           # YAML frontmatter templates per entity type
│   │   ├── module.yaml
│   │   ├── component.yaml
│   │   ├── decision.yaml
│   │   ├── spec.yaml
│   │   ├── entity.yaml
│   │   ├── contract.yaml
│   │   ├── person.yaml
│   │   ├── task.yaml
│   │   ├── paper.yaml                         # research preset
│   │   ├── concept.yaml
│   │   ├── topic.yaml
│   │   ├── idea.yaml
│   │   ├── experiment.yaml
│   │   ├── claim.yaml
│   │   ├── feature.yaml                       # product preset
│   │   ├── persona.yaml
│   │   ├── flow.yaml
│   │   ├── metric.yaml
│   │   ├── project.yaml                       # personal preset
│   │   ├── area.yaml
│   │   ├── resource.yaml
│   │   ├── permanent.yaml
│   │   ├── fleeting.yaml
│   │   └── source.yaml                        # knowledge-base preset
│   ├── hooks/
│   │   ├── session-start.sh                   # `cat <wiki_dir>/graph/context_brief.md`
│   │   ├── session-end.sh                     # lint --suggest + log entry + summary
│   │   ├── pre-commit.sh                      # lint --fix; fail on 🔴
│   │   ├── pre-tool-use.sh                    # Validates frontmatter before write
│   │   ├── post-tool-use.sh                   # Debounced context_brief rebuild
│   │   └── install-hooks.sh                   # Wires hooks into .git/hooks + settings
│   ├── workflows/
│   │   ├── wiki-lint.yml                      # GitHub Actions: lint on push/PR
│   │   ├── wiki-review.yml                    # Weekly cron: /wiki-review → issue
│   │   └── wiki-rollup.yml                    # Monthly cron: /wiki-rollup → commit
│   ├── obsidian/
│   │   ├── workspace.json                     # Default layout
│   │   ├── graph.json                         # Graph view defaults
│   │   ├── community-plugins.json             # Dataview enabled
│   │   └── hotkeys.json                       # Convenience bindings
│   ├── child-skills/
│   │   └── ingest-domain.j2                   # Project-local skill scaffold (used by /wiki-evolve --generate-skill)
│   └── settings-local.j2                      # → target/.claude/settings.local.json with hook wiring
│
├── references/                                # Loaded on demand by skills
│   ├── concept.md                             # Karpathy + OmegaWiki philosophy
│   ├── classifier.md                          # Artifact taxonomy (OpenAPI/ADR/migration/...)
│   ├── cross-reference-rules.md               # Bidirectional link canon + overlay-specific
│   ├── hooks-design.md                        # Detailed hook contracts
│   ├── schema-evolution.md                    # /wiki-evolve flow detail
│   ├── presets/
│   │   ├── README.md
│   │   ├── software-project.yaml
│   │   ├── research.yaml
│   │   ├── product.yaml
│   │   ├── personal.yaml
│   │   └── knowledge-base.yaml
│   ├── overlays/
│   │   ├── README.md
│   │   ├── clean.yaml
│   │   ├── hexagonal.yaml
│   │   ├── ddd.yaml
│   │   └── layered.yaml
│   └── examples/
│       ├── omegawiki-walkthrough.md
│       └── karpathy-original.md
│
├── scripts/
│   ├── __init__.py
│   ├── bootstrap.py                           # Main render pipeline + post-render
│   ├── interview.py                           # Sequential Q&A → InterviewConfig
│   └── add_entity_type.py                     # Schema evolution helper (CLAUDE.md mutation)
│
└── tests/
    ├── __init__.py
    ├── conftest.py                            # Shared fixtures (sample-wiki, tmp_target)
    ├── unit/
    │   ├── test_wiki_engine_edges.py
    │   ├── test_wiki_engine_context_brief.py
    │   ├── test_wiki_engine_open_questions.py
    │   ├── test_lint_broken_links.py
    │   ├── test_lint_missing_reverse.py
    │   ├── test_lint_orphans.py
    │   ├── test_lint_frontmatter.py
    │   ├── test_lint_duplicate_slugs.py
    │   ├── test_lint_dependency_rules.py
    │   ├── test_lint_fix_mode.py
    │   ├── test_classify_extension.py
    │   ├── test_classify_llm_stub.py
    │   ├── test_interview_round_trip.py
    │   ├── test_interview_auto_detect.py
    │   ├── test_bootstrap_render.py
    │   ├── test_bootstrap_idempotent.py
    │   └── test_add_entity_type.py
    ├── integration/
    │   ├── test_greenfield_software_hexagonal.py
    │   ├── test_greenfield_research.py
    │   ├── test_existing_codebase_autodetect.py
    │   ├── test_upgrade_preserves_wiki_pages.py
    │   └── test_lint_clean_after_bootstrap.py
    ├── fixtures/
    │   └── sample-wiki/                       # Tiny realistic wiki for tests
    │       ├── CLAUDE.md
    │       ├── wiki/
    │       │   ├── index.md
    │       │   ├── log.md
    │       │   ├── modules/{m1,m2,m3}.md
    │       │   ├── decisions/{d1,d2}.md
    │       │   ├── contracts/rest/c1.md
    │       │   └── graph/edges.jsonl
    │       └── raw/
    └── eval/                                  # Optional, not blocking
        ├── trigger_init.yaml
        ├── trigger_ingest.yaml
        ├── trigger_query.yaml
        ├── trigger_lint.yaml
        ├── trigger_evolve.yaml
        ├── trigger_spawn_agent.yaml
        ├── trigger_render.yaml
        └── anti_triggers.yaml
```

---

## Phase 0 — Repo bootstrap

### Task 0.1: Initialize plugin scaffolding

**Files:**
- Create: `plugin.json`, `pyproject.toml`, `README.md`, `.gitignore`, `tools/__init__.py`, `scripts/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "wiki-creator"
version = "0.1.0"
description = "Bootstraps an LLM-maintained wiki into any target project"
requires-python = ">=3.12"
dependencies = [
    "jinja2>=3.1",
    "pyyaml>=6.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-snapshot>=0.9",
    "pytest-cov>=5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"

[tool.coverage.run]
source = ["tools", "scripts"]
omit = ["tests/*"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Write `plugin.json`**

```json
{
  "name": "wiki-creator",
  "version": "0.1.0",
  "description": "LLM-maintained wiki bootstrap (Karpathy + OmegaWiki inspired)",
  "skills": [
    "skills/wiki-init",
    "skills/wiki-ingest",
    "skills/wiki-query",
    "skills/wiki-lint",
    "skills/wiki-evolve",
    "skills/wiki-spawn-agent",
    "skills/wiki-render"
  ]
}
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
dist/
*.egg-info/
.DS_Store
```

- [ ] **Step 4: Write minimal `README.md`**

```markdown
# wiki-creator

Claude Code plugin that bootstraps an LLM-maintained wiki into any project.

## Install

```bash
claude plugins install wiki-creator
```

## Quick start

In your project directory:

```
/wiki-init
```

Walks you through preset/overlay choice and renders the wiki scaffolding.

See `docs/superpowers/specs/` for the design spec.
```

- [ ] **Step 5: Create empty `__init__.py` files**

```bash
touch tools/__init__.py scripts/__init__.py tests/__init__.py
```

- [ ] **Step 6: Create empty `tests/conftest.py`**

```python
"""Shared pytest fixtures for wiki-creator tests."""
```

- [ ] **Step 7: Run `uv sync --dev` to verify project bootstraps**

Run: `uv sync --dev`
Expected: creates `.venv/`, installs deps, prints `Resolved N packages`.

- [ ] **Step 8: Commit**

```bash
git add plugin.json pyproject.toml README.md .gitignore tools/ scripts/ tests/
git commit -m "feat: initial plugin scaffolding"
```

---

## Phase 1 — Data models + sample fixture

### Task 1.1: Define core dataclasses

**Files:**
- Create: `tools/_models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_models.py
from tools._models import Page, Edge, LintFinding, LintSeverity

def test_page_round_trips_frontmatter():
    p = Page(slug="auth-api", title="Auth API", path="contracts/rest/auth-api.md",
             frontmatter={"version": "v2.1.0", "status": "stable"},
             body="# Auth API\n", forward_links=["module-auth"])
    assert p.slug == "auth-api"
    assert p.frontmatter["version"] == "v2.1.0"

def test_edge_typed_relation():
    e = Edge(source="modules/auth", target="contracts/rest/auth-api", relation="provides")
    assert e.relation == "provides"

def test_lint_finding_severity():
    f = LintFinding(check="broken-link", severity=LintSeverity.ERROR,
                    file="wiki/modules/m1.md", line=12, message="broken: [[m99]]",
                    fix_available=False)
    assert f.severity == LintSeverity.ERROR
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: ImportError — `tools._models` doesn't exist.

- [ ] **Step 3: Implement `tools/_models.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class LintSeverity(str, Enum):
    ERROR = "error"      # 🔴 blocks
    WARNING = "warning"  # 🟡
    OK = "ok"            # 🟢

@dataclass
class Page:
    slug: str
    title: str
    path: str  # relative to wiki dir, e.g. "modules/auth.md"
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    forward_links: list[str] = field(default_factory=list)

@dataclass
class Edge:
    source: str   # page slug
    target: str   # page slug
    relation: str # e.g. "depends_on", "provides", "supersedes"

    def to_jsonl(self) -> str:
        import json
        return json.dumps({"source": self.source, "target": self.target, "relation": self.relation})

@dataclass
class LintFinding:
    check: str
    severity: LintSeverity
    file: str
    line: int
    message: str
    fix_available: bool = False
    suggested_fix: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/_models.py tests/unit/test_models.py
git commit -m "feat(tools): add core dataclasses (Page, Edge, LintFinding)"
```

### Task 1.2: Build sample-wiki fixture

**Files:**
- Create: `tests/fixtures/sample-wiki/CLAUDE.md`
- Create: `tests/fixtures/sample-wiki/wiki/index.md`
- Create: `tests/fixtures/sample-wiki/wiki/log.md`
- Create: `tests/fixtures/sample-wiki/wiki/modules/m1.md`, `m2.md`, `m3.md`
- Create: `tests/fixtures/sample-wiki/wiki/decisions/d1.md`, `d2.md`
- Create: `tests/fixtures/sample-wiki/wiki/contracts/rest/c1.md`
- Create: `tests/fixtures/sample-wiki/wiki/graph/edges.jsonl`
- Create: `tests/fixtures/sample-wiki/raw/.gitkeep`

- [ ] **Step 1: Write `CLAUDE.md` (minimum viable contract for tests)**

```markdown
# Sample Wiki

Preset: software-project
Overlay: none
Wiki dir: `wiki/`

## Mutability Matrix
- L1 Raw: `raw/**` — human only
- L2 Wiki: `wiki/**` excluding `wiki/graph/**` — LLM-mutable
- L3 Derived: `wiki/graph/**` — auto-generated
- L4 Schema: `CLAUDE.md`, `.claude/**` — gated

## Page Types
| Type | Dir | Required frontmatter |
|---|---|---|
| module | `modules/` | title, slug, status |
| decision | `decisions/` | title, slug, status, date |
| contract | `contracts/<transport>/` | title, slug, transport, service, status |

## Cross-Reference Rules
- module `depends_on: [[X]]` → X.dependents adds source
- contract `service: [[M]]` → M.## Provides adds contract
- decision `affects: [[X]]` → X.## Decisions adds decision

## Skills
- /wiki-ingest, /wiki-query, /wiki-lint, /wiki-evolve, /wiki-spawn-agent, /wiki-render
```

- [ ] **Step 2: Write `wiki/modules/m1.md`** (intentional valid page with forward link)

```markdown
---
title: Module One
slug: m1
status: stable
depends_on: ["[[m2]]"]
---
# Module One
Depends on [[m2]].
```

- [ ] **Step 3: Write `wiki/modules/m2.md`** (correct reverse)

```markdown
---
title: Module Two
slug: m2
status: stable
dependents: ["[[m1]]"]
---
# Module Two
```

- [ ] **Step 4: Write `wiki/modules/m3.md`** (intentional ORPHAN — no in/out links)

```markdown
---
title: Module Three
slug: m3
status: draft
---
# Module Three
```

- [ ] **Step 5: Write `wiki/decisions/d1.md`** (forward to m1, with intentional MISSING REVERSE — m1 doesn't list d1 in `## Decisions`)

```markdown
---
title: Use Postgres
slug: d1
status: accepted
date: 2026-04-01
affects: ["[[m1]]"]
---
# ADR-1: Use Postgres
```

- [ ] **Step 6: Write `wiki/decisions/d2.md`** (forward to nonexistent — BROKEN LINK)

```markdown
---
title: Use Kafka
slug: d2
status: proposed
date: 2026-04-15
affects: ["[[m99-nonexistent]]"]
---
# ADR-2: Use Kafka
```

- [ ] **Step 7: Write `wiki/contracts/rest/c1.md`**

```markdown
---
title: Auth API
slug: c1
transport: rest
service: "[[m1]]"
version: v1.0.0
status: stable
consumers: []
---
# Auth API
```

- [ ] **Step 8: Write `wiki/index.md` and `wiki/log.md`**

```markdown
<!-- wiki/index.md -->
---
project: sample
generated: 2026-04-28
---
# Index

## Modules
- [[m1]] — Module One
- [[m2]] — Module Two
- [[m3]] — Module Three

## Decisions
- [[d1]] — Use Postgres
- [[d2]] — Use Kafka

## Contracts
- [[c1]] — Auth API
```

```markdown
<!-- wiki/log.md -->
# Log

## [2026-04-28] bootstrap | sample wiki for tests
```

- [ ] **Step 9: Write `wiki/graph/edges.jsonl` (initially empty, regenerated by tests)**

```bash
mkdir -p tests/fixtures/sample-wiki/wiki/graph
: > tests/fixtures/sample-wiki/wiki/graph/edges.jsonl
mkdir -p tests/fixtures/sample-wiki/raw
touch tests/fixtures/sample-wiki/raw/.gitkeep
```

- [ ] **Step 10: Add `sample_wiki_path` fixture to conftest**

```python
# tests/conftest.py
from pathlib import Path
import pytest
import shutil

FIXTURES_ROOT = Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_wiki(tmp_path: Path) -> Path:
    """Copy of tests/fixtures/sample-wiki/ in a tmp dir; tests can mutate freely."""
    src = FIXTURES_ROOT / "sample-wiki"
    dst = tmp_path / "sample-wiki"
    shutil.copytree(src, dst)
    return dst
```

- [ ] **Step 11: Verify fixture loads**

Run: `uv run python -c "from tests.conftest import FIXTURES_ROOT; assert (FIXTURES_ROOT / 'sample-wiki' / 'CLAUDE.md').exists()"`
Expected: exits 0, no output.

- [ ] **Step 12: Commit**

```bash
git add tests/fixtures/sample-wiki/ tests/conftest.py
git commit -m "test: add sample-wiki fixture for unit tests"
```

---

## Phase 2 — Schema YAMLs + reference docs

### Task 2.1: Author preset YAMLs

**Files:**
- Create: `references/presets/software-project.yaml`, `research.yaml`, `product.yaml`, `personal.yaml`, `knowledge-base.yaml`
- Create: `references/presets/README.md`

- [ ] **Step 1: Write `software-project.yaml`**

```yaml
name: software-project
description: Default preset for software/engineering projects
entity_types:
  - name: module
    dir: modules
    frontmatter_required: [title, slug, status]
    frontmatter_optional: [depends_on, dependents, owner, description]
    sections_required: [Provides, Consumes, Decisions, "Active tasks"]
  - name: component
    dir: components
    frontmatter_required: [title, slug, parent_module]
    frontmatter_optional: [status, tests]
    sections_required: [Specs]
  - name: decision
    dir: decisions
    frontmatter_required: [title, slug, status, date]
    frontmatter_optional: [affects, supersedes, superseded_by]
    sections_required: [Context, Decision, Consequences]
  - name: spec
    dir: specs
    frontmatter_required: [title, slug, kind, status]
    frontmatter_optional: [implements, version]
    sections_required: [Entities, Requirements]
  - name: entity
    dir: entities
    frontmatter_required: [title, slug, defined_in]
    sections_required: ["Used in contracts"]
  - name: contract
    dir: contracts
    transport_subdirs: [rest, graphql, grpc, events, webhooks, rpc, data-models]
    frontmatter_required: [title, slug, transport, service, version, status]
    frontmatter_optional: [consumers, source_file, breaking_changes, date_updated]
    sections_required: ["Migration notes"]
  - name: person
    dir: people
    frontmatter_required: [title, slug, role]
    frontmatter_optional: [email, github, areas]
  - name: task
    dir: tasks
    frontmatter_required: [title, slug, status, target_module]
    frontmatter_optional: [assignee, due, blocked_by]
cross_ref_rules:
  - forward: "modules/A: depends_on: [[module-B]]"
    reverse: "modules/B: dependents adds A"
  - forward: "decisions/D: affects: [[module-A]]"
    reverse: "modules/A: ## Decisions adds D"
  - forward: "specs/S: implements: [[component-C]]"
    reverse: "components/C: ## Specs adds S"
  - forward: "tasks/T: target_module: [[module-A]]"
    reverse: "modules/A: ## Active tasks adds T"
  - forward: "entities/E: defined_in: [[spec-S]]"
    reverse: "specs/S: ## Entities adds E"
  - forward: "contracts/X: service: [[module-S]]"
    reverse: "modules/S: ## Provides adds X"
  - forward: "modules/M: consumes: [[contract-X]]"
    reverse: "contracts/X: consumers adds M"
```

- [ ] **Step 2: Write `research.yaml`**

```yaml
name: research
description: Research preset (papers, claims, experiments) — OmegaWiki-aligned
entity_types:
  - {name: paper, dir: papers, frontmatter_required: [title, slug, authors, year, source_url]}
  - {name: concept, dir: concepts, frontmatter_required: [title, slug, defined_by]}
  - {name: topic, dir: topics, frontmatter_required: [title, slug]}
  - {name: person, dir: people, frontmatter_required: [title, slug, affiliation]}
  - {name: idea, dir: ideas, frontmatter_required: [title, slug, status, originator]}
  - {name: experiment, dir: experiments, frontmatter_required: [title, slug, hypothesis, status]}
  - {name: claim, dir: claims, frontmatter_required: [title, slug, supported_by, status]}
  - {name: foundations, dir: foundations, frontmatter_required: [title, slug]}
  - {name: summary, dir: summaries, frontmatter_required: [title, slug, period]}
cross_ref_rules:
  - {forward: "claim C: supported_by: [[experiment-E]]", reverse: "experiments/E: ## Supports claims adds C"}
  - {forward: "idea I: extends: [[paper-P]]", reverse: "papers/P: ## Extended by adds I"}
  - {forward: "experiment E: tests: [[claim-C]]", reverse: "claims/C: ## Tested by adds E"}
```

- [ ] **Step 3: Write `product.yaml`**

```yaml
name: product
description: Product management preset
entity_types:
  - {name: feature, dir: features, frontmatter_required: [title, slug, status, owner]}
  - {name: persona, dir: personas, frontmatter_required: [title, slug]}
  - {name: flow, dir: flows, frontmatter_required: [title, slug, persona]}
  - {name: decision, dir: decisions, frontmatter_required: [title, slug, status, date]}
  - {name: metric, dir: metrics, frontmatter_required: [title, slug, formula]}
  - {name: experiment, dir: experiments, frontmatter_required: [title, slug, hypothesis, status]}
  - {name: competitor, dir: competitors, frontmatter_required: [title, slug, url]}
cross_ref_rules:
  - {forward: "flow F: persona: [[persona-P]]", reverse: "personas/P: ## Flows adds F"}
  - {forward: "feature F: tracks_metric: [[metric-M]]", reverse: "metrics/M: ## Features adds F"}
```

- [ ] **Step 4: Write `personal.yaml`**

```yaml
name: personal
description: PARA + Zettelkasten preset
entity_types:
  - {name: project, dir: projects, frontmatter_required: [title, slug, status, due]}
  - {name: area, dir: areas, frontmatter_required: [title, slug]}
  - {name: resource, dir: resources, frontmatter_required: [title, slug, source_url]}
  - {name: permanent, dir: permanent, frontmatter_required: [title, slug, evergreen]}
  - {name: fleeting, dir: fleeting, frontmatter_required: [title, slug, captured_at]}
  - {name: journal, dir: journals, frontmatter_required: [title, slug, date]}
  - {name: goal, dir: goals, frontmatter_required: [title, slug, horizon]}
  - {name: archive, dir: archive, frontmatter_required: [title, slug, archived_at]}
cross_ref_rules:
  - {forward: "project P: belongs_to: [[area-A]]", reverse: "areas/A: ## Projects adds P"}
  - {forward: "permanent N: distilled_from: [[fleeting-F]]", reverse: "fleeting/F: ## Distilled into adds N"}
```

- [ ] **Step 5: Write `knowledge-base.yaml`**

```yaml
name: knowledge-base
description: Minimal universal preset
entity_types:
  - {name: entity, dir: entities, frontmatter_required: [title, slug]}
  - {name: concept, dir: concepts, frontmatter_required: [title, slug]}
  - {name: decision, dir: decisions, frontmatter_required: [title, slug, status, date]}
  - {name: source, dir: sources, frontmatter_required: [title, slug, url]}
  - {name: summary, dir: summaries, frontmatter_required: [title, slug]}
cross_ref_rules:
  - {forward: "entity E: derived_from: [[source-S]]", reverse: "sources/S: ## Derived adds E"}
```

- [ ] **Step 6: Write `references/presets/README.md`**

```markdown
# Presets

Each preset is a YAML file declaring entity types, their required frontmatter and sections,
and cross-reference rules. `bootstrap.py` reads the chosen preset, merges it with an overlay
(if any), and renders templates.

## Available presets

- `software-project.yaml` — default for engineering projects (8 entity types)
- `research.yaml` — OmegaWiki-aligned (9 entity types)
- `product.yaml` — product management
- `personal.yaml` — PARA + Zettelkasten
- `knowledge-base.yaml` — minimal universal (5 entity types)

## Custom

Preset = "custom" triggers interactive entity-type interview in `scripts/interview.py`,
producing an in-memory preset that gets persisted as `target/.wiki-creator/preset.yaml`.

## Schema

```yaml
name: <preset-name>
description: <one-liner>
entity_types:
  - name: <type>
    dir: <dir-relative-to-wiki>
    frontmatter_required: [<field>, ...]
    frontmatter_optional: [<field>, ...]
    sections_required: [<heading>, ...]
cross_ref_rules:
  - forward: "<source-pattern>"
    reverse: "<reverse-action>"
```
```

- [ ] **Step 7: Validate YAMLs parse**

```bash
uv run python -c "import yaml, glob; [yaml.safe_load(open(p)) for p in glob.glob('references/presets/*.yaml')]; print('ok')"
```
Expected: `ok`.

- [ ] **Step 8: Commit**

```bash
git add references/presets/
git commit -m "feat(presets): author 5 preset YAML schemas"
```

### Task 2.2: Author overlay YAMLs

**Files:**
- Create: `references/overlays/clean.yaml`, `hexagonal.yaml`, `ddd.yaml`, `layered.yaml`
- Create: `references/overlays/README.md`

- [ ] **Step 1: Write `hexagonal.yaml`**

```yaml
name: hexagonal
description: Ports & Adapters overlay (replaces software-project's flat layout)
applies_to: [software-project]
top_level_dirs:
  - core/entities
  - core/value-objects
  - core/aggregates
  - core/domain-events
  - ports/inbound
  - ports/outbound
  - adapters/inbound
  - adapters/outbound
  - application
  - contracts
  - decisions
  - people
  - tasks
dependency_rules:
  - {from: "core/", forbidden_to: ["adapters/", "application/", "infrastructure/"]}
  - {from: "ports/", forbidden_to: ["adapters/", "application/"]}
  - {from: "adapters/inbound/<X>/", required_to: ["ports/inbound/<X>"]}
  - {from: "adapters/outbound/<X>/", required_to: ["ports/outbound/<X>"]}
extra_cross_ref_rules: []
```

- [ ] **Step 2: Write `clean.yaml`**

```yaml
name: clean
description: Clean Architecture (Uncle Bob)
applies_to: [software-project]
top_level_dirs:
  - domains
  - use-cases
  - adapters/controllers
  - adapters/presenters
  - adapters/gateways
  - infrastructure
  - contracts
  - decisions
  - modules
  - people
  - tasks
dependency_rules:
  - {from: "domains/", forbidden_to: ["adapters/", "infrastructure/", "use-cases/"]}
  - {from: "use-cases/", forbidden_to: ["adapters/", "infrastructure/"]}
  - {from: "adapters/", forbidden_to: ["infrastructure/"]}
extra_cross_ref_rules: []
```

- [ ] **Step 3: Write `ddd.yaml`**

```yaml
name: ddd
description: Domain-Driven Design — bounded contexts (combinable with clean or hexagonal)
applies_to: [software-project]
combinable_with: [clean, hexagonal]
top_level_dirs:
  - bounded-contexts
  - shared-kernel
  - context-map.md
  - contracts
  - decisions
  - people
  - tasks
sub_structure_per_bc: inherit_outer_overlay
dependency_rules:
  - {from: "shared-kernel/", forbidden_to: ["bounded-contexts/"]}
extra_cross_ref_rules:
  - {forward: "context-map: A → B", reverse: "bounded-contexts/A: ## Downstream adds B; bounded-contexts/B: ## Upstream adds A"}
```

- [ ] **Step 4: Write `layered.yaml`**

```yaml
name: layered
description: Classic 3-tier (presentation / business-logic / data-access)
applies_to: [software-project]
top_level_dirs:
  - presentation
  - business-logic
  - data-access
  - contracts
  - decisions
  - modules
  - people
  - tasks
dependency_rules:
  - {from: "data-access/", forbidden_to: ["presentation/", "business-logic/"]}
  - {from: "business-logic/", forbidden_to: ["presentation/"]}
extra_cross_ref_rules: []
```

- [ ] **Step 5: Write `references/overlays/README.md`**

```markdown
# Architectural overlays

Overlays modify the macro-structure of `<wiki_dir>/` for the `software-project` preset.
They also add **dependency rules** that lint enforces (🟡 warnings).

## Available

- `none` (default) — flat preset layout, no dependency rules
- `clean.yaml` — Uncle Bob's Clean Architecture
- `hexagonal.yaml` — Ports & Adapters
- `ddd.yaml` — Domain-Driven Design (combinable: ddd+clean, ddd+hexagonal)
- `layered.yaml` — classic 3-tier

## Combinability

Only `ddd` is combinable. `clean+hexagonal` is forbidden (overlapping intent).
`bootstrap.py` validates this at config-resolution time.

## Schema

```yaml
name: <overlay-name>
description: <one-liner>
applies_to: [<preset>, ...]
combinable_with: [<overlay>, ...]    # optional
top_level_dirs: [<path>, ...]
dependency_rules:
  - {from: <pattern>, forbidden_to: [<pattern>, ...]}
  - {from: <pattern>, required_to: [<pattern>, ...]}
extra_cross_ref_rules: [...]
```
```

- [ ] **Step 6: Validate YAMLs parse**

```bash
uv run python -c "import yaml, glob; [yaml.safe_load(open(p)) for p in glob.glob('references/overlays/*.yaml')]; print('ok')"
```
Expected: `ok`.

- [ ] **Step 7: Commit**

```bash
git add references/overlays/
git commit -m "feat(overlays): author 4 architectural overlay YAMLs"
```

### Task 2.3: Author reference markdown docs

**Files:**
- Create: `references/concept.md`, `references/classifier.md`, `references/cross-reference-rules.md`, `references/hooks-design.md`, `references/schema-evolution.md`
- Create: `references/examples/karpathy-original.md`, `references/examples/omegawiki-walkthrough.md`

- [ ] **Step 1: Write `concept.md` (Karpathy + OmegaWiki philosophy summary)**

```markdown
# Concept

## Karpathy LLM Wiki (origin)

Three layers, three operations, two service files.

- **Raw** — immutable sources (read-only after capture)
- **Wiki** — LLM-generated markdown with cross-links
- **Schema** — `CLAUDE.md`, the runtime contract for the agent

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

## wiki-creator additions

- **Three-layer model = mutability contracts**, not folders
- **Domain presets** (software-project default + 4 alternatives + custom)
- **Architectural overlays** (clean, hexagonal, ddd, layered)
- **Schema evolution** through ingest (new artifact type → CLAUDE.md mutation)
- **Session-end automation** (lint + log + context_brief rebuild)
- **Sibling skill `wiki-spawn-agent`** for adding subagents

The full design spec lives at `docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`.
```

- [ ] **Step 2: Write `classifier.md`**

```markdown
# Artifact classifier

`tools/classify.py` decides which entity-type slot a raw file maps to.

## Strategy

1. **Extension + filename heuristics** (deterministic, no LLM)
2. **Frontmatter sniff** (if `.md` with YAML frontmatter)
3. **MIME inspection** (for ambiguous binaries)
4. **LLM fallback** (only if deterministic checks return None) — calls Claude with the file head

## Recognized classes (out of the box)

| Class | Detect by | Default slot (software-project) |
|---|---|---|
| OpenAPI spec | `*.yaml/*.json` w/ `openapi:` key | `contracts/rest/` |
| GraphQL schema | `*.graphql`, `*.gql` | `contracts/graphql/` |
| protobuf | `*.proto` | `contracts/grpc/` |
| AsyncAPI | `*.yaml/*.json` w/ `asyncapi:` key | `contracts/events/` |
| ADR | `*.md` w/ frontmatter `kind: adr` or filename `adr-*` | `decisions/` |
| C4/PlantUML | `*.puml`, `*.mermaid`, `*.dot` | `specs/` (with `kind: diagram`) |
| Source code | `*.py`, `*.ts`, `*.go`, ... | (skipped — not ingested) |
| Migration | `*.sql` w/ `CREATE TABLE` or filename `*_migration.sql` | (no default slot — triggers schema-evolve) |
| Terraform | `*.tf` | (no default slot — triggers schema-evolve) |
| K8s manifest | `*.yaml` w/ `apiVersion:` and `kind:` | (no default slot — triggers schema-evolve) |
| PRD/RFC | `*.md` w/ frontmatter `kind: prd` or filename `PRD*` / `RFC*` | `specs/` |
| Threat model | `*.md` w/ frontmatter `kind: threat-model` | `specs/` (with `kind: security`) |
| Runbook | `*.md` w/ frontmatter `kind: runbook` | `specs/` (with `kind: ops`) |
| Postmortem | `*.md` w/ filename `postmortem-*` | `decisions/` (with `kind: postmortem`) |
| Meeting transcript | `*.md`/`*.txt` w/ frontmatter `kind: transcript` or under `raw/transcripts/` | (extract → ingest as multiple pages) |
| Slack export | `.json` from Slack export | (extract → multiple pages) |
| Test plan | `*.md` w/ frontmatter `kind: test-plan` | `specs/` |
| Postman collection | `*.postman_collection.json` | `contracts/rest/` (with `kind: collection`) |
| SQL DDL | `*.sql` w/ `CREATE TABLE` | (triggers schema-evolve to `data/schema/`) |
| JSON Schema | `*.schema.json` | `contracts/data-models/` |
| Avro | `*.avsc` | `contracts/data-models/` |

Other file types fall through to schema-evolve flow.
```

- [ ] **Step 3: Write `cross-reference-rules.md`**

```markdown
# Cross-reference rules

Bidirectional link enforcement is the heart of OmegaWiki-style wikis.
Every forward link must have a reverse — `tools/lint.py` checks this.

## Canonical rules per preset

Defined in YAML under `references/presets/<preset>.yaml` → `cross_ref_rules`.

## Overlay-specific rules

Defined in YAML under `references/overlays/<overlay>.yaml` → `extra_cross_ref_rules`.

## Enforcement

1. **Write time** (`pre-tool-use` hook): validates frontmatter; if forward link added, calls `tools/wiki_engine.py add-edge --bidirectional` to write reverse.
2. **Lint time** (`tools/lint.py --check missing-reverse`): scans whole wiki, reports/fixes missing reverses.
3. **Edge graph** (`wiki_engine.py rebuild-edges`): regenerates `graph/edges.jsonl` from frontmatter — never hand-authored.

## Stub creation

If a forward link points to a nonexistent page, `pre-tool-use` creates a stub:

```markdown
---
title: <inferred-from-link>
slug: <link-target>
status: stub
---
# <inferred-title>
TODO: fill via /wiki-ingest
```

And appends `log.md`:
```
## [date] stub | <slug> | created from forward link in <source-file>
```
```

- [ ] **Step 4: Write `hooks-design.md`**

```markdown
# Hooks design

## L1 — Claude Code session hooks

Wired in `target/.claude/settings.local.json`. Scripts in `target/.claude/hooks/`.

| Hook | Matcher | Script | Purpose |
|---|---|---|---|
| `session-start` | always | `hooks/session-start.sh` | Loads `<wiki_dir>/graph/context_brief.md` into agent context |
| `pre-tool-use` | Write\|Edit on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/pre-tool-use.sh` | Validates frontmatter + reverse-link |
| `post-tool-use` | Write on `<wiki_dir>/**` (excluding `graph/**`) | `hooks/post-tool-use.sh` | Debounced (5s) `wiki_engine.py rebuild-context-brief` |
| `session-end` | always | `hooks/session-end.sh` | `lint --suggest`, append log entry, echo summary |

## L2 — Git hooks

Wired by `assets/install-hooks.sh` into `.git/hooks/`.

- **pre-commit**: `tools/lint.py --fix`; fail if 🔴 remain after auto-fix; stage auto-fixes.
- **post-commit**: if `<wiki_dir>/**` touched → `wiki_engine.py rebuild-edges`.

## L3 — CI (GitHub Actions)

In `target/.github/workflows/`:

- **wiki-lint.yml** — `uv run python tools/lint.py` on push/PR; fails PR if 🔴.
- **wiki-review.yml** — weekly cron, headless `claude -p "/wiki-review"` → publishes issue.
- **wiki-rollup.yml** — monthly cron, headless `claude -p "/wiki-rollup month"` → commits rollup.

## Debouncing

`post-tool-use` rebuild is debounced 5s using a lockfile `<wiki_dir>/graph/.rebuild.lock` with timestamp.
If a rebuild is requested within 5s of the previous, the second call exits silently.
```

- [ ] **Step 5: Write `schema-evolution.md`**

```markdown
# Schema evolution

`/wiki-ingest` may encounter artifacts with no matching slot in the current schema.

## Modes

- **gated** (default): pause, propose options, require user confirmation
- **auto**: pick best default and proceed (append `[schema-change]` log entry, allow rollback)

## Options proposed (gated mode)

For an artifact of class `X` with no slot:

1. **New top-level entity type** — e.g. `data/migrations/`
2. **Sub-folder under existing layer** — e.g. `infrastructure/migrations/` (if hexagonal/clean)
3. **Section append in related page** — e.g. `## Migrations` on `entities/users.md`

User picks; `/wiki-evolve` runs.

## /wiki-evolve actions

```
1. Update CLAUDE.md
   - "Page Types" table: add row
   - "Frontmatter Templates": append YAML
   - "Cross-Reference Rules": add rules
2. Create assets/frontmatter/<type>.yaml in target
3. mkdir <wiki_dir>/<dir>/
4. Append <wiki_dir>/log.md:
   ## [YYYY-MM-DD] schema-change | added type: <type> (<path>) | trigger: <trigger>
5. git add . && git commit -m "[schema-change] add type: <type>"
6. graph/edges.jsonl: untouched (no edges yet)
```

## Project-local skill (optional)

`/wiki-evolve <type> --generate-skill` renders `assets/child-skills/ingest-domain.j2`
into `target/.claude/skills/wiki-ingest-<type>/SKILL.md`. The child skill is a thin
wrapper that pre-classifies into this slot. It lives only in the target.
```

- [ ] **Step 6: Write `examples/karpathy-original.md`**

```markdown
# Karpathy LLM Wiki — original gist (excerpt)

Source: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Three layers

- `raw/` — immutable inputs (papers, transcripts, web saves)
- `wiki/` — LLM-curated markdown with `[[wiki-links]]`
- `CLAUDE.md` — runtime instructions for the agent

## Three operations

- `ingest` — agent reads raw → produces or updates wiki pages
- `query` — agent reads index.md and relevant pages → answers
- `lint` — structural sanity check (broken links, missing pages)

## Two service files

- `wiki/index.md` — catalog (table of contents, YAML-style)
- `wiki/log.md` — append-only diary of operations

## Karpathy's claim

For most projects, this is enough. RAG/embeddings introduce opacity; markdown + a good
index reads with no surprises. Vector search becomes useful only past ~100 sources.

## What we keep

All of it. wiki-creator preserves Karpathy's spirit while adding production-grade
extensions from OmegaWiki (typed entities, edges, bidirectional enforcement).
```

- [ ] **Step 7: Write `examples/omegawiki-walkthrough.md`**

```markdown
# OmegaWiki walkthrough — what we adopted

Source: https://github.com/skyllwt/OmegaWiki

## Architecture preserved

- Three-layer raw/wiki/schema split
- index.md + log.md service files
- LLM-mediated ingest/query/lint

## Production extensions adopted

### Typed entities

Each page has `kind:` in frontmatter (paper, concept, claim, experiment, ...).
Required frontmatter fields per type. Required sections per type. Lint enforces.

### Typed edge graph

`wiki/graph/edges.jsonl` — one edge per line:

```json
{"source": "claim-fast-llms", "target": "experiment-batched-decoding", "relation": "supported_by"}
```

Relations: `extends`, `contradicts`, `supports`, `inspired_by`, `tested_by`, `invalidates`,
`supersedes`, `addresses_gap`, `derived_from`.

### Bidirectional enforcement

Forward link in frontmatter → automatic reverse link write on target page.
Lint flags missing reverses (🟡, auto-fixable).

### Auto-generated graph artifacts

`graph/context_brief.md` — ≤8000 char compressed context (active claims + open questions + recent log).
`graph/open_questions.md` — extracted from frontmatter `open_question:` fields and `## Open questions` sections.

Both regenerated by `tools/wiki_engine.py rebuild-*`. Never hand-edit.

### Lint modes

`--fix` writes safe corrections; `--suggest` prints recommendations; `--dry-run` reports without changes.

### CI cron

OmegaWiki has `daily-arxiv` (paper ingestion). We have `wiki-review` (weekly) and `wiki-rollup` (monthly).

### Anti-repetition memory

Failed ideas tracked with `failure_reason` so the agent doesn't revisit dead ends.
We expose this via the `idea` entity type's `status: failed` + `failure_reason:` frontmatter.
```

- [ ] **Step 8: Commit**

```bash
git add references/concept.md references/classifier.md references/cross-reference-rules.md references/hooks-design.md references/schema-evolution.md references/examples/
git commit -m "docs(references): author concept + classifier + cross-ref + hooks + evolution + examples"
```

---

## Phase 3 — Deterministic engine (`tools/`)

### Task 3.1: `tools/_env.py` — env loading

**Files:**
- Create: `tools/_env.py`
- Test: `tests/unit/test_env.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_env.py
from pathlib import Path
import os
from tools._env import load_env

def test_load_env_reads_local_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO=bar\nBAZ=qux\n")
    load_env()
    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux"

def test_load_env_local_overrides_home(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("FOO=home\n")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".env").write_text("FOO=local\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(proj)
    load_env()
    assert os.environ["FOO"] == "local"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_env.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `tools/_env.py`**

```python
"""Loads ~/.env then ./.env (local overrides home)."""
from __future__ import annotations
import os
from pathlib import Path

def _parse_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out

def load_env() -> None:
    home_env = _parse_dotenv(Path.home() / ".env")
    local_env = _parse_dotenv(Path.cwd() / ".env")
    for k, v in {**home_env, **local_env}.items():
        os.environ.setdefault(k, v) if k in os.environ else os.environ.update({k: v})
        os.environ[k] = v  # local overrides
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_env.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/_env.py tests/unit/test_env.py
git commit -m "feat(tools): add _env.py for ~/.env and ./.env loading"
```

### Task 3.2: `wiki_engine.py` — page parsing helpers

**Files:**
- Create: `tools/wiki_engine.py` (initial: parsing only)
- Test: `tests/unit/test_wiki_engine_parsing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_wiki_engine_parsing.py
from pathlib import Path
from tools.wiki_engine import parse_page, extract_wikilinks, scan_wiki

def test_parse_page_splits_frontmatter_and_body(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("---\ntitle: X\nslug: x\n---\n# X\nbody [[y]]\n")
    page = parse_page(p)
    assert page.frontmatter["title"] == "X"
    assert page.slug == "x"
    assert "body [[y]]" in page.body

def test_extract_wikilinks_finds_all():
    body = "see [[a]] and [[b/c]] not [[d]] yet [[e|alias]]"
    assert sorted(extract_wikilinks(body)) == ["a", "b/c", "d", "e"]

def test_scan_wiki_returns_pages(sample_wiki: Path):
    pages = scan_wiki(sample_wiki / "wiki")
    slugs = sorted(p.slug for p in pages)
    assert "m1" in slugs
    assert "d2" in slugs
    assert "c1" in slugs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_wiki_engine_parsing.py -v`
Expected: ImportError on `parse_page` etc.

- [ ] **Step 3: Implement parsing helpers in `tools/wiki_engine.py`**

```python
from __future__ import annotations
import re
from pathlib import Path
import yaml
from tools._models import Page, Edge

WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

def parse_page(path: Path) -> Page:
    text = path.read_text()
    fm: dict = {}
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        fm = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    slug = fm.get("slug") or path.stem
    title = fm.get("title") or slug
    forward = sorted(set(extract_wikilinks(body) + _wikilinks_from_frontmatter(fm)))
    return Page(slug=slug, title=title, path=str(path),
                frontmatter=fm, body=body, forward_links=forward)

def extract_wikilinks(text: str) -> list[str]:
    return WIKILINK_RE.findall(text)

def _wikilinks_from_frontmatter(fm: dict) -> list[str]:
    out: list[str] = []
    def visit(v):
        if isinstance(v, str):
            out.extend(WIKILINK_RE.findall(v))
        elif isinstance(v, list):
            for x in v: visit(x)
        elif isinstance(v, dict):
            for x in v.values(): visit(x)
    visit(fm)
    return out

def scan_wiki(wiki_dir: Path) -> list[Page]:
    return [parse_page(p) for p in wiki_dir.rglob("*.md")
            if "graph" not in p.parts and p.name not in ("index.md", "log.md")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_wiki_engine_parsing.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/wiki_engine.py tests/unit/test_wiki_engine_parsing.py
git commit -m "feat(wiki_engine): add page parsing + wikilink extraction"
```

### Task 3.3: `wiki_engine.py` — edges (add, rebuild, jsonl)

**Files:**
- Modify: `tools/wiki_engine.py:end`
- Test: `tests/unit/test_wiki_engine_edges.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_wiki_engine_edges.py
from pathlib import Path
from tools.wiki_engine import rebuild_edges, add_edge, read_edges

def test_rebuild_edges_writes_jsonl_from_frontmatter(sample_wiki: Path):
    rebuild_edges(sample_wiki / "wiki")
    edges = read_edges(sample_wiki / "wiki" / "graph" / "edges.jsonl")
    relations = {(e.source, e.target, e.relation) for e in edges}
    assert ("m1", "m2", "depends_on") in relations
    assert ("d1", "m1", "affects") in relations
    assert ("c1", "m1", "service") in relations

def test_add_edge_bidirectional_writes_reverse(sample_wiki: Path):
    """Forward `depends_on` from m3 → m2 must add m3 to m2.dependents."""
    add_edge(sample_wiki / "wiki", source="m3", target="m2", relation="depends_on", bidirectional=True)
    m2_text = (sample_wiki / "wiki" / "modules" / "m2.md").read_text()
    assert "m3" in m2_text  # appears in dependents
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_wiki_engine_edges.py -v`
Expected: ImportError on `rebuild_edges`.

- [ ] **Step 3: Implement edges API in `tools/wiki_engine.py`**

```python
# Append to tools/wiki_engine.py
import json

# Frontmatter keys that produce typed edges (relation = key name)
EDGE_KEYS = {
    "depends_on", "dependents", "affects", "implements", "consumes",
    "service", "consumers", "supersedes", "superseded_by", "supports",
    "extends", "tested_by", "contradicts", "inspired_by", "addresses_gap",
    "derived_from", "invalidates", "target_module", "defined_in",
    "belongs_to", "distilled_from", "tracks_metric", "persona",
}

def rebuild_edges(wiki_dir: Path) -> list[Edge]:
    edges: list[Edge] = []
    for page in scan_wiki(wiki_dir):
        for key, value in page.frontmatter.items():
            if key not in EDGE_KEYS:
                continue
            for target in _coerce_targets(value):
                edges.append(Edge(source=page.slug, target=target, relation=key))
    out_path = wiki_dir / "graph" / "edges.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(e.to_jsonl() for e in edges) + ("\n" if edges else ""))
    return edges

def read_edges(path: Path) -> list[Edge]:
    if not path.exists():
        return []
    return [Edge(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]

def _coerce_targets(value) -> list[str]:
    if isinstance(value, str):
        return [s for s in WIKILINK_RE.findall(value)] or ([value] if not value.startswith("[") else [])
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            out.extend(_coerce_targets(v))
        return out
    return []

def add_edge(wiki_dir: Path, source: str, target: str, relation: str, bidirectional: bool = False) -> None:
    """Adds a forward link to source's frontmatter; if bidirectional, also writes reverse on target."""
    src_page = _find_page(wiki_dir, source)
    if src_page is None:
        raise FileNotFoundError(f"page not found: {source}")
    _add_to_frontmatter_list(src_page, relation, f"[[{target}]]")
    if bidirectional:
        reverse_relation = _reverse_of(relation)
        if reverse_relation is None:
            return
        tgt_page = _find_page(wiki_dir, target)
        if tgt_page is None:
            _create_stub(wiki_dir, target)
            tgt_page = _find_page(wiki_dir, target)
        _add_to_frontmatter_list(tgt_page, reverse_relation, f"[[{source}]]")

REVERSE_OF = {
    "depends_on": "dependents",
    "dependents": "depends_on",
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
    "service": "_provides",  # special: writes section, not frontmatter
    "consumes": "consumers",
    "consumers": "consumes",
    "implements": "_specs",  # special: writes section
}

def _reverse_of(relation: str) -> str | None:
    return REVERSE_OF.get(relation)

def _find_page(wiki_dir: Path, slug: str) -> Path | None:
    for p in wiki_dir.rglob("*.md"):
        if "graph" in p.parts:
            continue
        page = parse_page(p)
        if page.slug == slug:
            return p
    return None

def _add_to_frontmatter_list(page_path: Path, key: str, value: str) -> None:
    text = page_path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        # No frontmatter — add minimal
        new = f"---\n{key}:\n  - {value}\n---\n" + text
        page_path.write_text(new)
        return
    fm = yaml.safe_load(m.group(1)) or {}
    existing = fm.get(key, [])
    if isinstance(existing, str):
        existing = [existing]
    if value not in existing:
        existing.append(value)
    fm[key] = existing
    new_fm = yaml.safe_dump(fm, sort_keys=False).rstrip()
    page_path.write_text(f"---\n{new_fm}\n---\n" + text[m.end():])

def _create_stub(wiki_dir: Path, slug: str) -> None:
    stub_dir = wiki_dir / "_stubs"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_path = stub_dir / f"{slug}.md"
    stub_path.write_text(f"---\ntitle: {slug}\nslug: {slug}\nstatus: stub\n---\n# {slug}\nTODO: fill via /wiki-ingest\n")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_wiki_engine_edges.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/wiki_engine.py tests/unit/test_wiki_engine_edges.py
git commit -m "feat(wiki_engine): rebuild_edges + add_edge with bidirectional reverses"
```

### Task 3.4: `wiki_engine.py` — context_brief + open_questions

**Files:**
- Modify: `tools/wiki_engine.py:end`
- Test: `tests/unit/test_wiki_engine_context_brief.py`, `tests/unit/test_wiki_engine_open_questions.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_wiki_engine_context_brief.py
from pathlib import Path
from tools.wiki_engine import rebuild_context_brief

def test_context_brief_under_8000_chars(sample_wiki: Path):
    out = rebuild_context_brief(sample_wiki / "wiki")
    assert len(out.read_text()) <= 8000

def test_context_brief_includes_recent_log(sample_wiki: Path):
    out = rebuild_context_brief(sample_wiki / "wiki")
    text = out.read_text()
    assert "bootstrap | sample wiki for tests" in text or "Recent log" in text
```

```python
# tests/unit/test_wiki_engine_open_questions.py
from pathlib import Path
from tools.wiki_engine import rebuild_open_questions

def test_open_questions_extracted(sample_wiki: Path):
    # Add an explicit open question to one page
    p = sample_wiki / "wiki" / "modules" / "m1.md"
    p.write_text(p.read_text() + "\n## Open questions\n- Should we shard?\n- Auth strategy?\n")
    out = rebuild_open_questions(sample_wiki / "wiki")
    text = out.read_text()
    assert "Should we shard?" in text
    assert "Auth strategy?" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_wiki_engine_context_brief.py tests/unit/test_wiki_engine_open_questions.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement in `tools/wiki_engine.py`**

```python
# Append to tools/wiki_engine.py

CONTEXT_BRIEF_LIMIT = 8000

def rebuild_context_brief(wiki_dir: Path) -> Path:
    pages = scan_wiki(wiki_dir)
    active_claims = [p for p in pages if p.frontmatter.get("status") in ("active", "stable", "accepted")]
    log_path = wiki_dir / "log.md"
    recent_log = ""
    if log_path.exists():
        recent_log = "\n".join(log_path.read_text().splitlines()[-10:])
    open_q = _collect_open_questions(pages)

    parts = [
        "# Context brief (auto-generated)\n",
        f"## Recent log\n{recent_log}\n",
        f"## Active pages ({len(active_claims)})\n" +
        "\n".join(f"- [[{p.slug}]] — {p.title}" for p in active_claims[:50]),
        f"## Open questions\n{open_q}",
    ]
    out_text = "\n\n".join(parts)
    if len(out_text) > CONTEXT_BRIEF_LIMIT:
        out_text = out_text[:CONTEXT_BRIEF_LIMIT - 100] + "\n\n... (truncated)\n"
    out_path = wiki_dir / "graph" / "context_brief.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text)
    return out_path

def rebuild_open_questions(wiki_dir: Path) -> Path:
    pages = scan_wiki(wiki_dir)
    text = "# Open questions (auto-generated)\n\n" + _collect_open_questions(pages)
    out_path = wiki_dir / "graph" / "open_questions.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    return out_path

OPEN_Q_SECTION_RE = re.compile(r"^## Open questions\s*\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)

def _collect_open_questions(pages: list[Page]) -> str:
    lines: list[str] = []
    for p in pages:
        m = OPEN_Q_SECTION_RE.search(p.body)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip()
                if line.startswith("- ") and len(line) > 2:
                    lines.append(f"- ({p.slug}) {line[2:]}")
        if "open_question" in p.frontmatter:
            v = p.frontmatter["open_question"]
            for q in (v if isinstance(v, list) else [v]):
                lines.append(f"- ({p.slug}) {q}")
    return "\n".join(lines) if lines else "_(none)_\n"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_wiki_engine_context_brief.py tests/unit/test_wiki_engine_open_questions.py -v`
Expected: 3 passed total.

- [ ] **Step 5: Commit**

```bash
git add tools/wiki_engine.py tests/unit/test_wiki_engine_context_brief.py tests/unit/test_wiki_engine_open_questions.py
git commit -m "feat(wiki_engine): rebuild_context_brief + rebuild_open_questions"
```

### Task 3.5: `wiki_engine.py` — CLI entry point (click)

**Files:**
- Modify: `tools/wiki_engine.py:end`
- Test: `tests/unit/test_wiki_engine_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_wiki_engine_cli.py
from pathlib import Path
from click.testing import CliRunner
from tools.wiki_engine import cli

def test_cli_rebuild_edges(sample_wiki: Path):
    r = CliRunner().invoke(cli, ["rebuild-edges", "--wiki-dir", str(sample_wiki / "wiki")])
    assert r.exit_code == 0, r.output
    edges_path = sample_wiki / "wiki" / "graph" / "edges.jsonl"
    assert edges_path.read_text().strip(), "edges.jsonl should be non-empty"

def test_cli_add_edge(sample_wiki: Path):
    r = CliRunner().invoke(cli, [
        "add-edge", "--wiki-dir", str(sample_wiki / "wiki"),
        "--source", "m3", "--target", "m1", "--relation", "depends_on", "--bidirectional",
    ])
    assert r.exit_code == 0, r.output
    m1 = (sample_wiki / "wiki" / "modules" / "m1.md").read_text()
    assert "m3" in m1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_wiki_engine_cli.py -v`
Expected: ImportError on `cli`.

- [ ] **Step 3: Implement `cli` in `tools/wiki_engine.py`**

```python
# Append to tools/wiki_engine.py
import click

@click.group()
def cli():
    """wiki-creator deterministic engine."""

@cli.command("rebuild-edges")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def cli_rebuild_edges(wiki_dir: Path):
    edges = rebuild_edges(wiki_dir)
    click.echo(f"wrote {len(edges)} edges to {wiki_dir / 'graph' / 'edges.jsonl'}")

@cli.command("rebuild-context-brief")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def cli_rebuild_context_brief(wiki_dir: Path):
    out = rebuild_context_brief(wiki_dir)
    click.echo(f"wrote {out}")

@cli.command("rebuild-open-questions")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def cli_rebuild_open_questions(wiki_dir: Path):
    out = rebuild_open_questions(wiki_dir)
    click.echo(f"wrote {out}")

@cli.command("add-edge")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--source", required=True)
@click.option("--target", required=True)
@click.option("--relation", required=True)
@click.option("--bidirectional", is_flag=True)
def cli_add_edge(wiki_dir: Path, source: str, target: str, relation: str, bidirectional: bool):
    add_edge(wiki_dir, source, target, relation, bidirectional)
    click.echo(f"added {relation}: {source} → {target}")

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_wiki_engine_cli.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/wiki_engine.py tests/unit/test_wiki_engine_cli.py
git commit -m "feat(wiki_engine): add click CLI"
```

### Task 3.6: `lint.py` — broken wikilink check

**Files:**
- Create: `tools/lint.py`
- Test: `tests/unit/test_lint_broken_links.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_lint_broken_links.py
from pathlib import Path
from tools.lint import check_broken_wikilinks
from tools._models import LintSeverity

def test_broken_link_detected(sample_wiki: Path):
    findings = check_broken_wikilinks(sample_wiki / "wiki")
    # d2.md has affects: [[m99-nonexistent]]
    targets = [f.message for f in findings]
    assert any("m99-nonexistent" in t for t in targets)
    assert all(f.severity == LintSeverity.ERROR for f in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_lint_broken_links.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `tools/lint.py` (broken-links check)**

```python
"""Wiki structural lint. Pure Python, no LLM."""
from __future__ import annotations
from pathlib import Path
from tools._models import LintFinding, LintSeverity
from tools.wiki_engine import scan_wiki, parse_page

def check_broken_wikilinks(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    slugs = {p.slug for p in pages}
    findings: list[LintFinding] = []
    for p in pages:
        for link in p.forward_links:
            target_slug = link.split("/")[-1].split("|")[0]
            if target_slug not in slugs:
                findings.append(LintFinding(
                    check="broken-wikilink",
                    severity=LintSeverity.ERROR,
                    file=p.path,
                    line=0,
                    message=f"broken wikilink: [[{link}]] (no page with slug {target_slug})",
                    fix_available=False,
                ))
    return findings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_lint_broken_links.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/lint.py tests/unit/test_lint_broken_links.py
git commit -m "feat(lint): broken wikilink check"
```

### Task 3.7: `lint.py` — missing reverse-link check

**Files:**
- Modify: `tools/lint.py:end`
- Test: `tests/unit/test_lint_missing_reverse.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_lint_missing_reverse.py
from pathlib import Path
from tools.lint import check_missing_reverse_links
from tools._models import LintSeverity

def test_missing_reverse_detected(sample_wiki: Path):
    """d1.md has affects:[[m1]]; m1's `## Decisions` should list d1 — but doesn't."""
    findings = check_missing_reverse_links(sample_wiki / "wiki")
    msgs = [f.message for f in findings]
    assert any("d1" in m and "m1" in m for m in msgs)
    assert all(f.severity == LintSeverity.WARNING for f in findings)
    assert all(f.fix_available for f in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_lint_missing_reverse.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `check_missing_reverse_links` in `tools/lint.py`**

```python
# Append to tools/lint.py
from tools.wiki_engine import EDGE_KEYS, REVERSE_OF, _coerce_targets

def check_missing_reverse_links(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {p.slug: p for p in pages}
    findings: list[LintFinding] = []
    for src in pages:
        for key, value in src.frontmatter.items():
            reverse = REVERSE_OF.get(key)
            if reverse is None or reverse.startswith("_"):
                continue  # section-based reverses checked separately
            for target_slug in _coerce_targets(value):
                tgt = by_slug.get(target_slug)
                if tgt is None:
                    continue
                tgt_field = tgt.frontmatter.get(reverse, [])
                if isinstance(tgt_field, str):
                    tgt_field = [tgt_field]
                tgt_slugs = [_slug_of(s) for s in tgt_field]
                if src.slug not in tgt_slugs:
                    findings.append(LintFinding(
                        check="missing-reverse-link",
                        severity=LintSeverity.WARNING,
                        file=tgt.path,
                        line=0,
                        message=f"{tgt.slug}.{reverse} missing reverse for {src.slug}.{key}",
                        fix_available=True,
                        suggested_fix=f"add [[{src.slug}]] to {tgt.path} frontmatter `{reverse}`",
                    ))
    return findings

def _slug_of(s) -> str:
    if isinstance(s, str):
        if s.startswith("[[") and s.endswith("]]"):
            return s[2:-2].split("|")[0]
        return s
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_lint_missing_reverse.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/lint.py tests/unit/test_lint_missing_reverse.py
git commit -m "feat(lint): missing reverse-link check"
```

### Task 3.8: `lint.py` — orphan, frontmatter, duplicate-slug checks

**Files:**
- Modify: `tools/lint.py:end`
- Test: `tests/unit/test_lint_orphans.py`, `tests/unit/test_lint_frontmatter.py`, `tests/unit/test_lint_duplicate_slugs.py`

- [ ] **Step 1: Write all three failing tests**

```python
# tests/unit/test_lint_orphans.py
from pathlib import Path
from tools.lint import check_orphans

def test_orphan_detected(sample_wiki: Path):
    findings = check_orphans(sample_wiki / "wiki")
    # m3 has no in/out links and is in index.md — but no incoming edges → orphan
    msgs = [f.message for f in findings]
    assert any("m3" in m for m in msgs)
```

```python
# tests/unit/test_lint_frontmatter.py
from pathlib import Path
import yaml
from tools.lint import check_required_frontmatter

def test_missing_frontmatter_field_detected(sample_wiki: Path):
    schema = {"module": ["title", "slug", "status", "owner"]}  # owner missing on all modules
    findings = check_required_frontmatter(sample_wiki / "wiki", schema, dir_to_type={"modules": "module"})
    assert any("owner" in f.message for f in findings)
```

```python
# tests/unit/test_lint_duplicate_slugs.py
from pathlib import Path
from tools.lint import check_duplicate_slugs

def test_duplicate_slug_detected(sample_wiki: Path):
    # Create a duplicate
    (sample_wiki / "wiki" / "modules" / "m1-dup.md").write_text(
        "---\ntitle: Dup\nslug: m1\nstatus: stable\n---\n# Dup\n")
    findings = check_duplicate_slugs(sample_wiki / "wiki")
    assert any("m1" in f.message for f in findings)
```

- [ ] **Step 2: Run tests — all fail**

Run: `uv run pytest tests/unit/test_lint_orphans.py tests/unit/test_lint_frontmatter.py tests/unit/test_lint_duplicate_slugs.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement three checks in `tools/lint.py`**

```python
# Append to tools/lint.py
from tools.wiki_engine import rebuild_edges
from collections import Counter

def check_orphans(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    incoming: dict[str, int] = {p.slug: 0 for p in pages}
    for p in pages:
        for link in p.forward_links:
            target = link.split("|")[0].split("/")[-1]
            if target in incoming:
                incoming[target] += 1
    index_text = (wiki_dir / "index.md").read_text() if (wiki_dir / "index.md").exists() else ""
    findings: list[LintFinding] = []
    for p in pages:
        if incoming[p.slug] == 0 and f"[[{p.slug}]]" not in index_text:
            findings.append(LintFinding(
                check="orphan",
                severity=LintSeverity.WARNING,
                file=p.path,
                line=0,
                message=f"orphan: {p.slug} has no incoming links and is not in index.md",
                fix_available=False,
            ))
    return findings

def check_required_frontmatter(wiki_dir: Path, schema: dict[str, list[str]], dir_to_type: dict[str, str]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    pages = scan_wiki(wiki_dir)
    for p in pages:
        page_path = Path(p.path)
        # Determine type by parent dir name
        type_name = None
        for part in page_path.parts:
            if part in dir_to_type:
                type_name = dir_to_type[part]
                break
        if type_name is None:
            continue
        required = schema.get(type_name, [])
        for field in required:
            if field not in p.frontmatter:
                findings.append(LintFinding(
                    check="missing-frontmatter-field",
                    severity=LintSeverity.ERROR,
                    file=p.path,
                    line=0,
                    message=f"{p.slug} missing required frontmatter `{field}` (type={type_name})",
                    fix_available=False,
                ))
    return findings

def check_duplicate_slugs(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    counts = Counter(p.slug for p in pages)
    findings: list[LintFinding] = []
    for slug, count in counts.items():
        if count > 1:
            offenders = [p.path for p in pages if p.slug == slug]
            findings.append(LintFinding(
                check="duplicate-slug",
                severity=LintSeverity.ERROR,
                file=offenders[0],
                line=0,
                message=f"duplicate slug `{slug}`: {offenders}",
                fix_available=False,
            ))
    return findings
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_lint_orphans.py tests/unit/test_lint_frontmatter.py tests/unit/test_lint_duplicate_slugs.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/lint.py tests/unit/test_lint_orphans.py tests/unit/test_lint_frontmatter.py tests/unit/test_lint_duplicate_slugs.py
git commit -m "feat(lint): orphan, missing-frontmatter, duplicate-slug checks"
```

### Task 3.9: `lint.py` — dependency rule check + --fix mode + CLI

**Files:**
- Modify: `tools/lint.py:end`
- Test: `tests/unit/test_lint_dependency_rules.py`, `tests/unit/test_lint_fix_mode.py`, `tests/unit/test_lint_cli.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_lint_dependency_rules.py
from pathlib import Path
from tools.lint import check_dependency_rules
from tools._models import LintSeverity

def test_dependency_rule_violation_detected(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "core").mkdir(parents=True)
    (wiki / "infrastructure").mkdir()
    (wiki / "core" / "user.md").write_text(
        "---\ntitle: User\nslug: user\nstatus: stable\nuses: ['[[postgres-adapter]]']\n---\n")
    (wiki / "infrastructure" / "postgres-adapter.md").write_text(
        "---\ntitle: PG\nslug: postgres-adapter\nstatus: stable\n---\n")
    rules = [{"from": "core/", "forbidden_to": ["infrastructure/", "adapters/"]}]
    findings = check_dependency_rules(wiki, rules)
    assert any(f.severity == LintSeverity.WARNING for f in findings)
    assert any("core/" in f.message and "infrastructure/" in f.message for f in findings)
```

```python
# tests/unit/test_lint_fix_mode.py
from pathlib import Path
from tools.lint import apply_fixes, run_all_checks

def test_fix_mode_writes_reverse_link(sample_wiki: Path):
    findings = run_all_checks(sample_wiki / "wiki", schema={}, dir_to_type={}, dependency_rules=[])
    fixed = apply_fixes(findings, sample_wiki / "wiki")
    # m1 should now contain d1 in some Decisions reference
    m1 = (sample_wiki / "wiki" / "modules" / "m1.md").read_text()
    assert "d1" in m1
    assert fixed > 0
```

```python
# tests/unit/test_lint_cli.py
from pathlib import Path
from click.testing import CliRunner
from tools.lint import cli

def test_lint_dry_run_exits_with_findings(sample_wiki: Path):
    r = CliRunner().invoke(cli, ["--wiki-dir", str(sample_wiki / "wiki"), "--dry-run"])
    assert r.exit_code != 0  # 🔴 broken-link causes nonzero
    assert "broken-wikilink" in r.output
```

- [ ] **Step 2: Run tests — all fail**

Run: `uv run pytest tests/unit/test_lint_dependency_rules.py tests/unit/test_lint_fix_mode.py tests/unit/test_lint_cli.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement remaining lint pieces in `tools/lint.py`**

```python
# Append to tools/lint.py
import click
import fnmatch
from tools.wiki_engine import add_edge

def check_dependency_rules(wiki_dir: Path, rules: list[dict]) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {p.slug: p for p in pages}
    findings: list[LintFinding] = []
    for src in pages:
        src_dir = str(Path(src.path).relative_to(wiki_dir).parent) + "/"
        for link in src.forward_links:
            target_slug = link.split("|")[0].split("/")[-1]
            tgt = by_slug.get(target_slug)
            if tgt is None:
                continue
            tgt_dir = str(Path(tgt.path).relative_to(wiki_dir).parent) + "/"
            for rule in rules:
                from_pattern = rule["from"]
                if not src_dir.startswith(from_pattern):
                    continue
                for forbidden in rule.get("forbidden_to", []):
                    if tgt_dir.startswith(forbidden):
                        findings.append(LintFinding(
                            check="dependency-rule-violation",
                            severity=LintSeverity.WARNING,
                            file=src.path,
                            line=0,
                            message=f"dependency rule: {from_pattern} → {forbidden} forbidden ({src.slug} → {tgt.slug})",
                            fix_available=False,
                        ))
    return findings

def run_all_checks(wiki_dir: Path, schema: dict, dir_to_type: dict, dependency_rules: list[dict]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    findings += check_broken_wikilinks(wiki_dir)
    findings += check_missing_reverse_links(wiki_dir)
    findings += check_orphans(wiki_dir)
    findings += check_required_frontmatter(wiki_dir, schema, dir_to_type)
    findings += check_duplicate_slugs(wiki_dir)
    findings += check_dependency_rules(wiki_dir, dependency_rules)
    return findings

def apply_fixes(findings: list[LintFinding], wiki_dir: Path) -> int:
    """Applies safe fixes; returns count of fixes applied."""
    fixed = 0
    for f in findings:
        if not f.fix_available:
            continue
        if f.check == "missing-reverse-link":
            # Parse: "<tgt-slug>.<reverse> missing reverse for <src-slug>.<key>"
            try:
                tgt_part, _, src_part = f.message.replace("missing reverse for ", "").partition(" ")
                tgt_slug, _, _ = tgt_part.partition(".")
                src_slug, _, key = src_part.partition(".")
                add_edge(wiki_dir, source=tgt_slug, target=src_slug,
                         relation=_lookup_reverse(key), bidirectional=False)
                fixed += 1
            except Exception:
                continue
    return fixed

def _lookup_reverse(key: str) -> str:
    from tools.wiki_engine import REVERSE_OF
    return REVERSE_OF.get(key, key)

@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--fix", is_flag=True, help="Apply safe fixes in place.")
@click.option("--suggest", is_flag=True, help="Print suggestions but don't write.")
@click.option("--dry-run", is_flag=True, help="Run checks, exit nonzero if 🔴 found.")
@click.option("--config", type=click.Path(path_type=Path, exists=True),
              help="Path to wiki-creator config (preset+overlay merged) for schema.")
def cli(wiki_dir: Path, fix: bool, suggest: bool, dry_run: bool, config: Path | None):
    schema, dir_to_type, dep_rules = _load_config(config)
    findings = run_all_checks(wiki_dir, schema, dir_to_type, dep_rules)
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    warnings = [f for f in findings if f.severity == LintSeverity.WARNING]

    if fix:
        n = apply_fixes(findings, wiki_dir)
        click.echo(f"applied {n} fix(es); re-running checks...")
        findings = run_all_checks(wiki_dir, schema, dir_to_type, dep_rules)
        errors = [f for f in findings if f.severity == LintSeverity.ERROR]
        warnings = [f for f in findings if f.severity == LintSeverity.WARNING]

    for f in findings:
        icon = "🔴" if f.severity == LintSeverity.ERROR else "🟡"
        click.echo(f"{icon} [{f.check}] {f.file}: {f.message}")
        if suggest and f.suggested_fix:
            click.echo(f"   ↪ {f.suggested_fix}")

    click.echo(f"\nsummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        raise SystemExit(1)
    if dry_run and warnings:
        raise SystemExit(2)

def _load_config(config_path: Path | None) -> tuple[dict, dict, list]:
    if config_path is None:
        return {}, {}, []
    import yaml
    cfg = yaml.safe_load(config_path.read_text())
    schema = {t["name"]: t.get("frontmatter_required", []) for t in cfg.get("entity_types", [])}
    dir_to_type = {t["dir"].rstrip("/"): t["name"] for t in cfg.get("entity_types", [])}
    dep_rules = cfg.get("dependency_rules", [])
    return schema, dir_to_type, dep_rules

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_lint_dependency_rules.py tests/unit/test_lint_fix_mode.py tests/unit/test_lint_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/lint.py tests/unit/test_lint_dependency_rules.py tests/unit/test_lint_fix_mode.py tests/unit/test_lint_cli.py
git commit -m "feat(lint): dependency rules + --fix mode + CLI"
```

### Task 3.10: `classify.py` — extension-based + LLM stub

**Files:**
- Create: `tools/classify.py`
- Test: `tests/unit/test_classify_extension.py`, `tests/unit/test_classify_llm_stub.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_classify_extension.py
from pathlib import Path
from tools.classify import classify

def test_classify_openapi(tmp_path: Path):
    p = tmp_path / "auth.yaml"
    p.write_text("openapi: 3.0.0\ninfo:\n  title: Auth\n")
    a = classify(p)
    assert a.kind == "openapi"
    assert a.suggested_slot == "contracts/rest"

def test_classify_proto(tmp_path: Path):
    p = tmp_path / "svc.proto"
    p.write_text("syntax = \"proto3\";\nservice X {}")
    a = classify(p)
    assert a.kind == "protobuf"
    assert a.suggested_slot == "contracts/grpc"

def test_classify_unknown_returns_none(tmp_path: Path):
    p = tmp_path / "weird.xyz"
    p.write_text("???")
    a = classify(p)
    assert a.kind == "unknown"
    assert a.suggested_slot is None
```

```python
# tests/unit/test_classify_llm_stub.py
from pathlib import Path
from tools.classify import classify_llm_fallback

def test_llm_fallback_returns_none_without_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = tmp_path / "weird.txt"
    p.write_text("ambiguous content")
    result = classify_llm_fallback(p)
    assert result is None
```

- [ ] **Step 2: Run tests — fail**

Run: `uv run pytest tests/unit/test_classify_extension.py tests/unit/test_classify_llm_stub.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `tools/classify.py`**

```python
"""Artifact classifier — extension first, LLM fallback (stub)."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Artifact:
    kind: str
    suggested_slot: str | None
    confidence: float  # 0.0-1.0
    detected_by: str   # "extension" | "frontmatter" | "llm" | ...

def classify(path: Path) -> Artifact:
    name = path.name.lower()
    suffix = path.suffix.lower()
    head = path.read_text(errors="ignore")[:2000] if path.is_file() else ""

    if suffix in (".yaml", ".yml") and "openapi:" in head:
        return Artifact("openapi", "contracts/rest", 0.95, "extension+content")
    if suffix in (".yaml", ".yml") and "asyncapi:" in head:
        return Artifact("asyncapi", "contracts/events", 0.95, "extension+content")
    if suffix in (".graphql", ".gql"):
        return Artifact("graphql-schema", "contracts/graphql", 0.95, "extension")
    if suffix == ".proto":
        return Artifact("protobuf", "contracts/grpc", 0.95, "extension")
    if suffix == ".sql" and "create table" in head.lower():
        return Artifact("sql-ddl", None, 0.90, "extension+content")  # triggers schema-evolve
    if suffix == ".tf":
        return Artifact("terraform", None, 0.85, "extension")  # triggers schema-evolve
    if suffix == ".md":
        if "kind: adr" in head or name.startswith("adr-"):
            return Artifact("adr", "decisions", 0.90, "frontmatter+filename")
        if "kind: prd" in head or name.startswith("prd"):
            return Artifact("prd", "specs", 0.90, "frontmatter+filename")
        if "kind: rfc" in head or name.startswith("rfc"):
            return Artifact("rfc", "specs", 0.90, "frontmatter+filename")
        if "kind: runbook" in head:
            return Artifact("runbook", "specs", 0.85, "frontmatter")
        if "kind: postmortem" in head or "postmortem" in name:
            return Artifact("postmortem", "decisions", 0.85, "frontmatter+filename")
        if "kind: transcript" in head:
            return Artifact("transcript", None, 0.80, "frontmatter")
        return Artifact("markdown", None, 0.50, "extension")
    if suffix == ".puml" or suffix == ".mermaid":
        return Artifact("diagram", "specs", 0.85, "extension")
    if suffix == ".postman_collection.json" or name.endswith(".postman_collection.json"):
        return Artifact("postman-collection", "contracts/rest", 0.90, "extension")

    return Artifact("unknown", None, 0.0, "fallback")

def classify_llm_fallback(path: Path) -> Artifact | None:
    """LLM-based classification stub. Returns None if no API key configured.

    A real implementation would call Claude with the file head + ask for kind.
    For initial release, we ship the stub and rely on extension classification.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    # TODO(later): implement actual LLM call. Until then, return None.
    return None
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_classify_extension.py tests/unit/test_classify_llm_stub.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/classify.py tests/unit/test_classify_extension.py tests/unit/test_classify_llm_stub.py
git commit -m "feat(classify): extension-based classifier + LLM fallback stub"
```

---

## Phase 4 — Jinja templates + assets

### Task 4.1: Core .j2 templates (CLAUDE.md, README, index, log, pyproject, gitignore, env)

**Files:**
- Create: `assets/claude-md.j2`, `assets/readme.j2`, `assets/index-md.j2`, `assets/log-md.j2`, `assets/pyproject.j2`, `assets/gitignore.j2`, `assets/env.example`, `assets/settings-local.j2`
- Test: `tests/unit/test_templates_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_templates_render.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ASSETS = Path(__file__).parents[2] / "assets"

def _env():
    return Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)

def test_claude_md_renders():
    env = _env()
    out = env.get_template("claude-md.j2").render(
        project_name="Demo", project_description="A demo wiki",
        wiki_dir="wiki", preset="software-project", overlay="hexagonal",
        date="2026-04-28",
        entity_types=[
            {"name": "module", "dir": "modules",
             "frontmatter_required": ["title", "slug", "status"],
             "sections_required": ["Provides", "Consumes"]}],
        cross_ref_rules=[{"forward": "module A: depends_on B", "reverse": "B.dependents adds A"}],
        skills=["/wiki-init", "/wiki-ingest", "/wiki-query", "/wiki-lint"],
    )
    assert "Demo" in out
    assert "hexagonal" in out
    assert "module" in out

def test_index_md_renders():
    out = _env().get_template("index-md.j2").render(
        project_name="Demo", date="2026-04-28",
        entity_types=[{"name": "module", "dir": "modules"}, {"name": "decision", "dir": "decisions"}],
    )
    assert "## Module" in out or "## module" in out.lower()

def test_log_md_renders_first_entry():
    out = _env().get_template("log-md.j2").render(date="2026-04-28", preset="software-project", overlay="hexagonal")
    assert "[2026-04-28]" in out
    assert "bootstrap" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_templates_render.py -v`
Expected: TemplateNotFound.

- [ ] **Step 3: Write `assets/claude-md.j2`**

```jinja2
# {{ project_name }} Wiki

{{ project_description }}

- **Preset:** {{ preset }}
- **Overlay:** {{ overlay }}
- **Wiki dir:** `{{ wiki_dir }}/`
- **Generated:** {{ date }}

## Mutability Matrix

| Layer | Path | Writer | Rule |
|---|---|---|---|
| L1 Raw | `raw/**` | Human only | Immutable after ingest |
| L2 Wiki | `{{ wiki_dir }}/**` (excl. graph/) | LLM via skills | Each write triggers reverse-link check |
| L3 Derived | `{{ wiki_dir }}/graph/**` | `tools/wiki_engine.py` only | Auto-generated, hand edits clobbered |
| L4 Schema | `CLAUDE.md`, `.claude/**` | Human + `/wiki-evolve` (gated) | Contract layer |

## Page Types

{% for type in entity_types %}
### {{ type.name }} (`{{ wiki_dir }}/{{ type.dir }}/`)

- **Required frontmatter:** {{ type.frontmatter_required | join(', ') }}
{% if type.frontmatter_optional %}- **Optional frontmatter:** {{ type.frontmatter_optional | join(', ') }}
{% endif %}{% if type.sections_required %}- **Required sections:** {{ type.sections_required | join(', ') }}
{% endif %}
{% endfor %}

## Cross-Reference Rules

{% for rule in cross_ref_rules %}
- `{{ rule.forward }}` → reverse: `{{ rule.reverse }}`
{% endfor %}

## index.md format

YAML-frontmatter caretaker catalog. Auto-populated. Do not hand-edit the body sections;
they are regenerated by `/wiki-ingest`.

## log.md format

Append-only. One entry per line:

```
## [YYYY-MM-DD] op | description
```

Where `op ∈ {bootstrap, ingest, query, evolve, schema-change, session-end, stub}`.

## Constraints

- `raw/**` is read-only for the agent.
- `{{ wiki_dir }}/graph/**` is auto-generated (never hand-edit).
- Bidirectional links are required: every forward link must have a reverse.
- New entity types require `/wiki-evolve` (gated by default).

## Skills

{% for s in skills %}- `{{ s }}`
{% endfor %}

## Python environment

- Python 3.12+
- Use `uv run` for any tool invocation: `uv run python tools/lint.py`
- Activate `.venv` if invoking outside `uv`.

## Hooks behavior

- **session-start** loads `{{ wiki_dir }}/graph/context_brief.md` into agent context.
- **pre-tool-use** validates frontmatter and reverse-link on writes to `{{ wiki_dir }}/`.
- **post-tool-use** debounces (5s) `wiki_engine.py rebuild-context-brief`.
- **session-end** runs `lint --suggest`, appends a session-end log entry, and prints a summary.

## Schema-evolve mode

`{{ schema_evolve_mode | default('gated') }}` — {% if schema_evolve_mode == 'auto' %}new artifact types are added automatically; rollback via git revert.{% else %}new artifact types must be confirmed before being added.{% endif %}
```

- [ ] **Step 4: Write `assets/readme.j2`**

```jinja2
# {{ project_name }}

{{ project_description }}

This project uses an LLM-maintained wiki (Karpathy + OmegaWiki style) as persistent
agent memory. The wiki lives in `{{ wiki_dir }}/`. The runtime contract for agents
is in `CLAUDE.md`.

## Three commands to know

- `/wiki-ingest <path>` — ingest a raw artifact into the wiki
- `/wiki-query <question>` — ask the wiki
- `/wiki-lint --fix` — apply safe corrections

## Layout

- `raw/` — immutable sources (read-only for the agent)
- `{{ wiki_dir }}/` — LLM-maintained markdown
- `{{ wiki_dir }}/graph/` — auto-generated context brief, edges, open questions
- `CLAUDE.md` — runtime contract
- `tools/` — Python engine (lint, edges, classify)

## Obsidian

The `{{ wiki_dir }}/` directory is an Obsidian vault. Open it in Obsidian to browse
the graph view. Dataview is enabled.

## Hooks

- **Session start** loads compressed context for the agent.
- **Session end** runs lint and appends a log entry.
- **Pre-commit** runs `lint --fix` and blocks on errors.
{% if ci %}- **CI** runs `wiki-lint` on every push; weekly `wiki-review` posts an issue.
{% endif %}

## Generated

`{{ date }}` by `wiki-creator` (preset={{ preset }}, overlay={{ overlay }}).
```

- [ ] **Step 5: Write `assets/index-md.j2`**

```jinja2
---
project: {{ project_name }}
generated: {{ date }}
---
# Index

{% for type in entity_types %}
## {{ type.name | title }}

<!-- auto-populated by /wiki-ingest -->

{% endfor %}
```

- [ ] **Step 6: Write `assets/log-md.j2`**

```jinja2
# Log

## [{{ date }}] bootstrap | wiki-creator initialized | preset={{ preset }} overlay={{ overlay }}
```

- [ ] **Step 7: Write `assets/pyproject.j2`**

```jinja2
[project]
name = "{{ project_name | lower | replace(' ', '-') }}-wiki"
version = "0.1.0"
description = "{{ project_description }}"
requires-python = ">=3.12"
dependencies = [
    "jinja2>=3.1",
    "pyyaml>=6.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 8: Write `assets/gitignore.j2`**

```jinja2
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
{{ wiki_dir }}/graph/.rebuild.lock
```

- [ ] **Step 9: Write `assets/env.example`**

```
# Anthropic API key (required for headless CI workflows like wiki-review)
# ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 10: Write `assets/settings-local.j2`**

```jinja2
{
  "hooks": {
    "session-start": [
      {"command": ".claude/hooks/session-start.sh"}
    ],
    "pre-tool-use": [
      {"matcher": "Write|Edit", "command": ".claude/hooks/pre-tool-use.sh", "path_glob": "{{ wiki_dir }}/**"}
    ],
    "post-tool-use": [
      {"matcher": "Write", "command": ".claude/hooks/post-tool-use.sh", "path_glob": "{{ wiki_dir }}/**"}
    ],
    "session-end": [
      {"command": ".claude/hooks/session-end.sh"}
    ]
  }
}
```

- [ ] **Step 11: Run tests**

Run: `uv run pytest tests/unit/test_templates_render.py -v`
Expected: 3 passed.

- [ ] **Step 12: Commit**

```bash
git add assets/claude-md.j2 assets/readme.j2 assets/index-md.j2 assets/log-md.j2 assets/pyproject.j2 assets/gitignore.j2 assets/env.example assets/settings-local.j2 tests/unit/test_templates_render.py
git commit -m "feat(assets): core .j2 templates (CLAUDE/README/index/log/etc.)"
```

### Task 4.2: Frontmatter templates per entity type

**Files:**
- Create: `assets/frontmatter/*.yaml` (24 files — one per entity type across all 5 presets)

- [ ] **Step 1: Write `assets/frontmatter/module.yaml`**

```yaml
title: ""
slug: ""
status: "draft"      # draft | stable | deprecated
description: ""
depends_on: []
dependents: []
owner: ""
date_updated: ""
```

- [ ] **Step 2: Write `assets/frontmatter/component.yaml`**

```yaml
title: ""
slug: ""
parent_module: ""
status: "draft"
tests: []
```

- [ ] **Step 3: Write `assets/frontmatter/decision.yaml`**

```yaml
title: ""
slug: ""
status: "proposed"   # proposed | accepted | superseded | rejected
date: ""
affects: []
supersedes: ""
superseded_by: ""
```

- [ ] **Step 4: Write `assets/frontmatter/spec.yaml`**

```yaml
title: ""
slug: ""
kind: ""             # prd | rfc | api | protocol | runbook | threat-model | test-plan | diagram
status: "draft"
implements: []
version: ""
date_updated: ""
```

- [ ] **Step 5: Write `assets/frontmatter/entity.yaml`**

```yaml
title: ""
slug: ""
defined_in: ""
description: ""
```

- [ ] **Step 6: Write `assets/frontmatter/contract.yaml`**

```yaml
title: ""
slug: ""
transport: ""        # rest | graphql | grpc | events | webhooks | rpc | data-models
service: ""          # [[module-X]]
consumers: []
version: ""
status: "draft"      # draft | beta | stable | deprecated
source_file: ""
breaking_changes: []
date_updated: ""
```

- [ ] **Step 7: Write `assets/frontmatter/person.yaml`**

```yaml
title: ""
slug: ""
role: ""
email: ""
github: ""
areas: []
```

- [ ] **Step 8: Write `assets/frontmatter/task.yaml`**

```yaml
title: ""
slug: ""
status: "planned"    # planned | in_progress | done | blocked
target_module: ""
assignee: ""
due: ""
blocked_by: []
```

- [ ] **Step 9: Write research preset frontmatters** — `paper.yaml`, `concept.yaml`, `topic.yaml`, `idea.yaml`, `experiment.yaml`, `claim.yaml`

```yaml
# paper.yaml
title: ""
slug: ""
authors: []
year: 0
source_url: ""
abstract: ""
key_claims: []
```

```yaml
# concept.yaml
title: ""
slug: ""
defined_by: []
related_to: []
```

```yaml
# topic.yaml
title: ""
slug: ""
description: ""
```

```yaml
# idea.yaml
title: ""
slug: ""
status: "active"     # active | tested | failed | shelved
originator: ""
extends: []
failure_reason: ""   # set if status == failed
```

```yaml
# experiment.yaml
title: ""
slug: ""
hypothesis: ""
status: "planned"    # planned | running | done | abandoned
results: ""
tests: []
supports: []
contradicts: []
```

```yaml
# claim.yaml
title: ""
slug: ""
status: "open"       # open | supported | refuted
supported_by: []
contradicted_by: []
```

- [ ] **Step 10: Write product preset frontmatters** — `feature.yaml`, `persona.yaml`, `flow.yaml`, `metric.yaml`

```yaml
# feature.yaml
title: ""
slug: ""
status: "discovery"  # discovery | building | shipped | sunset
owner: ""
tracks_metric: []
```

```yaml
# persona.yaml
title: ""
slug: ""
description: ""
goals: []
pains: []
```

```yaml
# flow.yaml
title: ""
slug: ""
persona: ""
steps: []
```

```yaml
# metric.yaml
title: ""
slug: ""
formula: ""
target: ""
```

- [ ] **Step 11: Write personal + knowledge-base frontmatters** — `project.yaml`, `area.yaml`, `resource.yaml`, `permanent.yaml`, `fleeting.yaml`, `source.yaml`

```yaml
# project.yaml
title: ""
slug: ""
status: "active"     # active | done | dropped
due: ""
belongs_to: ""
```

```yaml
# area.yaml
title: ""
slug: ""
description: ""
```

```yaml
# resource.yaml
title: ""
slug: ""
source_url: ""
captured_at: ""
```

```yaml
# permanent.yaml
title: ""
slug: ""
evergreen: true
distilled_from: []
```

```yaml
# fleeting.yaml
title: ""
slug: ""
captured_at: ""
```

```yaml
# source.yaml
title: ""
slug: ""
url: ""
captured_at: ""
```

- [ ] **Step 12: Commit**

```bash
git add assets/frontmatter/
git commit -m "feat(assets): frontmatter YAML templates for all entity types"
```

### Task 4.3: Hooks scripts + workflows + obsidian config + child-skills

**Files:**
- Create: `assets/hooks/{session-start,session-end,pre-tool-use,post-tool-use,pre-commit,install-hooks}.sh`
- Create: `assets/workflows/{wiki-lint,wiki-review,wiki-rollup}.yml`
- Create: `assets/obsidian/{workspace,graph,community-plugins,hotkeys}.json`
- Create: `assets/child-skills/ingest-domain.j2`

- [ ] **Step 1: Write `assets/hooks/session-start.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
BRIEF="$WIKI_DIR/graph/context_brief.md"
if [ -f "$BRIEF" ]; then
  cat "$BRIEF"
fi
```

- [ ] **Step 2: Write `assets/hooks/session-end.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
DATE="$(date -u +%Y-%m-%d)"

REPORT="$(uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --suggest 2>&1 || true)"
SUGGESTIONS=$(echo "$REPORT" | grep -c "^🟡" || true)
ERRORS=$(echo "$REPORT" | grep -c "^🔴" || true)

echo "## [$DATE] session-end | suggestions=$SUGGESTIONS errors=$ERRORS" >> "$WIKI_DIR/log.md"

uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null

echo "Session ended. Lint: $ERRORS error(s), $SUGGESTIONS suggestion(s)."
echo "Run: /wiki-lint --fix or /wiki-review"
```

- [ ] **Step 3: Write `assets/hooks/pre-tool-use.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
TARGET_FILE="${1:-}"

if [ -z "$TARGET_FILE" ]; then exit 0; fi
case "$TARGET_FILE" in
  "$WIKI_DIR"/graph/*) exit 0 ;;
esac

uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --dry-run 2>&1 | head -5 || true
```

- [ ] **Step 4: Write `assets/hooks/post-tool-use.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
LOCK="$WIKI_DIR/graph/.rebuild.lock"
NOW=$(date +%s)

if [ -f "$LOCK" ]; then
  LAST=$(cat "$LOCK")
  if [ $((NOW - LAST)) -lt 5 ]; then exit 0; fi
fi
echo "$NOW" > "$LOCK"
uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null &
```

- [ ] **Step 5: Write `assets/hooks/pre-commit.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"

uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --fix
RESULT=$?
if [ $RESULT -eq 0 ]; then
  git add "$WIKI_DIR"
  exit 0
fi
echo "Lint errors remain after --fix. Resolve before committing."
exit 1
```

- [ ] **Step 6: Write `assets/hooks/install-hooks.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
HOOK_SRC=".claude/hooks"

for HOOK in pre-commit post-commit; do
  if [ -f "$HOOK_SRC/${HOOK}.sh" ]; then
    cp "$HOOK_SRC/${HOOK}.sh" ".git/hooks/$HOOK"
    chmod +x ".git/hooks/$HOOK"
    echo "installed: .git/hooks/$HOOK"
  fi
done
```

- [ ] **Step 7: Write `assets/workflows/wiki-lint.yml`**

```yaml
name: wiki-lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: install uv
        run: pip install uv
      - name: sync deps
        run: uv sync --dev
      - name: run lint
        run: uv run python tools/lint.py --wiki-dir wiki --dry-run
```

- [ ] **Step 8: Write `assets/workflows/wiki-review.yml`**

```yaml
name: wiki-review
on:
  schedule:
    - cron: '0 9 * * 1'  # Mon 09:00 UTC
  workflow_dispatch:
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync
      - name: install Claude Code
        run: npm install -g @anthropic/claude-code
      - name: run /wiki-review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: claude -p "/wiki-review" > review.md
      - name: post issue
        uses: peter-evans/create-issue-from-file@v5
        with:
          title: "Weekly wiki review (auto)"
          content-filepath: review.md
          labels: wiki-review
```

- [ ] **Step 9: Write `assets/workflows/wiki-rollup.yml`**

```yaml
name: wiki-rollup
on:
  schedule:
    - cron: '0 9 1 * *'  # 1st of month, 09:00 UTC
  workflow_dispatch:
jobs:
  rollup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync
      - run: npm install -g @anthropic/claude-code
      - name: run /wiki-rollup
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: claude -p "/wiki-rollup month"
      - name: commit rollup
        run: |
          git config user.name "wiki-rollup-bot"
          git config user.email "wiki-rollup@noreply"
          git add wiki/rollups/ || true
          git commit -m "chore: monthly wiki rollup" || echo "no changes"
          git push
```

- [ ] **Step 10: Write Obsidian config files**

```json
// assets/obsidian/workspace.json
{
  "main": {
    "id": "main",
    "type": "split",
    "children": []
  },
  "active": ""
}
```

```json
// assets/obsidian/graph.json
{
  "collapse-filter": false,
  "search": "",
  "showTags": false,
  "showAttachments": false,
  "hideUnresolved": false,
  "showOrphans": true,
  "collapse-color-groups": false,
  "colorGroups": [],
  "collapse-display": false,
  "showArrow": true,
  "textFadeMultiplier": 0,
  "nodeSizeMultiplier": 1,
  "lineSizeMultiplier": 1,
  "collapse-forces": false,
  "centerStrength": 0.5,
  "repelStrength": 10,
  "linkStrength": 1,
  "linkDistance": 250,
  "scale": 1,
  "close": false
}
```

```json
// assets/obsidian/community-plugins.json
["dataview"]
```

```json
// assets/obsidian/hotkeys.json
{}
```

- [ ] **Step 11: Write `assets/child-skills/ingest-domain.j2`**

```jinja2
---
name: wiki-ingest-{{ type_name }}
description: Pre-classified ingest into `{{ wiki_dir }}/{{ slot_dir }}/`. Use when {{ trigger_phrase }}.
---

# wiki-ingest-{{ type_name }}

Wraps `/wiki-ingest` and forces classification into `{{ wiki_dir }}/{{ slot_dir }}/`.

## Behavior

1. Validate input file exists.
2. Skip the LLM classifier — set `kind = {{ type_name }}` directly.
3. Render `{{ wiki_dir }}/{{ slot_dir }}/<slug>.md` using frontmatter from `assets/frontmatter/{{ type_name }}.yaml`.
4. Update `index.md`, `log.md`, regenerate `graph/edges.jsonl`.

## Generated by

`/wiki-evolve {{ type_name }} --generate-skill` — see `references/schema-evolution.md`.
```

- [ ] **Step 12: Make hook scripts executable**

```bash
chmod +x assets/hooks/*.sh
```

- [ ] **Step 13: Commit**

```bash
git add assets/hooks/ assets/workflows/ assets/obsidian/ assets/child-skills/
git commit -m "feat(assets): hooks + workflows + obsidian config + child-skills template"
```

---

## Phase 5 — Bootstrap pipeline (`scripts/`)

### Task 5.1: `interview.py` — InterviewConfig + auto-detect

**Files:**
- Create: `scripts/interview.py`
- Test: `tests/unit/test_interview_round_trip.py`, `tests/unit/test_interview_auto_detect.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_interview_round_trip.py
from scripts.interview import InterviewConfig, config_from_answers

def test_config_dataclass_round_trip():
    c = InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="hexagonal",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="all", ci=True, schema_evolve_mode="gated",
    )
    assert c.preset == "software-project"
    assert c.obsidian is True

def test_config_from_answers_minimal():
    answers = {
        "project_name": "demo", "project_description": "d",
        "wiki_dir": "wiki", "preset": "software-project", "overlay": "none",
        "i18n": "en", "hooks": "all", "ci": True, "schema_evolve_mode": "gated",
    }
    c = config_from_answers(answers)
    assert c.preset == "software-project"
    assert c.overlay == "none"
```

```python
# tests/unit/test_interview_auto_detect.py
from pathlib import Path
from scripts.interview import auto_detect_wiki_dir

def test_auto_detect_greenfield_returns_wiki(tmp_path: Path):
    assert auto_detect_wiki_dir(tmp_path) == "wiki"

def test_auto_detect_existing_codebase_returns_dot_wiki(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text("{}")
    assert auto_detect_wiki_dir(tmp_path) == ".wiki"

def test_auto_detect_python_project_returns_dot_wiki(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert auto_detect_wiki_dir(tmp_path) == ".wiki"
```

- [ ] **Step 2: Run tests — fail**

Run: `uv run pytest tests/unit/test_interview_round_trip.py tests/unit/test_interview_auto_detect.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/interview.py`**

```python
"""Interactive interview → InterviewConfig."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class EntityTypeSpec:
    name: str
    dir: str
    frontmatter_required: list[str]
    frontmatter_optional: list[str] = field(default_factory=list)
    sections_required: list[str] = field(default_factory=list)

@dataclass
class InterviewConfig:
    project_name: str
    project_description: str
    wiki_dir: str  # "wiki" or ".wiki"
    preset: str   # software-project | research | product | personal | knowledge-base | custom
    overlay: str  # none | clean | hexagonal | ddd | ddd+clean | ddd+hexagonal | layered
    custom_entity_types: list[EntityTypeSpec] | None
    i18n_languages: list[str]
    hooks: str   # all | session | git | none
    ci: bool
    schema_evolve_mode: str  # gated | auto
    obsidian: bool = True
    python_version: str = "3.12"
    package_manager: str = "uv"

CODE_MARKERS = {
    "src", "lib", "package.json", "pyproject.toml", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "Gemfile", "composer.json",
    "tsconfig.json", "deno.json",
}

def auto_detect_wiki_dir(cwd: Path) -> str:
    """If existing codebase markers found → .wiki/, else wiki/."""
    for marker in CODE_MARKERS:
        if (cwd / marker).exists():
            return ".wiki"
    return "wiki"

def config_from_answers(answers: dict) -> InterviewConfig:
    return InterviewConfig(
        project_name=answers["project_name"],
        project_description=answers["project_description"],
        wiki_dir=answers["wiki_dir"],
        preset=answers["preset"],
        overlay=answers.get("overlay", "none"),
        custom_entity_types=answers.get("custom_entity_types"),
        i18n_languages=([answers["i18n"]] if isinstance(answers.get("i18n"), str) else answers.get("i18n", ["en"])),
        hooks=answers.get("hooks", "all"),
        ci=bool(answers.get("ci", False)),
        schema_evolve_mode=answers.get("schema_evolve_mode", "gated"),
    )
```

- [ ] **Step 4: Run tests — pass**

Run: `uv run pytest tests/unit/test_interview_round_trip.py tests/unit/test_interview_auto_detect.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/interview.py tests/unit/test_interview_round_trip.py tests/unit/test_interview_auto_detect.py
git commit -m "feat(scripts): InterviewConfig + auto-detect wiki dir"
```

### Task 5.2: `bootstrap.py` — config resolution + render + post-render

**Files:**
- Create: `scripts/bootstrap.py`
- Test: `tests/unit/test_bootstrap_render.py`, `tests/unit/test_bootstrap_idempotent.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_bootstrap_render.py
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap

def test_bootstrap_creates_expected_files(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo", project_description="A demo wiki",
        wiki_dir="wiki", preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "wiki" / "index.md").exists()
    assert (tmp_path / "wiki" / "log.md").exists()
    assert (tmp_path / "wiki" / "graph" / "edges.jsonl").exists()
    assert (tmp_path / ".obsidian" / "graph.json").exists()
    assert (tmp_path / "tools" / "lint.py").exists()
    # Entity-type dirs from software-project preset:
    for d in ["modules", "decisions", "specs", "entities", "contracts", "people", "tasks", "components"]:
        assert (tmp_path / "wiki" / d).is_dir(), f"missing: wiki/{d}"
    # Bootstrap log entry:
    assert "bootstrap" in (tmp_path / "wiki" / "log.md").read_text()

def test_bootstrap_overlay_hexagonal_creates_hex_dirs(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="hexagonal",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    assert (tmp_path / "wiki" / "core" / "entities").is_dir()
    assert (tmp_path / "wiki" / "ports" / "inbound").is_dir()
    assert (tmp_path / "wiki" / "adapters" / "outbound").is_dir()
```

```python
# tests/unit/test_bootstrap_idempotent.py
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap

def _cfg():
    return InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )

def test_re_bootstrap_does_not_clobber_wiki_pages(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg())
    user_page = tmp_path / "wiki" / "modules" / "my-mod.md"
    user_page.write_text("---\ntitle: Mine\nslug: my-mod\nstatus: stable\n---\n# Mine\n")
    bootstrap(target=tmp_path, config=_cfg(), upgrade=True)
    assert user_page.exists()
    assert "Mine" in user_page.read_text()
```

- [ ] **Step 2: Run tests — fail**

Run: `uv run pytest tests/unit/test_bootstrap_render.py tests/unit/test_bootstrap_idempotent.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/bootstrap.py`**

```python
"""Render pipeline: InterviewConfig → target file tree."""
from __future__ import annotations
import shutil
from datetime import date as _date
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader
from scripts.interview import InterviewConfig

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PLUGIN_ROOT / "assets"
PRESETS = PLUGIN_ROOT / "references" / "presets"
OVERLAYS = PLUGIN_ROOT / "references" / "overlays"
TOOLS = PLUGIN_ROOT / "tools"

def bootstrap(target: Path, config: InterviewConfig, upgrade: bool = False) -> None:
    target.mkdir(parents=True, exist_ok=True)
    merged = _resolve_merged_config(config)
    ctx = _render_context(config, merged)

    _render_top_level_files(target, ctx, upgrade=upgrade)
    _create_wiki_dirs(target, config, merged)
    _initialize_wiki_files(target, ctx, upgrade=upgrade)
    _copy_assets(target, config)
    _copy_tools(target)
    _initialize_graph(target, config)

def _resolve_merged_config(config: InterviewConfig) -> dict:
    preset = yaml.safe_load((PRESETS / f"{config.preset}.yaml").read_text()) if config.preset != "custom" \
             else {"name": "custom", "entity_types": [
                 {"name": t.name, "dir": t.dir,
                  "frontmatter_required": t.frontmatter_required,
                  "frontmatter_optional": t.frontmatter_optional,
                  "sections_required": t.sections_required} for t in (config.custom_entity_types or [])],
              "cross_ref_rules": []}
    if config.overlay == "none":
        return preset
    overlay_names = config.overlay.split("+")
    if "clean" in overlay_names and "hexagonal" in overlay_names:
        raise ValueError("clean+hexagonal not combinable")
    merged = dict(preset)
    merged["overlay_dirs"] = []
    merged["dependency_rules"] = []
    for ov_name in overlay_names:
        ov = yaml.safe_load((OVERLAYS / f"{ov_name}.yaml").read_text())
        merged["overlay_dirs"].extend(ov.get("top_level_dirs", []))
        merged["dependency_rules"].extend(ov.get("dependency_rules", []))
        merged["cross_ref_rules"].extend(ov.get("extra_cross_ref_rules", []))
    return merged

def _render_context(config: InterviewConfig, merged: dict) -> dict:
    return {
        "project_name": config.project_name,
        "project_description": config.project_description,
        "wiki_dir": config.wiki_dir,
        "preset": config.preset,
        "overlay": config.overlay,
        "date": _date.today().isoformat(),
        "entity_types": merged.get("entity_types", []),
        "cross_ref_rules": merged.get("cross_ref_rules", []),
        "skills": ["/wiki-init", "/wiki-ingest", "/wiki-query", "/wiki-lint",
                   "/wiki-evolve", "/wiki-spawn-agent", "/wiki-render"],
        "schema_evolve_mode": config.schema_evolve_mode,
        "ci": config.ci,
    }

def _render_top_level_files(target: Path, ctx: dict, upgrade: bool) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    files = [
        ("claude-md.j2", "CLAUDE.md"),
        ("readme.j2", "README.md"),
        ("pyproject.j2", "pyproject.toml"),
        ("gitignore.j2", ".gitignore"),
    ]
    for tmpl_name, out_name in files:
        out_path = target / out_name
        if out_path.exists() and upgrade and out_name in ("README.md",):
            continue  # Don't overwrite user-edited README
        out_path.write_text(env.get_template(tmpl_name).render(**ctx))
    shutil.copy(ASSETS / "env.example", target / ".env.example")

def _create_wiki_dirs(target: Path, config: InterviewConfig, merged: dict) -> None:
    wiki = target / config.wiki_dir
    wiki.mkdir(exist_ok=True)
    if merged.get("overlay_dirs"):
        for d in merged["overlay_dirs"]:
            (wiki / d).mkdir(parents=True, exist_ok=True)
    else:
        for t in merged.get("entity_types", []):
            (wiki / t["dir"]).mkdir(parents=True, exist_ok=True)
    (wiki / "outputs").mkdir(exist_ok=True)
    (wiki / "graph").mkdir(exist_ok=True)
    # raw/
    (target / "raw" / "docs").mkdir(parents=True, exist_ok=True)
    (target / "raw" / "transcripts").mkdir(exist_ok=True)
    (target / "raw" / "chats").mkdir(exist_ok=True)
    (target / "raw" / "web").mkdir(exist_ok=True)

def _initialize_wiki_files(target: Path, ctx: dict, upgrade: bool) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    wiki = target / ctx["wiki_dir"]
    if not (wiki / "index.md").exists() or not upgrade:
        (wiki / "index.md").write_text(env.get_template("index-md.j2").render(**ctx))
    log_path = wiki / "log.md"
    if not log_path.exists():
        log_path.write_text(env.get_template("log-md.j2").render(**ctx))
    elif upgrade:
        log_path.write_text(log_path.read_text() + f"\n## [{ctx['date']}] upgrade | re-bootstrapped via /wiki-init\n")

def _copy_assets(target: Path, config: InterviewConfig) -> None:
    if config.obsidian:
        obsidian = target / ".obsidian"
        obsidian.mkdir(exist_ok=True)
        for f in (ASSETS / "obsidian").iterdir():
            shutil.copy(f, obsidian / f.name)
    if config.hooks in ("all", "session", "git"):
        hooks_dir = target / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "hooks").iterdir():
            dest = hooks_dir / f.name
            shutil.copy(f, dest)
            dest.chmod(0o755)
        env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
        (target / ".claude" / "settings.local.json").write_text(
            env.get_template("settings-local.j2").render(wiki_dir=config.wiki_dir))
    if config.ci:
        wf_dir = target / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "workflows").iterdir():
            shutil.copy(f, wf_dir / f.name)
    (target / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    (target / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

def _copy_tools(target: Path) -> None:
    tools_dst = target / "tools"
    tools_dst.mkdir(exist_ok=True)
    for f in TOOLS.iterdir():
        if f.is_file() and f.suffix == ".py":
            shutil.copy(f, tools_dst / f.name)

def _initialize_graph(target: Path, config: InterviewConfig) -> None:
    g = target / config.wiki_dir / "graph"
    (g / "edges.jsonl").write_text("")
    (g / "context_brief.md").write_text("# Context brief\n\n_(empty — will populate after first ingest)_\n")
    (g / "open_questions.md").write_text("# Open questions\n\n_(none yet)_\n")
```

- [ ] **Step 4: Run tests — pass**

Run: `uv run pytest tests/unit/test_bootstrap_render.py tests/unit/test_bootstrap_idempotent.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/bootstrap.py tests/unit/test_bootstrap_render.py tests/unit/test_bootstrap_idempotent.py
git commit -m "feat(scripts): bootstrap pipeline (render + copy + idempotent upgrade)"
```

### Task 5.3: `add_entity_type.py` — schema evolution helper

**Files:**
- Create: `scripts/add_entity_type.py`
- Test: `tests/unit/test_add_entity_type.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_add_entity_type.py
from pathlib import Path
from scripts.add_entity_type import add_entity_type

def test_add_entity_type_updates_claude_md_and_creates_dir(sample_wiki: Path):
    new_spec = {
        "name": "migration",
        "dir": "data/migrations",
        "frontmatter_required": ["title", "slug", "applied_at"],
        "frontmatter_optional": ["target_table", "rollback"],
        "sections_required": ["Up", "Down"],
    }
    add_entity_type(sample_wiki, new_spec, trigger="ingest of raw/migrations/2026.sql")
    claude = (sample_wiki / "CLAUDE.md").read_text()
    assert "migration" in claude
    assert "data/migrations" in claude
    assert (sample_wiki / "wiki" / "data" / "migrations").is_dir()
    log = (sample_wiki / "wiki" / "log.md").read_text()
    assert "schema-change" in log
    assert "migration" in log
```

- [ ] **Step 2: Run test — fail**

Run: `uv run pytest tests/unit/test_add_entity_type.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/add_entity_type.py`**

```python
"""Schema evolution: append a new entity type to CLAUDE.md, create dir, log it."""
from __future__ import annotations
from datetime import date as _date
from pathlib import Path

PAGE_TYPES_HEADER = "## Page Types"

def add_entity_type(target: Path, spec: dict, trigger: str = "manual") -> None:
    claude_path = target / "CLAUDE.md"
    text = claude_path.read_text()
    new_section = _render_type_section(spec)
    if PAGE_TYPES_HEADER in text:
        # Append after the Page Types header section (before next ## section)
        idx = text.index(PAGE_TYPES_HEADER)
        next_h2 = text.find("\n## ", idx + len(PAGE_TYPES_HEADER))
        insert_at = next_h2 if next_h2 != -1 else len(text)
        text = text[:insert_at] + "\n" + new_section + "\n" + text[insert_at:]
    else:
        text = text + f"\n\n{PAGE_TYPES_HEADER}\n\n" + new_section + "\n"
    claude_path.write_text(text)

    new_dir = target / "wiki" / spec["dir"]
    new_dir.mkdir(parents=True, exist_ok=True)

    log_path = target / "wiki" / "log.md"
    today = _date.today().isoformat()
    log_path.write_text(log_path.read_text() +
        f"\n## [{today}] schema-change | added type: {spec['name']} ({spec['dir']}/) | trigger: {trigger}\n")

def _render_type_section(spec: dict) -> str:
    lines = [f"### {spec['name']} (`wiki/{spec['dir']}/`)\n",
             f"- **Required frontmatter:** {', '.join(spec.get('frontmatter_required', []))}"]
    if spec.get("frontmatter_optional"):
        lines.append(f"- **Optional frontmatter:** {', '.join(spec['frontmatter_optional'])}")
    if spec.get("sections_required"):
        lines.append(f"- **Required sections:** {', '.join(spec['sections_required'])}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test — pass**

Run: `uv run pytest tests/unit/test_add_entity_type.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/add_entity_type.py tests/unit/test_add_entity_type.py
git commit -m "feat(scripts): add_entity_type for schema evolution"
```

---

## Phase 6 — Skills (SKILL.md authoring)

Each skill below is its own task with a single step (write SKILL.md). Skills are LLM-orchestrated entry points; the heavy lifting is in `tools/` and `scripts/`.

### Task 6.1: `skills/wiki-init/SKILL.md`

**File:** `skills/wiki-init/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-init
description: Use this skill whenever the user wants to bootstrap a wiki, knowledge base, or persistent memory layer for an LLM agent or multi-agent system. Triggers include "create a wiki", "set up a knowledge base", "bootstrap project memory", "agent memory layer", "Karpathy LLM wiki", "OmegaWiki style", "Obsidian + Claude Code workflow", "set up CLAUDE.md", "wiki for my project", "memory for agents". Also use when the user describes wanting raw → wiki → schema separation, persistent compounding knowledge instead of RAG, or session-end automation that keeps documentation current. Do NOT use for one-off doc generation, single-file summaries, or static documentation that won't be incrementally maintained.
---

# wiki-init — bootstrap an LLM wiki into the current project

## Process

1. **Environment check**
   - Verify Python ≥ 3.12 and `uv` are available (suggest `pipx install uv` if missing).
   - Run `git rev-parse --is-inside-work-tree`; if not a repo, ask before `git init`.
   - Detect existing source code (src/, package.json, pyproject.toml, etc.).

2. **Interview** — sequentially ask:
   1. Project name (default: directory basename)
   2. One-line description
   3. Wiki dir — auto-suggest `wiki/` (greenfield) or `.wiki/` (existing code); allow override
   4. Preset: software-project (default) | research | product | personal | knowledge-base | custom
   5. (if software-project) Architectural overlay — none | clean | hexagonal | ddd | ddd+clean | ddd+hexagonal | layered (no default — explicit choice)
   6. (if custom) Define entity types — for each: name, dir, required frontmatter, sections
   7. i18n: en-only (default) or en + other
   8. Hooks installation: all (default) | session-only | git-only | none
   9. CI workflows: yes (default if `.github/` exists or remote is GitHub) | no
   10. Schema-evolve mode: gated (default) | auto

3. **Propose plan** — show resolved tree + key decisions; require user confirmation before any writes.

4. **Render** — invoke `uv run python -m scripts.bootstrap` (calls `scripts.bootstrap.bootstrap(target, config)`).

5. **Post-render** — `uv sync`, `tools/lint.py --dry-run`, `wiki_engine.py rebuild-context-brief`, `git add . && git commit -m "wiki bootstrap"`.

6. **First ingest (optional)** — if `raw/` has files, prompt to ingest now via `/wiki-ingest`.

7. **Handoff** — print 3 main commands, Obsidian instructions, session-end hook explainer.

## Idempotency

If `CLAUDE.md` already exists, enter upgrade mode: diff requested config vs existing, never overwrite wiki pages, only touch schema/scaffolding with confirmation.

## References

- `references/concept.md` — Karpathy + OmegaWiki philosophy
- `references/presets/` — preset YAMLs
- `references/overlays/` — overlay YAMLs
- `references/cross-reference-rules.md` — bidirectional link canon
- `references/hooks-design.md` — hook contracts
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-init/SKILL.md
git commit -m "feat(skills): wiki-init"
```

### Task 6.2: `skills/wiki-ingest/SKILL.md`

**File:** `skills/wiki-ingest/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-ingest
description: Use when the user wants to add new sources (papers, docs, transcripts, OpenAPI specs, ADRs, etc.) into an existing wiki. Triggers include "ingest this", "add to wiki", "process raw/", "import these docs", "feed this into the wiki". Use after `/wiki-init` has bootstrapped the wiki. Skip for one-off summaries that won't be persisted.
---

# wiki-ingest — raw artifact → wiki page(s)

## Process

1. Validate target paths exist (under `raw/` or absolute paths).
2. For each path:
   a. Run `tools/classify.py` to determine artifact kind.
   b. Match to existing slot in `CLAUDE.md` page types.
   c. If no match:
      - **gated mode** → propose options: (a) new top-level type, (b) sub-folder under existing layer, (c) section append on related page. Wait for user.
      - **auto mode** → pick best default and proceed (write `[schema-change]` log).
   d. If a new type is needed → invoke `/wiki-evolve <type>`.
   e. Render page from frontmatter template + artifact body. Use the entity type's required sections.
   f. Compute forward links from content; let `wiki_engine.add_edge --bidirectional` write reverse links automatically.
   g. Update `<wiki_dir>/index.md` (auto section for the page type).
   h. Append to `<wiki_dir>/log.md`: `## [date] ingest | <path> → <slot>`.
3. After all ingests:
   a. `uv run python tools/wiki_engine.py rebuild-edges --wiki-dir <wiki_dir>`
   b. `uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir <wiki_dir>`
   c. `uv run python tools/wiki_engine.py rebuild-open-questions --wiki-dir <wiki_dir>`
4. Run `tools/lint.py --suggest` and surface findings to user.

## Stub creation

If a forward link target doesn't exist yet, `pre-tool-use` creates a stub with `status: stub` and a TODO. The stub is logged. Don't block the ingest on this — a follow-up ingest can fill the stub.

## References

- `references/classifier.md` — artifact taxonomy
- `references/schema-evolution.md` — evolve flow
- `references/cross-reference-rules.md` — bidirectional canon
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-ingest/SKILL.md
git commit -m "feat(skills): wiki-ingest"
```

### Task 6.3: `skills/wiki-query/SKILL.md`

**File:** `skills/wiki-query/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-query
description: Use when the user asks a question that should be answered from the wiki rather than from general knowledge or the codebase. Triggers include "ask the wiki", "what does the wiki say about X", "summarize what we know about X", "find pages about X", "what decisions were made about X". Use after at least one `/wiki-ingest` has populated the wiki.
---

# wiki-query — ask the wiki

## Process

1. Read `<wiki_dir>/graph/context_brief.md` (loaded by session-start hook anyway).
2. Read `<wiki_dir>/index.md` to find candidate pages.
3. Identify 3-7 pages most relevant to the question. Read them.
4. Synthesize an answer that:
   a. Cites pages by `[[slug]]`.
   b. Distinguishes between settled facts (status: stable/accepted) and open questions.
   c. Flags contradictions if any.
5. Offer to save the answer to `<wiki_dir>/outputs/<slug>.md` (a fresh page) or as a section in an existing summary page.
6. Append `<wiki_dir>/log.md`: `## [date] query | <question excerpt> | answered from <N> pages`.

## When to save

- One-off conversational answer → don't save.
- Synthesis the user will reference later → save under `outputs/`.
- Update to an existing finding → suggest editing the existing page via `/wiki-ingest` or manual edit (then `/wiki-lint`).

## References

- `references/concept.md` — Karpathy's claim that index.md is sufficient up to ~100 sources
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-query/SKILL.md
git commit -m "feat(skills): wiki-query"
```

### Task 6.4: `skills/wiki-lint/SKILL.md`

**File:** `skills/wiki-lint/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-lint
description: Use when the user wants to verify wiki structural integrity, fix broken links, surface orphans, or check before commit. Triggers include "lint the wiki", "check the wiki", "fix wiki links", "wiki health check". Also auto-invoked by pre-commit hook and CI. Use the `--fix` flag to apply safe corrections.
---

# wiki-lint — wiki structural validation

## Process

1. Determine flags: `--fix` (apply safe fixes), `--suggest` (print suggestions), `--dry-run` (report-only, exit nonzero on errors).
2. Run: `uv run python tools/lint.py --wiki-dir <wiki_dir> [--fix|--suggest|--dry-run] --config <merged-config-path>`.
3. Surface findings to user, grouped by severity:
   - 🔴 errors (blocking): broken links, missing required frontmatter, duplicate slugs
   - 🟡 warnings: missing reverse links (auto-fixable), orphans, dependency rule violations, contract migration notes missing
4. If `--fix` was used, summarize what was auto-corrected.
5. Suggest manual follow-ups for non-auto-fixable items.

## Lint check inventory

See `references/cross-reference-rules.md` and `tools/lint.py` source for exact check definitions.

| Check | Severity | Auto-fix |
|---|---|---|
| broken-wikilink | 🔴 | no |
| missing-reverse-link | 🟡 | yes |
| orphan | 🟡 | no |
| missing-frontmatter-field | 🔴 | no |
| duplicate-slug | 🔴 | no |
| dependency-rule-violation | 🟡 | no |
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-lint/SKILL.md
git commit -m "feat(skills): wiki-lint"
```

### Task 6.5: `skills/wiki-evolve/SKILL.md`

**File:** `skills/wiki-evolve/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-evolve
description: Use when the user (or `/wiki-ingest`) needs to add a new entity type to the wiki schema. Triggers include "add type X to the wiki", "the wiki needs a new category for Y", or auto-invocation when ingest finds a no-match artifact. Pass `--generate-skill` to also produce a project-local skill that pre-classifies into the new slot.
---

# wiki-evolve — add an entity type

## Process

1. Collect type spec interactively (or from `/wiki-ingest` schema-evolve flow):
   - `name` (slug-friendly, lowercase, hyphenated)
   - `dir` (relative to wiki/, may include subdirs)
   - `frontmatter_required` (list)
   - `frontmatter_optional` (list)
   - `sections_required` (list)
   - Cross-reference rules (forward → reverse pairs, optional)

2. Show the proposed CLAUDE.md diff to the user. Confirm before writing.

3. Run: `uv run python -m scripts.add_entity_type` (calls `add_entity_type(target, spec, trigger)`).

4. Append `assets/frontmatter/<name>.yaml` to the target (so future ingests can use it).

5. Commit:
   ```bash
   git add CLAUDE.md wiki/ assets/frontmatter/
   git commit -m "[schema-change] add type: <name>"
   ```

6. If `--generate-skill <trigger-phrase>`: render `assets/child-skills/ingest-domain.j2` into `target/.claude/skills/wiki-ingest-<name>/SKILL.md`.

## Modes

- **gated** (default): require explicit confirmation
- **auto**: log and proceed; user can `git revert` if unhappy

## References

- `references/schema-evolution.md`
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-evolve/SKILL.md
git commit -m "feat(skills): wiki-evolve"
```

### Task 6.6: `skills/wiki-spawn-agent/SKILL.md`

**File:** `skills/wiki-spawn-agent/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-spawn-agent
description: Use when the user wants to add a Claude Code subagent that operates on the wiki — e.g. a maintainer, reviewer, or domain-specific agent. Triggers include "add an agent for X", "spawn a wiki agent", "create a subagent that does X with the wiki". Generates `.claude/agents/<name>.md` and optionally a companion skill. Out of scope: writing arbitrary agents unrelated to the wiki.
---

# wiki-spawn-agent — add a wiki-aware subagent

## Process

1. Ask the user for:
   - Agent name (e.g. `wiki-reviewer`, `domain-curator`)
   - Role description (1-2 sentences)
   - Which wiki skills the agent should use (subset of `/wiki-ingest`, `/wiki-query`, `/wiki-lint`, `/wiki-evolve`)
   - Whether to also generate a companion skill (yes/no)

2. Render `.claude/agents/<name>.md` with frontmatter and a body that:
   - States the role
   - Lists allowed tools (typically `Read`, `Edit`, `Bash`)
   - Lists which wiki skills to invoke
   - Notes that it MUST read `<wiki_dir>/graph/context_brief.md` at start

3. (Optional) If companion skill requested, render `.claude/skills/<name>/SKILL.md` with a description and process steps tailored to the role.

4. Append `<wiki_dir>/log.md`: `## [date] spawn-agent | <name> | role: <role>`.

5. Commit and print activation instructions to the user.

## Constraints

- The agent operates within the wiki — it does not bypass `pre-tool-use` validation.
- The agent MUST honor the mutability matrix in CLAUDE.md.
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-spawn-agent/SKILL.md
git commit -m "feat(skills): wiki-spawn-agent"
```

### Task 6.7: `skills/wiki-render/SKILL.md`

**File:** `skills/wiki-render/SKILL.md`

- [ ] **Step 1: Author the skill**

```markdown
---
name: wiki-render
description: Use when the user wants to refresh or regenerate the visual layer of the wiki — Obsidian config or static HTML. Triggers include "refresh obsidian config", "render wiki to html", "regenerate dashboards", "update vault settings". For initial bootstrap, `/wiki-init` already creates the Obsidian config; use this skill for refresh or HTML output.
---

# wiki-render — refresh wiki UI artifacts

## Modes

### `obsidian`

- Reads current preset+overlay config.
- Refreshes `.obsidian/graph.json` colors and filters to match the current page-type set.
- Ensures `community-plugins.json` enables Dataview.
- Idempotent — re-run safe.

### `html`

- Renders a static site to `dist/wiki/`:
  - `index.html` from `<wiki_dir>/index.md`
  - One HTML page per markdown file
  - Graph view via D3 (read from `graph/edges.jsonl`)
- Uses `markdown` Python library with `wikilinks` extension.
- Suitable for GitHub Pages.

## Process

1. Determine mode: `--mode obsidian` (default) | `--mode html`
2. For `obsidian`:
   - Re-render `.obsidian/graph.json` from current config.
   - Update `.obsidian/community-plugins.json` if needed.
3. For `html`:
   - `uv run python tools/render_html.py --wiki-dir <wiki_dir> --out dist/wiki/`
   - Print path to `dist/wiki/index.html`.

## Notes

`tools/render_html.py` is added at v0.2 — initial release ships `obsidian` mode only. The `html` mode is documented here for forward compatibility but the skill should refuse `--mode html` and point to `references/concept.md` until v0.2 lands.
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-render/SKILL.md
git commit -m "feat(skills): wiki-render"
```

---

## Phase 7 — Integration tests

### Task 7.1: Greenfield software-project + hexagonal end-to-end

**File:** `tests/integration/test_greenfield_software_hexagonal.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap

def test_greenfield_software_hexagonal(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="hexagonal",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="all", ci=True, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)

    # Hexagonal dirs created
    for sub in ["core/entities", "core/value-objects", "core/aggregates",
                "ports/inbound", "ports/outbound", "adapters/inbound",
                "adapters/outbound", "application", "contracts", "decisions"]:
        assert (tmp_path / "wiki" / sub).is_dir(), f"missing wiki/{sub}"
    # Hooks installed
    for hook in ["session-start.sh", "session-end.sh", "pre-tool-use.sh",
                 "post-tool-use.sh", "pre-commit.sh", "install-hooks.sh"]:
        assert (tmp_path / ".claude" / "hooks" / hook).exists()
    # CI workflows installed
    for wf in ["wiki-lint.yml", "wiki-review.yml", "wiki-rollup.yml"]:
        assert (tmp_path / ".github" / "workflows" / wf).exists()
    # CLAUDE.md mentions hexagonal
    assert "hexagonal" in (tmp_path / "CLAUDE.md").read_text()
    # Obsidian config
    assert (tmp_path / ".obsidian" / "graph.json").exists()
    # Tools copied
    assert (tmp_path / "tools" / "lint.py").exists()
    # Empty edges + empty context brief
    assert (tmp_path / "wiki" / "graph" / "edges.jsonl").read_text() == ""
```

- [ ] **Step 2: Run test — pass**

Run: `uv run pytest tests/integration/test_greenfield_software_hexagonal.py -v`
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_greenfield_software_hexagonal.py
git commit -m "test(integration): greenfield software-project + hexagonal"
```

### Task 7.2: Greenfield research preset

**File:** `tests/integration/test_greenfield_research.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap

def test_greenfield_research(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="omega-clone", project_description="research wiki",
        wiki_dir="wiki", preset="research", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="session", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    for d in ["papers", "concepts", "topics", "ideas", "experiments", "claims", "foundations", "summaries"]:
        assert (tmp_path / "wiki" / d).is_dir(), f"missing: wiki/{d}"
    assert "research" in (tmp_path / "CLAUDE.md").read_text()
    # CI not installed
    assert not (tmp_path / ".github").exists()
```

- [ ] **Step 2: Run + commit**

```bash
uv run pytest tests/integration/test_greenfield_research.py -v
git add tests/integration/test_greenfield_research.py
git commit -m "test(integration): greenfield research preset"
```

### Task 7.3: Existing-codebase auto-detect

**File:** `tests/integration/test_existing_codebase_autodetect.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
from scripts.interview import auto_detect_wiki_dir, InterviewConfig
from scripts.bootstrap import bootstrap

def test_existing_codebase_uses_dot_wiki(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text("{}")
    detected = auto_detect_wiki_dir(tmp_path)
    assert detected == ".wiki"

    cfg = InterviewConfig(
        project_name="legacy", project_description="d",
        wiki_dir=detected, preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="git", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    assert (tmp_path / ".wiki" / "modules").is_dir()
    assert (tmp_path / "src").is_dir()  # Existing source untouched
```

- [ ] **Step 2: Run + commit**

```bash
uv run pytest tests/integration/test_existing_codebase_autodetect.py -v
git add tests/integration/test_existing_codebase_autodetect.py
git commit -m "test(integration): existing codebase → .wiki/ auto-detect"
```

### Task 7.4: Upgrade preserves user wiki pages

**File:** `tests/integration/test_upgrade_preserves_wiki_pages.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap

def _cfg():
    return InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )

def test_re_bootstrap_preserves_wiki_content(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg())
    user = tmp_path / "wiki" / "modules" / "auth.md"
    user.write_text("---\ntitle: Auth\nslug: auth\nstatus: stable\n---\n# Auth\nMy notes\n")
    bootstrap(target=tmp_path, config=_cfg(), upgrade=True)
    assert "My notes" in user.read_text()
```

- [ ] **Step 2: Run + commit**

```bash
uv run pytest tests/integration/test_upgrade_preserves_wiki_pages.py -v
git add tests/integration/test_upgrade_preserves_wiki_pages.py
git commit -m "test(integration): upgrade preserves user wiki pages"
```

### Task 7.5: Lint clean after bootstrap (invariant)

**File:** `tests/integration/test_lint_clean_after_bootstrap.py`

- [ ] **Step 1: Write the test**

```python
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap
from tools.lint import run_all_checks
from tools._models import LintSeverity

def test_fresh_bootstrap_passes_lint_clean(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    findings = run_all_checks(tmp_path / "wiki", schema={}, dir_to_type={}, dependency_rules=[])
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    assert errors == [], f"fresh bootstrap should be lint-clean, found errors: {errors}"
```

- [ ] **Step 2: Run + commit**

```bash
uv run pytest tests/integration/test_lint_clean_after_bootstrap.py -v
git add tests/integration/test_lint_clean_after_bootstrap.py
git commit -m "test(integration): fresh bootstrap is lint-clean (invariant)"
```

---

## Phase 8 — Plugin packaging + final polish

### Task 8.1: Plugin self-CI

**File:** `.github/workflows/plugin-ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: plugin-ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv sync --dev
      - run: uv run pytest --cov=tools --cov=scripts --cov-report=term-missing
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/plugin-ci.yml
git commit -m "ci: add plugin self-test workflow"
```

### Task 8.2: README polish

**File:** `README.md`

- [ ] **Step 1: Expand README with full usage examples**

```markdown
# wiki-creator

A Claude Code plugin that bootstraps an LLM-maintained wiki into any project.

Inspired by:
- [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — three-layer raw/wiki/schema model.
- [OmegaWiki](https://github.com/skyllwt/OmegaWiki) — typed entities, edges, bidirectional enforcement.

## What you get

- Persistent agent memory: a markdown wiki that compounds over time
- Auto-generated context brief loaded at every session start
- Lint enforcement: broken links, missing reverses, orphans, dependency rules
- Schema evolution: new entity types added through ingest, never preempted
- Obsidian-compatible — open `wiki/` as a vault for graph view

## Install

```bash
claude plugins install wiki-creator
```

Requires Python 3.12+ and `uv` (install via `pipx install uv`).

## Quick start

In a project directory:

```
/wiki-init
```

Walks you through preset/overlay choice and renders the scaffolding. Then ingest:

```
/wiki-ingest raw/PRD.md raw/AUDIT_TASKS.md
```

Then ask:

```
/wiki-query "What modules does the auth feature touch?"
```

## Skills

- `/wiki-init` — bootstrap
- `/wiki-ingest` — raw → wiki
- `/wiki-query` — ask the wiki
- `/wiki-lint` — structural validation
- `/wiki-evolve` — add an entity type
- `/wiki-spawn-agent` — add a subagent
- `/wiki-render` — refresh Obsidian / generate HTML

## Design

See [`docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md`](docs/superpowers/specs/2026-04-28-wiki-creator-skill-design.md).

## Development

```bash
uv sync --dev
uv run pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: expand README with usage examples"
```

### Task 8.3: End-to-end smoke (manual)

- [ ] **Step 1: In a tmp directory, run the plugin manually**

```bash
mkdir /tmp/wiki-smoke && cd /tmp/wiki-smoke
git init
# Simulate /wiki-init by calling bootstrap directly with hard-coded config:
uv run python -c "
from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap
cfg = InterviewConfig(
    project_name='Smoke', project_description='Manual smoke test',
    wiki_dir='wiki', preset='software-project', overlay='hexagonal',
    custom_entity_types=None, i18n_languages=['en'],
    hooks='all', ci=False, schema_evolve_mode='gated',
)
bootstrap(target=Path('.'), config=cfg)
"
ls wiki/
cat CLAUDE.md | head -30
uv run python tools/lint.py --wiki-dir wiki --dry-run || echo "lint exit code: $?"
```

Expected:
- Tree with hexagonal dirs (core/, ports/, adapters/, application/, contracts/, decisions/, people/, tasks/)
- CLAUDE.md mentions "hexagonal"
- Lint clean (no errors, possibly 0 warnings)

- [ ] **Step 2: Verify Obsidian opens cleanly**

Open `/tmp/wiki-smoke/wiki/` in Obsidian. Graph view should render with no nodes (empty wiki) and the Dataview plugin should be enabled. No errors in console.

- [ ] **Step 3: Tear down**

```bash
rm -rf /tmp/wiki-smoke
```

- [ ] **Step 4: Commit any fixes discovered during smoke**

(If smoke surfaces issues, write a TDD-style failing test, fix, commit.)

---

## Self-review checklist

After completing all tasks:

**Spec coverage** — every section of the spec must map to at least one task:

| Spec section | Implementing task(s) |
|---|---|
| §1 Goal — 7-skill plugin | Phase 6 (T6.1-T6.7) |
| §3 Karpathy + OmegaWiki | T1.1 (Edge model), T2.3 (concept.md), T3.4 (context_brief), T3.7 (missing-reverse) |
| §4 #1 Mono-plugin | T0.1 (plugin.json) |
| §4 #2 Agents out-of-band | T6.6 (wiki-spawn-agent) |
| §4 #3 Mutability layers | T2.3 (cross-reference-rules.md), T4.1 (CLAUDE.md template) |
| §4 #4 Obsidian-first | T4.3 (obsidian config), T6.7 (wiki-render) |
| §4 #5 Python 3.12 + uv | T0.1 (pyproject.toml) |
| §4 #7 Auto-detect wiki dir | T5.1 (auto_detect_wiki_dir) |
| §5 Mutability matrix | T4.1 (CLAUDE.md template renders matrix) |
| §6 Plugin structure | T0.1 + Phase 4-6 (whole tree built) |
| §7 Bootstrap flow | T5.2 (bootstrap.py) |
| §8 Op skills | Phase 6 |
| §8 Lint checks | T3.6-T3.9 |
| §8 Schema-evolve flow | T5.3 (add_entity_type), T6.5 (wiki-evolve skill) |
| §9 Hooks (all 3 levels) | T4.3 (assets/hooks + workflows) |
| §10 Testing strategy | Phase 7 |
| §11 Trigger phrases | Each SKILL.md description in Phase 6 |
| §13 Open questions deferred | Documented in spec; each is implementable post-v0.1 |

**Placeholder scan:** No "TBD"/"TODO"/"implement later" in any task body. (One TODO appears in `tools/classify.py` Step 3 noting that LLM fallback is a future enhancement — this is intentional and scoped.)

**Type consistency:** Cross-checked names:
- `InterviewConfig` — defined T5.1, used T5.2, T7.1-T7.5
- `Page`, `Edge`, `LintFinding`, `LintSeverity` — defined T1.1, used throughout
- `EDGE_KEYS`, `REVERSE_OF` — defined T3.3, used T3.7, T3.9 (apply_fixes)
- `bootstrap(target, config, upgrade)` — defined T5.2, used T7.x
- `add_entity_type(target, spec, trigger)` — defined T5.3, used T6.5
- `auto_detect_wiki_dir(cwd)` — defined T5.1, used T7.3
- `run_all_checks` / `apply_fixes` — defined T3.9, used T7.5

All consistent.

**Coverage gaps:** None identified. All spec requirements have at least one implementing task.

---


