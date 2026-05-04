from datetime import date
from pathlib import Path

from click.testing import CliRunner

from tools.review import cli as review_cli
from tools.review import review_report
from tools.rollup import cli as rollup_cli
from tools.rollup import rollup_report, write_rollup


def test_review_report_includes_status_and_lint_summary(sample_wiki: Path):
    report = review_report(sample_wiki / "wiki")

    assert "# Wiki Review" in report
    assert "## Health Snapshot" in report
    assert "## Trust Checks" in report
    assert "## Structural Findings" in report
    assert "Errors:" in report
    assert "Warnings:" in report


def test_review_cli_writes_report(sample_wiki: Path, tmp_path: Path):
    out = tmp_path / "review.md"

    result = CliRunner().invoke(review_cli, [
        "--wiki-dir", str(sample_wiki / "wiki"),
        "--out", str(out),
    ])

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "# Wiki Review" in out.read_text()


def test_rollup_report_includes_matching_log_entries(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "modules").mkdir(parents=True)
    (wiki / "log.md").write_text(
        "# Log\n\n"
        "## [2026-04-03] ingest | added module\n"
        "## [2026-03-30] ingest | old module\n"
    )
    (wiki / "modules" / "m1.md").write_text(
        "---\ntitle: M1\nslug: m1\nstatus: stable\ndate_updated: 2026-04-04\n---\n# M1\n"
    )

    label, report = rollup_report(wiki, period="month", today=date(2026, 4, 30))

    assert label == "2026-04"
    assert "2026-04-03 ingest | added module" in report
    assert "old module" not in report
    assert "[[m1]]" in report


def test_rollup_write_is_idempotent(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "log.md").write_text("# Log\n\n## [2026-04-03] query | answered\n")

    first = write_rollup(wiki, period="month", today=date(2026, 4, 30))
    first_text = first.read_text()
    second = write_rollup(wiki, period="month", today=date(2026, 4, 30))

    assert first == second
    assert second.read_text() == first_text
    assert first.name == "2026-04.md"


def test_rollup_cli_writes_file(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "log.md").write_text("# Log\n\n## [2026-04-03] query | answered\n")

    result = CliRunner().invoke(rollup_cli, [
        "--wiki-dir", str(wiki),
        "--period", "month",
        "--write",
    ])

    assert result.exit_code == 0, result.output
    assert "wrote" in result.output
    assert list((wiki / "rollups").glob("*.md"))
