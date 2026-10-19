# tests/unit/test_templates_render.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ASSETS = Path(__file__).parents[2] / "assets"

def _env():
    return Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)

def test_agents_md_renders_the_single_contract():
    env = _env()
    out = env.get_template("agents-md.j2").render(
        project_name="Demo", project_description="A demo wiki",
        wiki_dir="wiki", preset="software-project", overlay="hexagonal",
        date="2026-04-28",
        codex_skills=["$alpha-wiki:init", "$alpha-wiki:doctor"],
    )
    assert "Demo" in out
    assert "hexagonal" in out
    assert "**Wiki dir:** `wiki/`" in out
    assert ".alpha-wiki/config.yaml" in out
    assert "$alpha-wiki:doctor" in out
    assert ".claude/CLAUDE.md" in out
    assert "## Page Types" not in out

def test_index_md_renders():
    out = _env().get_template("index-md.j2").render(
        project_name="Demo", date="2026-04-28",
        entity_types=[{"name": "module", "dir": "modules"}, {"name": "decision", "dir": "decisions"}],
    )
    assert "## Module" in out or "## module" in out.lower()

def test_claude_adapter_imports_the_single_contract_without_copying_it():
    text = _env().get_template("claude-md.j2").render()
    assert "@../AGENTS.md" in text
    assert "Page Types" not in text

def test_generated_contract_uses_target_tracker_not_plugin_roadmap():
    text = _env().get_template("agents-md.j2").render(wiki_dir=".memory")
    assert "docs/roadmap-execution.md" not in text
    assert "target project's existing roadmap" in text

def test_log_md_renders_first_entry():
    out = _env().get_template("log-md.j2").render(date="2026-04-28", preset="software-project", overlay="hexagonal")
    assert "[2026-04-28]" in out
    assert "bootstrap" in out

def test_generated_readme_uses_alpha_wiki_ci_commands():
    out = _env().get_template("readme.j2").render(
        project_name="Demo",
        project_description="A demo wiki",
        wiki_dir=".wiki",
        date="2026-04-30",
        preset="software-project",
        overlay="none",
        ci=True,
    )
    assert "/alpha-wiki:lint" in out
    assert "/alpha-wiki:doctor" in out
    assert "/alpha-wiki:review" in out
    assert "/alpha-wiki:rollup" in out
    assert "$alpha-wiki-doctor" in out
    assert "$alpha-wiki-status" in out
    assert "Color is not a cluster" in out
    assert "`wiki:review`" not in out
    assert "/wiki-review" not in out


def test_generated_gitignore_ignores_obsidian_runtime_state():
    out = _env().get_template("gitignore.j2").render(wiki_dir="wiki")

    assert ".obsidian/" in out
    assert "wiki/.obsidian/app.json" in out
    assert "wiki/.obsidian/graph.json" in out
    assert "wiki/.obsidian/workspace.json" in out
