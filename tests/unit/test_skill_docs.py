from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def _skill_files() -> list[Path]:
    return sorted((ROOT / "skills").glob("*/SKILL.md"))


def test_skill_frontmatter_is_valid_yaml():
    for path in _skill_files():
        text = path.read_text()
        assert text.startswith("---\n"), path
        _, frontmatter, _ = text.split("---", 2)
        data = yaml.safe_load(frontmatter)
        assert data["name"] == path.parent.name
        assert data["description"]


def test_skill_docs_have_operational_manual_sections():
    required = ["## Mission", "## Name Contract", "## Workflow"]
    for path in _skill_files():
        text = path.read_text()
        for heading in required:
            assert heading in text, f"{path} missing {heading}"


def test_skill_docs_preserve_wiki_discipline_language():
    corpus = "\n".join(path.read_text() for path in _skill_files())
    for term in ["Karpathy", "Obsidian", "graph", "frontmatter", "wikilinks", "CLAUDE.md"]:
        assert term in corpus


def test_commands_explain_human_meaning():
    for path in sorted((ROOT / "commands").glob("*.md")):
        text = path.read_text()
        assert "Human meaning:" in text, f"{path} should explain the command in user language"
