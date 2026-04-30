from pathlib import Path

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig


def _cfg(wiki_dir: str = "wiki") -> InterviewConfig:
    return InterviewConfig(
        project_name="demo",
        project_description="d",
        wiki_dir=wiki_dir,
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="none",
        ci=False,
        schema_evolve_mode="gated",
    )


def test_bootstrap_preserves_existing_project_files(tmp_path: Path):
    originals = {
        "CLAUDE.md": "# Existing agent rules\n",
        "README.md": "# Existing readme\n",
        "pyproject.toml": "[project]\nname = 'existing'\n",
        ".gitignore": "dist/\n",
        ".env.example": "EXISTING=1\n",
    }
    for name, content in originals.items():
        (tmp_path / name).write_text(content)

    report = bootstrap(target=tmp_path, config=_cfg())

    for name, content in originals.items():
        assert (tmp_path / name).read_text() == content
    assert len(report.skipped) == len(originals)
    assert (tmp_path / ".alpha-wiki" / "bootstrap-report.md").exists()
    assert (tmp_path / "wiki" / "index.md").exists()


def test_bootstrap_dry_run_reports_conflicts_without_writing(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Existing readme\n")

    report = bootstrap(target=tmp_path, config=_cfg(), dry_run=True)

    assert report.dry_run is True
    assert len(report.skipped) == 1
    assert "README.md" in report.skipped[0].path
    assert not (tmp_path / "wiki").exists()
    assert not (tmp_path / ".alpha-wiki").exists()


def test_upgrade_preserves_graph_artifacts(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg())
    graph = tmp_path / "wiki" / "graph"
    (graph / "edges.jsonl").write_text('{"source":"a","target":"b","relation":"depends_on"}\n')
    (graph / "context_brief.md").write_text("# Custom brief\n")
    (graph / "open_questions.md").write_text("# Custom questions\n")

    bootstrap(target=tmp_path, config=_cfg(), upgrade=True)

    assert "source" in (graph / "edges.jsonl").read_text()
    assert "Custom brief" in (graph / "context_brief.md").read_text()
    assert "Custom questions" in (graph / "open_questions.md").read_text()
