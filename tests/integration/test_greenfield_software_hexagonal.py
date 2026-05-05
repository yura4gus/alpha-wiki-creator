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
    assert (tmp_path / "wiki" / ".obsidian" / "graph.json").exists()
    # Tools copied
    assert (tmp_path / "tools" / "lint.py").exists()
    # Empty edges + empty context brief
    assert (tmp_path / "wiki" / "graph" / "edges.jsonl").read_text() == ""
