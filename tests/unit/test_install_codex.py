from pathlib import Path

import yaml

from scripts.install_codex import install_codex_skills, transform_skill_for_codex


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
    assert "invoke this skill as `$alpha-wiki-init`" in out
    assert "/alpha-wiki:init" in out
    _, frontmatter, _ = out.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert data["name"] == "alpha-wiki-init"
    assert data["description"].startswith("Codex adapter for Alpha-Wiki")


def test_install_codex_skills_writes_prefixed_skill_set(tmp_path: Path):
    installed = install_codex_skills(tmp_path)

    assert len(installed) == 10
    assert (tmp_path / "alpha-wiki-init" / "SKILL.md").exists()
    assert (tmp_path / "alpha-wiki-query" / "SKILL.md").exists()
    assert "name: alpha-wiki-status" in (tmp_path / "alpha-wiki-status" / "SKILL.md").read_text()
