from pathlib import Path

import pytest

from tools.lint import (
    check_broken_wikilinks, check_cluster_links, check_dependency_rules,
    check_duplicate_slugs, check_orphans, check_required_frontmatter,
)
from tools.status import status_report
from tools.review import review_report
from tools.wiki_engine import cluster_gaps, collect_edges, scan_wiki


def write_page(wiki, relative, metadata, body=""):
    path = wiki / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{metadata}\n---\n{body}")
    return path


def test_navigation_has_identity_not_contract_schema_or_cluster_gaps(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md", "title: Contracts\nslug: contracts-index")
    assert check_required_frontmatter(
        wiki, {"contract": ["title", "slug", "transport", "service"]},
        {"contracts": "contract"},
    ) == []
    assert check_cluster_links(wiki) == []
    assert cluster_gaps(wiki, scan_wiki(wiki)[0]) == []
    report = status_report(wiki, refresh=False)
    assert "- Cluster link gaps: 0" in report
    assert "Coverage gap: no decision/spec/contract/feature/claim evidence pages" in report


@pytest.mark.parametrize("metadata,missing", [
    ("title: Contracts", "slug"),
    ("slug: contracts-index", "title"),
    ("title: ''\nslug: contracts-index", "title"),
    ("title: Contracts\nslug: 7", "slug"),
])
def test_navigation_requires_explicit_nonempty_identity(tmp_path, metadata, missing):
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md", metadata)
    findings = check_required_frontmatter(wiki, {}, {})
    assert any(f"`{missing}`" in item.message for item in findings)


def test_navigation_does_not_exempt_neighbor_entities(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md", "title: Contracts\nslug: contracts-index")
    entity = write_page(wiki, "contracts/rest/orders.md", "title: Orders\nslug: orders")
    findings = check_required_frontmatter(wiki, {"contract": ["service", "transport"]}, {"contracts": "contract"})
    assert len(findings) == 2
    assert all(item.file == str(entity) for item in findings)
    assert len(check_cluster_links(wiki)) == 2
    assert "- Cluster link gaps: 2" in status_report(wiki, refresh=False)


def test_navigation_stays_in_link_orphan_and_duplicate_checks(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md", "title: Contracts\nslug: contracts-index", "[[orders]]\n[[missing]]")
    write_page(wiki, "specs/orders.md", "title: Orders\nslug: orders", "[[contracts-index]]")
    assert {page.slug for page in scan_wiki(wiki)} == {"contracts-index", "orders"}
    assert len(check_broken_wikilinks(wiki)) == 1
    assert "missing" in check_broken_wikilinks(wiki)[0].message
    assert check_orphans(wiki) == []
    write_page(wiki, "specs/_index.md", "title: Specs\nslug: contracts-index")
    assert len(check_duplicate_slugs(wiki)) == 1


def test_navigation_stays_in_dependency_checks(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "core/_index.md", "title: Core\nslug: core-index", "[[postgres]]")
    write_page(wiki, "infrastructure/postgres.md", "title: Postgres\nslug: postgres")
    findings = check_dependency_rules(wiki, [{"from": "core/", "forbidden_to": ["infrastructure/"]}])
    assert len(findings) == 1
    assert "core-index" in findings[0].message


def test_navigation_alone_does_not_prove_a_mixed_service_cluster(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "services/_index.md", "title: Services\nslug: services-index")
    write_page(wiki, "services/auth.md", "title: Auth\nslug: auth")
    write_page(wiki, "contracts/_index.md", "title: Contracts\nslug: contracts-index\nbelongs_to: '[[auth]]'")
    report = status_report(wiki, refresh=False)
    assert "- Service clusters: 0" in report
    assert "- Mixed-role clusters: 0" in report
    assert "- Isolated service nodes: 1" in report
    review = review_report(wiki, refresh=False)
    assert "- Isolated services: 1" in review
    assert "- Cluster gaps: 0" in review


def test_vault_relative_navigation_paths_remain_distinct(tmp_path):
    from tools.lint import check_missing_reverse_links
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md",
               "title: Contracts\nslug: contracts-index\ndepends_on: ['[[specs/_index]]']",
               "[[specs/_index|Specs]]")
    write_page(wiki, "specs/_index.md",
               "title: Specs\nslug: specs-index\ndependents: ['[[contracts/_index.md]]']",
               "[[contracts/_index.md|Contracts]]")
    assert check_broken_wikilinks(wiki) == []
    assert check_orphans(wiki) == []
    assert check_missing_reverse_links(wiki) == []
    edges = {(edge.source, edge.target, edge.relation) for edge in collect_edges(wiki)}
    assert ("contracts-index", "specs-index", "depends_on") in edges
    assert ("specs-index", "contracts-index", "dependents") in edges
    findings = check_dependency_rules(wiki, [{"from": "contracts/", "forbidden_to": ["specs/"]}])
    assert len(findings) == 1
    assert "specs-index" in findings[0].message


def test_root_index_can_link_navigation_by_native_obsidian_path(tmp_path):
    wiki = tmp_path / "wiki"
    write_page(wiki, "contracts/_index.md", "title: Contracts\nslug: contracts-index")
    (wiki / "index.md").write_text("[[contracts/_index|Contract Catalog]]\n")
    assert check_orphans(wiki) == []
