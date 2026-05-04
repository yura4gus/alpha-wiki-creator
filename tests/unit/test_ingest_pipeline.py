from pathlib import Path

from click.testing import CliRunner

from tools.ingest_pipeline import cli, ingest_files
from tools.wiki_engine import read_edges


def test_ingest_pipeline_writes_page_with_provenance_log_and_graph(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "services").mkdir(parents=True)
    (wiki / "specs").mkdir()
    (wiki / "graph").mkdir()
    (wiki / "log.md").write_text("# Log\n")
    (wiki / "services" / "auth-service.md").write_text(
        "---\ntitle: Auth Service\nslug: auth-service\nstatus: stable\ndate_updated: 2026-05-04\n---\n# Auth Service\n"
    )
    source = tmp_path / "raw" / "prd-auth.md"
    source.parent.mkdir()
    source.write_text("---\nkind: prd\n---\n# Auth PRD\nShould login use JWT?\n")

    results = ingest_files(wiki, [source], belongs_to="auth-service")

    page = results[0].page
    text = page.read_text()
    assert page == wiki / "specs" / "prd-auth.md"
    assert "source_file:" in text
    assert "belongs_to: [[auth-service]]" in text
    assert "Should login use JWT?" in text
    assert "deterministic pipeline" in (wiki / "log.md").read_text()
    edges = {(edge.source, edge.target, edge.relation) for edge in read_edges(wiki / "graph" / "edges.jsonl")}
    assert ("prd-auth", "auth-service", "belongs_to") in edges


def test_ingest_pipeline_cli_reports_written_page(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "specs").mkdir(parents=True)
    (wiki / "graph").mkdir()
    source = tmp_path / "raw-note.md"
    source.write_text("# Raw Note\nDurable note.\n")

    result = CliRunner().invoke(cli, ["--wiki-dir", str(wiki), str(source)])

    assert result.exit_code == 0, result.output
    assert "# Wiki Ingest" in result.output
    assert "[[raw-note]]" in result.output
    assert (wiki / "specs" / "raw-note.md").exists()
