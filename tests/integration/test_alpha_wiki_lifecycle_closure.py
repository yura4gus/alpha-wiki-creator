from pathlib import Path

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig
from tools._models import LintSeverity
from tools.lint import run_all_checks
from tools.review import review_report
from tools.rollup import rollup_report
from tools.status import status_report
from tools.wiki_engine import read_edges, rebuild_edges


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_alpha_wiki_lifecycle_is_closed_for_clustered_pages(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo",
        project_description="Lifecycle smoke",
        wiki_dir="wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="all",
        ci=True,
        schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    wiki = tmp_path / "wiki"

    _write_page(
        wiki / "modules" / "auth-service.md",
        "title: Auth Service\nslug: auth-service\nstatus: stable\ndate_updated: 2026-05-01",
        "# Auth Service\n",
    )
    _write_page(
        wiki / "modules" / "auth-module.md",
        "title: Auth Module\nslug: auth-module\nstatus: stable\ndate_updated: 2026-05-01\nbelongs_to: '[[auth-service]]'\nconsumes: ['[[auth-api]]']",
        "# Auth Module\n",
    )
    _write_page(
        wiki / "features" / "login-flow.md",
        "title: Login Flow\nslug: login-flow\nstatus: building\ndate_updated: 2026-05-01\nbelongs_to: '[[auth-service]]'\nimplements: ['[[auth-module]]']",
        "# Login Flow\n",
    )
    _write_page(
        wiki / "decisions" / "auth-adr.md",
        "title: Auth ADR\nslug: auth-adr\nstatus: accepted\ndate: 2026-05-01\ndate_updated: 2026-05-01\nbelongs_to: '[[auth-service]]'\naffects: ['[[auth-module]]']",
        "# Auth ADR\n",
    )
    _write_page(
        wiki / "contracts" / "rest" / "auth-api.md",
        "title: Auth API\nslug: auth-api\ntransport: rest\nservice: '[[auth-service]]'\nconsumers: ['[[auth-module]]']\nversion: v1\nstatus: stable\ndate_updated: 2026-05-01",
        "# Auth API\n",
    )
    (wiki / "log.md").write_text(
        "# Log\n\n"
        "## [2026-05-01] bootstrap | preset=software-project overlay=none\n"
        "## [2026-05-01] ingest | auth cluster | pages=5\n"
    )

    rebuild_edges(wiki)
    edges = {(edge.source, edge.target, edge.relation) for edge in read_edges(wiki / "graph" / "edges.jsonl")}
    assert ("auth-module", "auth-service", "belongs_to") in edges
    assert ("login-flow", "auth-module", "implements") in edges
    assert ("auth-adr", "auth-module", "affects") in edges
    assert ("auth-api", "auth-service", "service") in edges

    findings = run_all_checks(wiki, schema={}, dir_to_type={}, dependency_rules=[])
    assert not [f for f in findings if f.severity == LintSeverity.ERROR]
    assert not [f for f in findings if f.check == "cluster-link-gap"]

    status = status_report(wiki)
    assert "Cluster gap:" not in status
    assert "Edges:" in status

    review = review_report(wiki)
    assert "# Wiki Review" in review
    assert "cluster-link-gap" not in review

    label, rollup = rollup_report(wiki, period="month")
    assert label
    assert "auth cluster" in rollup
