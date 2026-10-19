"""Test config-backed schema evolution."""
from pathlib import Path

import yaml
import pytest

from scripts.add_entity_type import add_entity_type


def test_add_entity_type_updates_config_and_creates_dir(sample_wiki: Path):
    new_spec = {
        "name": "migration",
        "dir": "data/migrations",
        "frontmatter_required": ["title", "slug", "applied_at"],
        "frontmatter_optional": ["target_table", "rollback"],
        "sections_required": ["Up", "Down"],
    }
    add_entity_type(sample_wiki, new_spec, trigger="ingest of raw/migrations/2026.sql")
    config = yaml.safe_load((sample_wiki / ".alpha-wiki" / "config.yaml").read_text())
    assert config["entity_types"][-1]["name"] == "migration"
    assert config["entity_types"][-1]["dir"] == "data/migrations"
    assert (sample_wiki / "wiki" / "data" / "migrations").is_dir()
    log = (sample_wiki / "wiki" / "log.md").read_text()
    assert "schema-change" in log
    assert "migration" in log


def test_add_entity_type_respects_dot_wiki_dir(tmp_path: Path):
    """When wiki_dir=.wiki, dir + log are under .wiki/, not wiki/."""
    (tmp_path / ".alpha-wiki").mkdir()
    (tmp_path / ".alpha-wiki" / "config.yaml").write_text("entity_types: []\n")
    (tmp_path / ".wiki").mkdir()
    (tmp_path / ".wiki" / "log.md").write_text("# Log\n")
    spec = {"name": "migration", "dir": "migrations",
            "frontmatter_required": ["title", "slug"],
            "frontmatter_optional": [], "sections_required": []}
    from scripts.add_entity_type import add_entity_type
    add_entity_type(tmp_path, spec, trigger="test", wiki_dir=".wiki")
    assert (tmp_path / ".wiki" / "migrations").is_dir()
    assert "schema-change" in (tmp_path / ".wiki" / "log.md").read_text()
    assert not (tmp_path / "wiki").exists()


def test_add_entity_type_rejects_duplicate_name(sample_wiki: Path):
    spec = {
        "name": "module",
        "dir": "another-modules",
        "frontmatter_required": ["title", "slug"],
    }

    try:
        add_entity_type(sample_wiki, spec)
    except ValueError as exc:
        assert "entity type already exists" in str(exc)
    else:
        raise AssertionError("duplicate entity type was accepted")


def contents(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("directory", ["../escape", "/tmp/escape", "nested/../escape", ".", "graph/pages", "render/pages", "agentops/pages", "dir\nnew-entry", "a\\b"])
def test_invalid_directory_never_changes_config_or_log(sample_wiki, directory):
    before = contents(sample_wiki)
    with pytest.raises(ValueError):
        add_entity_type(sample_wiki, {"name": "example", "dir": directory})
    assert contents(sample_wiki) == before
    assert not (sample_wiki.parent / "escape").exists()


def test_schema_failure_rolls_back_config_log_and_new_directories(sample_wiki, monkeypatch):
    import scripts.add_entity_type as module
    before = contents(sample_wiki)
    atomic = module._atomic_text

    def fail_log(path, text):
        if path.name == "log.md":
            raise OSError("injected log write failure")
        atomic(path, text)

    monkeypatch.setattr(module, "_atomic_text", fail_log)
    with pytest.raises(OSError, match="injected"):
        add_entity_type(sample_wiki, {"name": "example", "dir": "new/nested"})
    assert contents(sample_wiki) == before
    assert not (sample_wiki / "wiki/new").exists()


def test_schema_rejects_symlink_directory_without_touching_target(sample_wiki, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (sample_wiki / "wiki/linked").symlink_to(outside, target_is_directory=True)
    before = contents(sample_wiki)
    with pytest.raises(ValueError):
        add_entity_type(sample_wiki, {"name": "example", "dir": "linked/new"})
    assert not list(outside.iterdir())
    assert contents(sample_wiki) == before


def test_schema_preserves_other_fields_instructions_and_repeat_state(sample_wiki):
    config_path = sample_wiki / ".alpha-wiki/config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["user_policy"] = {"limits": [1, 2], "enabled": False}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    instructions = {path: path.read_bytes() for path in (sample_wiki / "AGENTS.md", sample_wiki / "CLAUDE.md") if path.exists()}
    spec = {"name": "example", "dir": "new/pages"}
    add_entity_type(sample_wiki, spec)
    after = yaml.safe_load(config_path.read_text())
    assert after["cross_ref_rules"] == config["cross_ref_rules"]
    assert after["user_policy"] == config["user_policy"]
    assert all(path.read_bytes() == value for path, value in instructions.items())
    before = contents(sample_wiki)
    with pytest.raises(ValueError, match="already exists"):
        add_entity_type(sample_wiki, spec)
    assert contents(sample_wiki) == before
