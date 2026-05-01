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
        skills=["/alpha-wiki:init", "/alpha-wiki:ingest", "/alpha-wiki:query", "/alpha-wiki:lint"],
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
    assert "/alpha-wiki:review" in out
    assert "/alpha-wiki:rollup" in out
    assert "$alpha-wiki-status" in out
    assert "Color is not a cluster" in out
    assert "`wiki:review`" not in out
    assert "/wiki-review" not in out
