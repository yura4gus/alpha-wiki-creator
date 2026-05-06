from pathlib import Path
import json

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
    assert "[[prd-auth]]" in (wiki / "index.md").read_text()
    assert "deterministic pipeline" in (wiki / "log.md").read_text()
    edges = {(edge.source, edge.target, edge.relation) for edge in read_edges(wiki / "graph" / "edges.jsonl")}
    assert ("prd-auth", "auth-service", "belongs_to") in edges


def test_ingest_pipeline_cli_reports_written_page(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "services").mkdir(parents=True)
    (wiki / "specs").mkdir(parents=True)
    (wiki / "graph").mkdir()
    (wiki / "services" / "demo-service.md").write_text(
        "---\ntitle: Demo Service\nslug: demo-service\nstatus: stable\ndate_updated: 2026-05-04\n---\n# Demo Service\n"
    )
    (wiki / "index.md").write_text("# Index\n\n- [[demo-service]]\n")
    source = tmp_path / "raw-note.md"
    source.write_text("# Raw Note\nDurable note.\n")

    result = CliRunner().invoke(cli, ["--wiki-dir", str(wiki), "--belongs-to", "demo-service", str(source)])

    assert result.exit_code == 0, result.output
    assert "# Wiki Ingest" in result.output
    assert "[[raw-note]]" in result.output
    assert "lint: 0 error(s), 0 warning(s)" in result.output
    assert (wiki / "specs" / "raw-note.md").exists()
    assert "[[raw-note]]" in (wiki / "index.md").read_text()


def test_ingest_pipeline_routes_adr_to_decisions(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "decisions").mkdir(parents=True)
    (wiki / "graph").mkdir()
    source = tmp_path / "adr-auth.md"
    source.write_text("---\nkind: adr\n---\n# Auth ADR\nRisk: token replay.\n")

    result = ingest_files(wiki, [source])[0]

    text = result.page.read_text()
    assert result.page == wiki / "decisions" / "adr-auth.md"
    assert "date:" in text
    assert "Risk: token replay." in text


def test_ingest_pipeline_routes_openapi_to_contracts_with_service_link(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "contracts" / "rest").mkdir(parents=True)
    (wiki / "services").mkdir()
    (wiki / "graph").mkdir()
    (wiki / "services" / "auth-service.md").write_text(
        "---\ntitle: Auth Service\nslug: auth-service\nstatus: stable\ndate_updated: 2026-05-04\n---\n# Auth Service\n"
    )
    source = tmp_path / "auth-openapi.yaml"
    source.write_text("openapi: 3.0.0\ninfo:\n  title: Auth API\n  version: v1\n")

    result = ingest_files(wiki, [source], belongs_to="auth-service")[0]

    text = result.page.read_text()
    assert result.page == wiki / "contracts" / "rest" / "auth-openapi.md"
    assert "transport: rest" in text
    assert "service: [[auth-service]]" in text
    assert "version: v0" in text


def test_ingest_pipeline_routes_transcript_to_sources(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "sources").mkdir(parents=True)
    (wiki / "graph").mkdir()
    source = tmp_path / "standup.md"
    source.write_text("---\nkind: transcript\n---\n# Standup\nWho owns auth?\n")

    result = ingest_files(wiki, [source])[0]

    assert result.page == wiki / "sources" / "standup.md"
    assert "Who owns auth?" in result.page.read_text()


def test_ingest_pipeline_truncates_oversized_source_excerpt(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "specs").mkdir(parents=True)
    (wiki / "graph").mkdir()
    source = tmp_path / "large-prd.md"
    source.write_text("---\nkind: prd\n---\n# Large PRD\n" + "\n".join(f"Line {i}" for i in range(120)))

    result = ingest_files(wiki, [source])[0]

    text = result.page.read_text()
    assert "Source excerpt truncated" in text
    assert "Line 119" not in text


def test_ingest_pipeline_refuses_binary_source_before_writing(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "specs").mkdir(parents=True)
    (wiki / "graph").mkdir()
    source = tmp_path / "image.bin"
    source.write_bytes(b"alpha\x00wiki")

    try:
        ingest_files(wiki, [source])
    except ValueError as exc:
        assert "likely binary" in str(exc)
    else:
        raise AssertionError("binary source should be refused")

    assert not list((wiki / "specs").glob("*.md"))


def test_ingest_pipeline_resume_skips_completed_sources(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "specs").mkdir(parents=True)
    (wiki / "graph").mkdir()
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("# First\n")
    second.write_text("# Second\n")

    ingest_files(wiki, [first], resume=True)
    ingest_files(wiki, [first, second], resume=True)

    state = json.loads((wiki / "graph" / "ingest_state.json").read_text())
    assert str(first.resolve()) in state["completed"]
    assert str(second.resolve()) in state["completed"]
    assert (wiki / "specs" / "first.md").exists()
    assert not (wiki / "specs" / "first-2.md").exists()
    assert (wiki / "specs" / "second.md").exists()
