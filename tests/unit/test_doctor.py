import json
from pathlib import Path

from click.testing import CliRunner

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig
from scripts.install_codex import install_codex
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
    codex_home = tmp_path / ".codex"
    codex_skills = tmp_path / ".agents" / "skills"
    codex_plugin = tmp_path / "plugins" / "alpha-wiki"
    codex_marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    install_codex(
        skills_target=codex_skills,
        plugin_dir=codex_plugin,
        marketplace_path=codex_marketplace,
        activate=False,
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("ALPHA_WIKI_CODEX_SKILLS_DIR", str(codex_skills))
    monkeypatch.setenv("ALPHA_WIKI_CODEX_PLUGIN_DIR", str(codex_plugin))
    monkeypatch.setenv("ALPHA_WIKI_CODEX_MARKETPLACE", str(codex_marketplace))

    result = run_doctor(project, platform="both", refresh=True)

    assert not result.failures
    assert any(check.name == "claude hooks" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "github workflows" and check.status == "PASS" for check in result.checks)
    assert any(
        check.name == "codex skill surface"
        and check.status == "PASS"
        and "plugin-only mode" in check.message
        for check in result.checks
    )
    assert any(check.name == "codex plugin package" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "codex plugin command migration" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "codex project instructions" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "codex project hooks" and check.status == "PASS" for check in result.checks)

    hooks_path = project / ".codex" / "hooks.json"
    hooks = json.loads(hooks_path.read_text())
    hooks["hooks"].pop("SubagentStart")
    hooks_path.write_text(json.dumps(hooks))

    stale_result = run_doctor(project, platform="codex")
    hook_check = next(check for check in stale_result.checks if check.name == "codex project hooks")
    assert hook_check.status == "WARN"
    assert "SubagentStart" in hook_check.message


def test_doctor_report_surfaces_missing_wiki(tmp_path: Path):
    report = doctor_report(tmp_path, platform="claude")

    assert "FAIL `wiki directory`" in report
    assert "Run /alpha-wiki:init first" in report


def test_doctor_does_not_pass_empty_claude_hooks_directory(tmp_path: Path):
    project = _bootstrap_project(tmp_path)
    for hook in (project / ".claude" / "hooks").glob("*.sh"):
        hook.unlink()

    result = run_doctor(project, platform="claude")

    check = next(item for item in result.checks if item.name == "claude hooks")
    assert check.status == "WARN"
    assert "contains no hook scripts" in check.message


def test_doctor_cli_exits_nonzero_on_failures(tmp_path: Path):
    result = CliRunner().invoke(cli, ["--project-dir", str(tmp_path), "--platform", "claude"])

    assert result.exit_code == 1
    assert "Alpha-Wiki Doctor" in result.output
    assert "FAIL `wiki directory`" in result.output


def test_codex_doctor_uses_codex_operation_hints(tmp_path: Path):
    result = run_doctor(tmp_path, platform="codex")

    config = next(check for check in result.checks if check.name == "config")
    wiki = next(check for check in result.checks if check.name == "wiki directory")
    assert "$alpha-wiki:init" in (config.action or "")
    assert "$alpha-wiki:init" in (wiki.action or "")
    assert "/alpha-wiki:init" not in (wiki.action or "")
