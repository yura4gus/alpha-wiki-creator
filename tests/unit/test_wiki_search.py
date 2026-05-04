from pathlib import Path

from click.testing import CliRunner

from tools.wiki_search import cli, query_report, search_wiki


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_search_wiki_ranks_slug_title_and_body_matches(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "decisions" / "auth-adr.md",
        "title: Auth Decision\nslug: auth-adr\nstatus: accepted\ndate_updated: 2026-05-04",
        "# Auth Decision\nJWT auth is accepted for login.\n",
    )
    _write_page(
        wiki / "modules" / "billing.md",
        "title: Billing\nslug: billing\nstatus: stable\ndate_updated: 2026-05-04",
        "# Billing\nNo auth details here.\n",
    )

    hits = search_wiki(wiki, "auth login")

    assert hits[0].slug == "auth-adr"
    assert hits[0].status == "accepted"
    assert any("decisions/auth-adr.md" in citation for citation in hits[0].citations)


def test_query_report_handles_no_answer(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "modules").mkdir(parents=True)

    report = query_report(wiki, "payments")

    assert "No relevant wiki pages were found" in report
    assert "Ingest or link durable source material" in report


def test_query_report_surfaces_truth_status_and_related_pages(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "features" / "login-flow.md",
        "title: Login Flow\nslug: login-flow\nstatus: building\ndate_updated: 2026-05-04",
        "# Login Flow\nLogin depends on JWT auth.\n",
    )

    report = query_report(wiki, "login")

    assert "## Truth Status" in report
    assert "assumption:" in report
    assert "[[login-flow]]" in report


def test_wiki_search_cli_outputs_query_report(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "modules" / "auth.md",
        "title: Auth\nslug: auth\nstatus: stable\ndate_updated: 2026-05-04",
        "# Auth\nAuth owns login.\n",
    )

    result = CliRunner().invoke(cli, ["--wiki-dir", str(wiki), "--query", "login"])

    assert result.exit_code == 0, result.output
    assert "# Wiki Query" in result.output
    assert "[[auth]]" in result.output
