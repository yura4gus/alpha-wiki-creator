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
