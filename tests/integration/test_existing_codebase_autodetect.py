from pathlib import Path
from scripts.interview import auto_detect_wiki_dir, InterviewConfig
from scripts.bootstrap import bootstrap

def test_existing_codebase_uses_visible_wiki_dir(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text("{}")
    detected = auto_detect_wiki_dir(tmp_path)
    assert detected == "wiki"

    cfg = InterviewConfig(
        project_name="legacy", project_description="d",
        wiki_dir=detected, preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="git", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    assert (tmp_path / "wiki" / "modules").is_dir()
    assert (tmp_path / "wiki" / ".obsidian" / "graph.json").exists()
    assert (tmp_path / "src").is_dir()  # Existing source untouched
