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
