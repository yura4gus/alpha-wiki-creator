from pathlib import Path
import json

import pytest

from scripts.bootstrap import upgrade_runtime_assets
from scripts.bootstrap_cli import bootstrap_project


def test_runtime_upgrade_preserves_user_schema_contracts_and_hook_routing(tmp_path: Path):
    bootstrap_project(tmp_path, wiki_dir=".wiki", hooks="all", ci=True)
    config = tmp_path / ".alpha-wiki/config.yaml"
    config.write_text(config.read_text() + "\nuser_schema_marker: preserve-me\n")
    contract = tmp_path / "CLAUDE.md"
    contract.write_text(contract.read_text() + "\nUser-owned project instructions.\n")
    routing = tmp_path / ".codex/hooks.json"
    routing.write_text(routing.read_text() + "\n")
    wiki = tmp_path / ".wiki"
    (wiki / "graph/edges.jsonl").write_text("preserve generated snapshot\n")
    protected = [config, contract, routing, tmp_path / "AGENTS.md", tmp_path / "README.md",
                 tmp_path / ".github/workflows/wiki-lint.yml", wiki / "log.md",
                 wiki / "graph/edges.jsonl"]
    before = {path: path.read_bytes() for path in protected}
    (tmp_path / ".alpha-wiki/run.py").unlink()

    report = upgrade_runtime_assets(tmp_path)

    assert report.written
    assert (tmp_path / ".alpha-wiki/run.py").is_file()
    assert not (tmp_path / "pyproject.toml").exists()
    assert 'WIKI_DIR="${WIKI_DIR:-.wiki}"' in (tmp_path / ".claude/hooks/post-tool-use.sh").read_text()
    for path, content in before.items():
        assert path.read_bytes() == content, path


def test_runtime_only_dry_run_writes_nothing(tmp_path: Path):
    bootstrap_project(tmp_path)
    (tmp_path / ".alpha-wiki/run.py").unlink()
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    report = upgrade_runtime_assets(tmp_path, dry_run=True)

    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert report.planned and not report.written
    assert after == before


def snapshot(root: Path):
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
        for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("platform", ["claude", "codex"])
def test_runtime_upgrade_restores_only_missing_configured_hooks(tmp_path: Path, platform: str):
    bootstrap_project(tmp_path, wiki_dir=".wiki", hooks="session")
    hook = tmp_path / (".claude/hooks/session-start.sh" if platform == "claude"
                       else ".codex/hooks/alpha_wiki_hook.py")
    original = hook.read_bytes()
    hook.unlink()
    # An unconfigured missing script must stay absent.
    unconfigured = tmp_path / ".claude/hooks/pre-commit.sh"
    custom = tmp_path / ".claude/hooks/session-end.sh"
    custom.write_text("#!/bin/sh\n# User-owned hook, never replace.\nexit 0\n")
    custom.chmod(0o700)
    before = snapshot(tmp_path)

    planned = upgrade_runtime_assets(tmp_path, dry_run=True)

    assert planned.planned == [str(hook)]
    assert not planned.written
    assert snapshot(tmp_path) == before
    applied = upgrade_runtime_assets(tmp_path)
    assert applied.written == [str(hook)]
    assert hook.read_bytes() == original
    assert hook.stat().st_mode & 0o111 == 0o111
    assert not unconfigured.exists()
    assert {key: value for key, value in snapshot(tmp_path).items() if key in before} == before

    after = snapshot(tmp_path)
    repeated = upgrade_runtime_assets(tmp_path)
    assert not repeated.planned and not repeated.written
    assert snapshot(tmp_path) == after


def routing(path: Path, command: str, kind: str = "command"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [
        {"type": kind, "command": command}
    ]}]}}))


@pytest.mark.parametrize("command", [
    '"$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh"',
    'bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-start.sh"',
    'sh ./.claude/hooks/session-start.sh',
    '.claude/hooks/session-start.sh',
])
def test_claude_project_settings_can_request_missing_hook(tmp_path: Path, command: str):
    bootstrap_project(tmp_path, hooks="none")
    routing(tmp_path / ".claude/settings.json", command)
    hook = tmp_path / ".claude/hooks/session-start.sh"
    report = upgrade_runtime_assets(tmp_path)
    assert report.written == [str(hook)]
    assert hook.is_file()


@pytest.mark.parametrize("command,kind", [
    ('echo .claude/hooks/session-start.sh', "command"),
    ('cat .claude/hooks/session-start.sh', "command"),
    ('# .claude/hooks/session-start.sh', "command"),
    ('.claude/hooks/session-start.sh.backup', "command"),
    ('/other/project/.claude/hooks/session-start.sh', "command"),
    ('$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh', "prompt"),
])
def test_unrelated_commands_do_not_register_hooks(tmp_path: Path, command: str, kind: str):
    bootstrap_project(tmp_path, hooks="none")
    routing(tmp_path / ".claude/settings.local.json", command, kind)
    before = snapshot(tmp_path)
    assert not upgrade_runtime_assets(tmp_path).written
    assert snapshot(tmp_path) == before
    assert not (tmp_path / ".claude/hooks/session-start.sh").exists()


def test_no_routing_means_no_hook_creation_or_existing_hook_overwrite(tmp_path: Path):
    bootstrap_project(tmp_path, hooks="none")
    hook = tmp_path / ".codex/hooks/alpha_wiki_hook.py"
    hook.parent.mkdir(parents=True)
    hook.write_text("# custom, unconfigured adapter\n")
    before = snapshot(tmp_path)
    assert not upgrade_runtime_assets(tmp_path).written
    assert snapshot(tmp_path) == before
    assert not (tmp_path / ".claude/hooks").exists()


@pytest.mark.parametrize("platform", ["claude", "codex"])
def test_invalid_routing_fails_before_any_upgrade_writes(tmp_path: Path, platform: str):
    bootstrap_project(tmp_path, hooks="session")
    path = tmp_path / (".claude/settings.local.json" if platform == "claude" else ".codex/hooks.json")
    path.write_text("{not valid JSON")
    (tmp_path / ".alpha-wiki/run.py").unlink()
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="hook routing"):
        upgrade_runtime_assets(tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("platform", ["claude", "codex"])
@pytest.mark.parametrize("occupied", ["directory", "dangling-symlink", "parent-symlink"])
def test_hook_recovery_does_not_follow_symlinks_or_replace_paths(tmp_path: Path, platform: str, occupied: str):
    project = tmp_path / "project"
    bootstrap_project(project, hooks="session")
    hook = project / (".claude/hooks/session-start.sh" if platform == "claude"
                      else ".codex/hooks/alpha_wiki_hook.py")
    hook.unlink()
    outside = tmp_path / "outside"
    outside.mkdir()
    if occupied == "directory":
        hook.mkdir()
    elif occupied == "dangling-symlink":
        hook.symlink_to(outside / hook.name)
    else:
        for sibling in hook.parent.iterdir():
            sibling.unlink()
        hook.parent.rmdir()
        hook.parent.symlink_to(outside, target_is_directory=True)

    report = upgrade_runtime_assets(project)
    assert str(hook) not in report.written
    assert not list(outside.iterdir())
    assert any(conflict.path == str(hook) for conflict in report.skipped)
