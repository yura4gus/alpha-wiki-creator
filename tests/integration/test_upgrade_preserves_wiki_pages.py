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
