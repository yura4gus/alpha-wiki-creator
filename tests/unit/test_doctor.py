import json
from pathlib import Path

import pytest

from click.testing import CliRunner

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig
from scripts.install_codex import install_codex
from tools.doctor import cli, doctor_report, run_doctor


def test_hook_smoke_uses_configured_interpreter_and_wiki_path(tmp_path, monkeypatch):
    import subprocess
    from tools.doctor import _check_codex_hook_runtime
    project = _bootstrap_project(tmp_path)
    path = project / ".codex/hooks.json"
    routing = json.loads(path.read_text())
    for event in ("PreToolUse", "PostToolUse"):
        hook = routing["hooks"][event][0]["hooks"][0]
        hook["command"] = hook["command"].replace("python3 ", "/custom/bin/python3 ").replace('"wiki"', '".wiki"')
    path.write_text(json.dumps(routing))
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(subprocess, "run", run)
    check = _check_codex_hook_runtime(project, project / ".codex/hooks/alpha_wiki_hook.py")
    assert check.status == "PASS"
    assert len(calls) == 2
    assert all(command[0] == "/custom/bin/python3" and command[-1] == ".wiki" for command in calls)


@pytest.mark.parametrize("exit_code,stdout,stderr", [
    (1, "", "ImportError: cannot import name 'UTC' from 'datetime'"),
    (0, '{"systemMessage":"Alpha-Wiki hook skipped after an unexpected TypeError."}', ""),
])
def test_hook_smoke_reports_import_errors_and_advisory_failures(tmp_path, monkeypatch, exit_code, stdout, stderr):
    import subprocess
    from tools.doctor import _check_codex_hook_runtime
    project = _bootstrap_project(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, exit_code, stdout, stderr))
    check = _check_codex_hook_runtime(project, project / ".codex/hooks/alpha_wiki_hook.py")
    assert check.status == "FAIL"
    assert "PreToolUse via python3" in check.message
    assert "--refresh-hooks" in check.action


def test_hook_smoke_does_not_execute_custom_shell_wrappers(tmp_path, monkeypatch):
    import subprocess
    from tools.doctor import _check_codex_hook_runtime
    project = _bootstrap_project(tmp_path)
    path = project / ".codex/hooks.json"
    routing = json.loads(path.read_text())
    routing["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "sh -c 'touch /tmp/should-not-run'"
    path.write_text(json.dumps(routing))
    def run(*args, **kwargs):
        pytest.fail("custom wrapper must not run")
    monkeypatch.setattr(subprocess, "run", run)
    assert _check_codex_hook_runtime(project, project / ".codex/hooks/alpha_wiki_hook.py").status == "WARN"


@pytest.mark.parametrize("value", ["null", "{}"])
def test_doctor_reports_invalid_entity_list_without_traceback(tmp_path, value):
    from tools.doctor import _check_project_config
    config = tmp_path / ".alpha-wiki/config.yaml"
    config.parent.mkdir()
    config.write_text(f"entity_types: {value}\n")
    checks = _check_project_config(tmp_path, "both")
    assert checks[0].status == "FAIL"
    assert "entity_types list" in checks[0].message


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


def test_doctor_reports_broken_isolated_runtime_with_exact_diagnostic(tmp_path: Path, monkeypatch):
    import subprocess
    from tools.doctor import _check_project_runtime

    project = _bootstrap_project(tmp_path)
    python = project / ".alpha-wiki/runtime/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, "", "ModuleNotFoundError: No module named 'click'\n"))

    check = _check_project_runtime(project)

    assert check.status == "FAIL"
    assert "ModuleNotFoundError: No module named 'click'" in check.message
    assert ".alpha-wiki/runtime/.venv" in check.action
    assert "pip install" not in check.action


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
    assert any(check.name == "project instructions" and check.status == "PASS" for check in result.checks)
    assert any(check.name == "claude contract adapter" and check.status == "PASS" for check in result.checks)
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


def test_existing_custom_adapter_is_preserved_and_needs_explicit_merge(tmp_path):
    project = _bootstrap_project(tmp_path)
    adapter = project / ".claude/CLAUDE.md"
    adapter.write_text("# Existing user adapter\n")
    original = adapter.read_bytes()
    _bootstrap_project(project)
    assert adapter.read_bytes() == original
    check = next(item for item in run_doctor(project, platform="claude").checks
                 if item.name == "claude contract adapter")
    assert check.status == "WARN"
    assert "@../AGENTS.md" in check.action


def test_config_wiki_dir_takes_precedence_and_old_claude_metadata_still_works(tmp_path):
    import yaml
    from tools.doctor import _resolve_wiki_dir
    project = _bootstrap_project(tmp_path)
    (project / "AGENTS.md").write_text("# User instructions without path metadata\n")
    (project / "CLAUDE.md").write_text("**Wiki dir:** `.legacy/`\n")
    config = project / ".alpha-wiki/config.yaml"
    data = yaml.safe_load(config.read_text())
    assert _resolve_wiki_dir(project, None) == project / "wiki"
    data.pop("wiki_dir")
    config.write_text(yaml.safe_dump(data))
    assert _resolve_wiki_dir(project, None) == project / ".legacy"
    data["wiki_dir"] = "../outside"
    config.write_text(yaml.safe_dump(data))
    result = run_doctor(project, platform="claude", refresh=True)
    assert any(item.name == "wiki location" and item.status == "FAIL" for item in result.checks)


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


def test_doctor_reports_malformed_document_policy_without_traceback(tmp_path: Path):
    from tools.doctor import _check_project_config

    (tmp_path / ".alpha-wiki").mkdir()
    (tmp_path / ".alpha-wiki/config.yaml").write_text(
        "entity_types: []\ndocument_governance: [invalid]\n"
    )
    checks = _check_project_config(tmp_path, "codex")
    assert any(check.name == "document governance" and check.status == "FAIL" for check in checks)
