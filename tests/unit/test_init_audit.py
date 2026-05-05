from pathlib import Path

from tools.init_audit import discover_sources, init_audit_report, write_source_manifest


def test_init_audit_discovers_sources_and_excludes_wiki_raw(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ADR-001-choice.md").write_text("# ADR\n")
    (tmp_path / "skills" / "query").mkdir(parents=True)
    (tmp_path / "skills" / "query" / "SKILL.md").write_text("# Skill\n")
    (tmp_path / ".wiki" / "specs").mkdir(parents=True)
    (tmp_path / ".wiki" / "specs" / "generated.md").write_text("# Generated\n")
    (tmp_path / "wiki" / "specs").mkdir(parents=True)
    (tmp_path / "wiki" / "specs" / "generated.md").write_text("# Generated\n")
    (tmp_path / ".alpha-wiki").mkdir()
    (tmp_path / ".alpha-wiki" / "config.yaml").write_text("wiki_dir: .wiki\n")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "graph.json").write_text("{}\n")
    (tmp_path / "raw" / "docs").mkdir(parents=True)
    (tmp_path / "raw" / "docs" / "old.md").write_text("# Raw\n")
    (tmp_path / "tests" / "fixtures").mkdir(parents=True)
    (tmp_path / "tests" / "fixtures" / "CLAUDE.md").write_text("# Fixture\n")

    sources = discover_sources(tmp_path)
    paths = {str(item.path) for item in sources}

    assert "docs/ADR-001-choice.md" in paths
    assert "skills/query/SKILL.md" in paths
    assert ".wiki/specs/generated.md" not in paths
    assert "wiki/specs/generated.md" not in paths
    assert ".alpha-wiki/config.yaml" not in paths
    assert ".obsidian/graph.json" not in paths
    assert "raw/docs/old.md" not in paths
    fixture = next(item for item in sources if str(item.path) == "tests/fixtures/CLAUDE.md")
    assert fixture.reason == "markdown source"


def test_init_audit_report_proposes_raw_and_wiki_processing_plan(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands" / "status.md").write_text("# Status\n")

    report = init_audit_report(tmp_path)

    assert "Alpha-Wiki Init Audit" in report
    assert "Proposed Raw Placement" in report
    assert "Processing Plan" in report
    assert "Recommended wiki dir: `wiki`" in report
    assert "`README.md` -> `raw/docs/README.md`" in report
    assert "Batch 2 - command and skill manuals" in report


def test_write_source_manifest_records_candidates(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "quickstart.md").write_text("# Quickstart\n")

    out = write_source_manifest(tmp_path)

    assert out == tmp_path / "raw" / "docs" / "source-manifest.md"
    text = out.read_text()
    assert "docs/quickstart.md" in text
    assert "wiki_slot=`specs`" in text
