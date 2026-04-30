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
    assert (tmp_path / ".alpha-wiki" / "config.yaml").exists()
    claude = (tmp_path / "CLAUDE.md").read_text()
    assert "/alpha-wiki:review" in claude
    assert "/alpha-wiki:rollup" in claude


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
