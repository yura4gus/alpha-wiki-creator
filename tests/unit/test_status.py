from pathlib import Path
from datetime import date, timedelta
from tools.status import status_report

def test_status_report_includes_stats(sample_wiki: Path):
    r = status_report(sample_wiki / "wiki")
    assert "Pages:" in r
    assert "Edges:" in r
    assert "Open questions:" in r

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
