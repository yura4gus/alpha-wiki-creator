from pathlib import Path
from datetime import date, timedelta
from tools.wiki_engine import read_edges
from tools.status import status_report

def test_status_report_includes_stats(sample_wiki: Path):
    r = status_report(sample_wiki / "wiki")
    assert "Pages:" in r
    assert "Edges:" in r
    assert "Open questions:" in r
    assert "Gap Check" in r

def test_status_report_lists_recent_log_entries(sample_wiki: Path):
    r = status_report(sample_wiki / "wiki")
    assert "Recent activity" in r
    assert "bootstrap" in r  # log.md has bootstrap entry

def test_status_report_flags_stale_pages(tmp_path: Path):
    """Pages with date_updated > 30 days old are flagged stale."""
    wiki = tmp_path / "wiki"
    (wiki / "modules").mkdir(parents=True)
    (wiki / "log.md").write_text("# Log\n")
    old = (date.today() - timedelta(days=60)).isoformat()
    (wiki / "modules" / "old.md").write_text(
        f"---\ntitle: Old\nslug: old\nstatus: stable\ndate_updated: {old}\n---\n# Old\n")
    r = status_report(wiki)
    assert "old" in r
    assert "Stale" in r or "stale" in r

def test_status_report_includes_schema_evolution(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "log.md").write_text(
        "# Log\n\n## [2026-04-28] schema-change | added type: migration (data/migrations/) | trigger: ingest\n")
    r = status_report(wiki)
    assert "Schema evolution" in r or "schema-change" in r
    assert "migration" in r


def test_status_report_rebuilds_graph_before_gap_check(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "modules").mkdir(parents=True)
    (wiki / "graph").mkdir()
    (wiki / "log.md").write_text("# Log\n\n## [2026-04-30] ingest | added modules\n")
    today = date.today().isoformat()
    (wiki / "modules" / "m1.md").write_text(
        f"---\ntitle: M1\nslug: m1\nstatus: stable\ndate_updated: {today}\ndepends_on: ['[[m2]]']\n---\n# M1\n"
    )
    (wiki / "modules" / "m2.md").write_text(
        f"---\ntitle: M2\nslug: m2\nstatus: stable\ndate_updated: {today}\n---\n# M2\n"
    )
    (wiki / "graph" / "edges.jsonl").write_text("")

    r = status_report(wiki)
    edges = read_edges(wiki / "graph" / "edges.jsonl")

    assert "Edges: 1" in r
    assert [(edge.source, edge.target, edge.relation) for edge in edges] == [("m1", "m2", "depends_on")]
    assert "Graph gap" not in r


def test_status_report_surfaces_cluster_gaps(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "decisions").mkdir(parents=True)
    (wiki / "log.md").write_text("# Log\n\n## [2026-05-01] ingest | added decision\n")
    today = date.today().isoformat()
    (wiki / "decisions" / "d1.md").write_text(
        f"---\ntitle: D1\nslug: d1\nstatus: accepted\ndate_updated: {today}\n---\n# D1\n"
    )

    r = status_report(wiki)

    assert "Cluster gap:" in r
    assert "typed ownership links" in r
