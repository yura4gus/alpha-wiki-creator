from pathlib import Path
import sys

import yaml

import json
import pytest

from scripts.install_codex import (
    cli,
    ensure_personal_marketplace,
    find_managed_codex_skills,
    install_codex,
    install_codex_skills,
    remove_managed_codex_skills,
    transform_skill_for_codex,
)


def test_transform_skill_for_codex_prefixes_name_and_maps_command():
    text = """---
name: init
description: "Bootstrap a wiki"
---

# wiki:init
"""

    out = transform_skill_for_codex(text, "init")

    assert "name: alpha-wiki-init" in out
    assert "Codex adapter for Alpha-Wiki `init`" in out
    assert "Invoke this workflow as `$alpha-wiki-init`" in out
    assert "$alpha-wiki-init" in out
    _, frontmatter, _ = out.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert data["name"] == "alpha-wiki-init"
    assert data["description"].startswith("Codex adapter for Alpha-Wiki")


def test_install_codex_skills_writes_prefixed_skill_set(tmp_path: Path):
    installed = install_codex_skills(tmp_path)

    assert len(installed) == 16
    assert (tmp_path / "alpha-wiki-init" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-doctor" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-query" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-audit-project" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-orchestrate" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-release-check" / "SKILL.md").exists()
    assert "name: alpha-wiki-doctor" in (tmp_path / "alpha-wiki-doctor" / "SKILL.md").read_text()
    assert "name: alpha-wiki-status" in (tmp_path / "alpha-wiki-status" / "SKILL.md").read_text()


def test_transform_plugin_skill_keeps_name_and_maps_namespaced_commands(tmp_path: Path):
    text = """---
name: init
description: "Bootstrap a wiki"
---

Run /alpha-wiki:status after init.
"""

    out = transform_skill_for_codex(text, "init", style="plugin", runtime_root=tmp_path)

    assert "name: init" in out
    assert "name: alpha-wiki-init" not in out
    assert "Invoke this workflow as `$alpha-wiki:init`" in out
    assert "$alpha-wiki:status" in out
    assert str(tmp_path) in out


def test_install_codex_builds_plugin_and_personal_marketplace(tmp_path: Path):
    skills_target = tmp_path / ".agents" / "skills"
    result = install_codex(
        skills_target=skills_target,
        plugin_dir=tmp_path / "plugins" / "alpha-wiki",
        marketplace_path=tmp_path / ".agents" / "plugins" / "marketplace.json",
        activate=False,
    )

    assert result.skills == []
    assert not skills_target.exists()
    assert result.plugin_dir == tmp_path / "plugins" / "alpha-wiki"
    manifest = json.loads((result.plugin_dir / ".codex-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "alpha-wiki"
    assert manifest["version"].startswith("0.6.0+codex.local-")
    assert len(list((result.plugin_dir / "skills").glob("*/SKILL.md"))) == 16
    assert not (result.plugin_dir / "commands").exists()
    assert (result.plugin_dir / "docs" / "project-audit.md").exists()
    assert (result.plugin_dir / "docs" / "codex-adapter.md").exists()
    assert (
        result.plugin_dir
        / "docs"
        / "examples"
        / "codex-parallel-audit-prompt.md"
    ).exists()
    assert (
        result.plugin_dir
        / "references"
        / "codex-subagent-orchestration.md"
    ).exists()
    assert (result.plugin_dir / "tools" / "worktree_snapshot.py").exists()
    assert (result.plugin_dir / "tools" / "release_check.py").exists()
    assert not list(result.plugin_dir.rglob("__pycache__"))
    marketplace = json.loads((tmp_path / ".agents" / "plugins" / "marketplace.json").read_text())
    entry = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == "alpha-wiki")
    assert entry["source"]["path"] == "./plugins/alpha-wiki"


def test_install_codex_can_opt_into_standalone_fallback(tmp_path: Path):
    result = install_codex(
        skills_target=tmp_path / ".agents" / "skills",
        plugin_dir=tmp_path / "plugins" / "alpha-wiki",
        marketplace_path=tmp_path / ".agents" / "plugins" / "marketplace.json",
        install_standalone=True,
        install_plugin=False,
        activate=False,
    )

    assert len(result.skills) == 16
    assert result.plugin_dir is None


def test_install_codex_rejects_plugin_and_standalone_together(tmp_path: Path):
    with pytest.raises(ValueError, match="cannot be installed together"):
        install_codex(
            skills_target=tmp_path / ".agents" / "skills",
            plugin_dir=tmp_path / "plugins" / "alpha-wiki",
            marketplace_path=tmp_path / ".agents" / "plugins" / "marketplace.json",
            install_standalone=True,
            install_plugin=True,
            activate=False,
        )


def test_standalone_cli_does_not_install_plugin(tmp_path: Path, monkeypatch):
    target = tmp_path / ".agents" / "skills"
    plugin_dir = tmp_path / "plugins" / "alpha-wiki"
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install_codex.py",
            "--standalone",
            "--target",
            str(target),
            "--plugin-dir",
            str(plugin_dir),
            "--marketplace-path",
            str(marketplace),
            "--no-activate",
        ],
    )

    cli()

    assert len(list(target.glob("alpha-wiki-*/SKILL.md"))) == 16
    assert not plugin_dir.exists()
    assert not marketplace.exists()


def test_remove_managed_codex_skills_preserves_unmanaged_paths(tmp_path: Path):
    install_codex_skills(tmp_path)
    unmanaged = tmp_path / "alpha-wiki-custom"
    unmanaged.mkdir()
    (unmanaged / "SKILL.md").write_text(
        "---\nname: alpha-wiki-custom\ndescription: User-owned skill\n---\n"
    )

    planned = find_managed_codex_skills(tmp_path)
    removed = remove_managed_codex_skills(tmp_path)

    assert len(planned) == 16
    assert removed == planned
    assert unmanaged.exists()
    assert not list(path for path in tmp_path.glob("alpha-wiki-*") if path != unmanaged)


def test_custom_marketplace_path_resolves_plugin_relative_to_its_directory(tmp_path: Path):
    marketplace_path = tmp_path / "marketplace.json"
    plugin_dir = tmp_path / "alpha-wiki"

    ensure_personal_marketplace(marketplace_path, plugin_dir)

    marketplace = json.loads(marketplace_path.read_text())
    entry = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == "alpha-wiki")
    assert entry["source"]["path"] == "./alpha-wiki"
