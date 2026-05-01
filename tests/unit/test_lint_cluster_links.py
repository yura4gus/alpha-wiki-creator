from pathlib import Path

from tools.lint import check_cluster_links
from tools._models import LintSeverity


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_unclustered_document_is_flagged(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "decisions" / "auth-adr.md",
        "title: Auth ADR\nslug: auth-adr\nstatus: accepted",
    )

    findings = check_cluster_links(wiki)

    assert any(f.check == "cluster-link-gap" for f in findings)
    assert any("auth-adr" in f.message and "document has no cluster" in f.message for f in findings)


def test_clustered_document_is_not_flagged(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "decisions" / "auth-adr.md",
        "title: Auth ADR\nslug: auth-adr\nstatus: accepted\naffects: ['[[auth-module]]']",
    )
    _write_page(
        wiki / "modules" / "auth-module.md",
        "title: Auth Module\nslug: auth-module\nstatus: stable",
    )

    findings = check_cluster_links(wiki)

    assert not [f for f in findings if "auth-adr" in f.message]


def test_feature_without_implementation_is_flagged(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "features" / "login.md",
        "title: Login\nslug: login\nstatus: discovery\nbelongs_to: ''\nimplements: []",
    )

    findings = check_cluster_links(wiki)

    assert any(f.severity == LintSeverity.WARNING for f in findings)
    assert any("feature/flow has no implementation" in f.message for f in findings)


def test_contract_without_owner_or_consumers_is_flagged(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "contracts" / "rest" / "auth.md",
        "title: Auth API\nslug: auth-api\ntransport: rest\nstatus: draft",
    )

    findings = check_cluster_links(wiki)
    messages = [f.message for f in findings]

    assert any("contract has no service owner" in msg for msg in messages)
    assert any("contract has no consumers" in msg for msg in messages)
