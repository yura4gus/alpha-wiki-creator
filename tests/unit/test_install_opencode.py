import json
from pathlib import Path

import pytest

from scripts.install_opencode import install_opencode


def snapshot(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


def test_opencode_install_dry_run_repeat_and_native_discovery_files(tmp_path):
    config = tmp_path / "opencode"
    preview = install_opencode(config, dry_run=True)
    assert not config.exists()
    assert preview["skills"] == preview["commands"] == 16
    result = install_opencode(config)
    assert result["writes"] == preview["writes"]
    assert not (config / "opencode.json").exists()
    skill = (config / "skills/alpha-wiki-doctor/SKILL.md").read_text()
    assert "/alpha-wiki/doctor" in skill
    assert str(config / "alpha-wiki/references/opencode-adapter.md") in skill
    command = (config / "commands/alpha-wiki/doctor.md").read_text()
    assert "subagent: false" in command and "$ARGUMENTS" in command
    before = snapshot(config)
    repeated = install_opencode(config, upgrade=True)
    assert not repeated["writes"] and not repeated["manifest_changed"]
    assert snapshot(config) == before


def test_opencode_upgrade_preserves_modified_user_files_before_any_writes(tmp_path):
    install_opencode(tmp_path)
    skill = tmp_path / "skills/alpha-wiki-doctor/SKILL.md"
    skill.write_text(skill.read_text() + "\nUser instructions.\n")
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="user modified"):
        install_opencode(tmp_path, upgrade=True)
    assert snapshot(tmp_path) == before


def test_opencode_doctor_checks_managed_skill_integrity(tmp_path, monkeypatch):
    from tools.doctor import _check_opencode
    install_opencode(tmp_path)
    monkeypatch.setenv("ALPHA_WIKI_OPENCODE_CONFIG_DIR", str(tmp_path))
    checks = _check_opencode()
    assert next(check for check in checks if check.name == "opencode adapter").status == "PASS"
    (tmp_path / "commands/alpha-wiki/doctor.md").write_text("modified")
    checks = _check_opencode()
    assert next(check for check in checks if check.name == "opencode adapter").status == "FAIL"
