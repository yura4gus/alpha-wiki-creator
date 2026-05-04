from pathlib import Path

from click.testing import CliRunner

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig
from scripts.install_codex import install_codex_skills
from tools.doctor import cli, doctor_report, run_doctor


def _bootstrap_project(tmp_path: Path) -> Path:
    cfg = InterviewConfig(
        project_name="demo",
        project_description="A demo wiki",
        wiki_dir="wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="all",
        ci=True,
        schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    return tmp_path


def test_doctor_passes_bootstrapped_project_without_failures(tmp_path: Path):
    project = _bootstrap_project(tmp_path)

    result = run_doctor(project, platform="claude", refresh=True)

    assert not result.failures
    assert any(check.name == "graph refresh" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "github workflows" and check.status == "PASS" for check in result.checks)


def test_doctor_verifies_claude_and_codex_runtime_paths(tmp_path: Path, monkeypatch):
    project = _bootstrap_project(tmp_path / "project")
    codex_home = tmp_path / "codex-home"
    install_codex_skills(codex_home / "skills")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    result = run_doctor(project, platform="both", refresh=True)

    assert not result.failures
    assert any(check.name == "claude hooks" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "github workflows" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "codex skills" and check.status == "PASS" for check in result.checks)


def test_doctor_report_surfaces_missing_wiki(tmp_path: Path):
    report = doctor_report(tmp_path, platform="claude")

    assert "FAIL `wiki directory`" in report
    assert "Run /alpha-wiki:init first" in report


def test_doctor_cli_exits_nonzero_on_failures(tmp_path: Path):
    result = CliRunner().invoke(cli, ["--project-dir", str(tmp_path), "--platform", "claude"])

    assert result.exit_code == 1
    assert "Alpha-Wiki Doctor" in result.output
    assert "FAIL `wiki directory`" in result.output
