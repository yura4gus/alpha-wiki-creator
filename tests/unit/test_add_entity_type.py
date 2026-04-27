"""Test schema evolution: add_entity_type."""
from pathlib import Path
from scripts.add_entity_type import add_entity_type


def test_add_entity_type_updates_claude_md_and_creates_dir(sample_wiki: Path):
    new_spec = {
        "name": "migration",
        "dir": "data/migrations",
        "frontmatter_required": ["title", "slug", "applied_at"],
        "frontmatter_optional": ["target_table", "rollback"],
        "sections_required": ["Up", "Down"],
    }
    add_entity_type(sample_wiki, new_spec, trigger="ingest of raw/migrations/2026.sql")
    claude = (sample_wiki / "CLAUDE.md").read_text()
    assert "migration" in claude
    assert "data/migrations" in claude
    assert (sample_wiki / "wiki" / "data" / "migrations").is_dir()
    log = (sample_wiki / "wiki" / "log.md").read_text()
    assert "schema-change" in log
    assert "migration" in log
