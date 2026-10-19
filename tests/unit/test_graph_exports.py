from pathlib import Path

from click.testing import CliRunner

from tools.render_dot import cli as dot_cli
from tools.render_dot import render_dot
from tools.render_html import cli as html_cli
from tools.render_html import render_html
from tools.render_mermaid import cli as mermaid_cli
from tools.render_mermaid import render_mermaid
from tools.wiki_engine import rebuild_edges


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def _mixed_cluster_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "services" / "auth-service.md",
        "title: Auth Service\nslug: auth-service\nstatus: stable\ndate_updated: 2026-05-04",
        "# Auth Service\n",
    )
    _write_page(
        wiki / "modules" / "jwt-module.md",
        "title: JWT Module\nslug: jwt-module\nstatus: stable\ndate_updated: 2026-05-04\nbelongs_to: '[[auth-service]]'",
        "# JWT Module\n",
    )
    _write_page(
        wiki / "features" / "login-flow.md",
        "title: Login Flow\nslug: login-flow\nstatus: building\ndate_updated: 2026-05-04\nbelongs_to: '[[auth-service]]'\nimplements: ['[[jwt-module]]']",
        "# Login Flow\n",
    )
    _write_page(
        wiki / "decisions" / "auth-adr.md",
        "title: Auth ADR\nslug: auth-adr\nstatus: accepted\ndate_updated: 2026-05-04\nbelongs_to: '[[auth-service]]'\naffects: ['[[jwt-module]]']",
        "# Auth ADR\nSee [[auth-service]], [[jwt-module|JWT]], and [[missing-page]].\n",
    )
    _write_page(
        wiki / "contracts" / "rest" / "auth-api.md",
        "title: Auth API\nslug: auth-api\nstatus: stable\ndate_updated: 2026-05-04\nservice: '[[auth-service]]'\nconsumers: ['[[jwt-module]]']",
        "# Auth API\n",
    )
    rebuild_edges(wiki)
    return wiki


def test_mermaid_export_groups_mixed_role_nodes_by_typed_service_links(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)

    out = render_mermaid(wiki)

    assert 'subgraph cluster_auth_service["Auth Service cluster"]' in out
    assert 'auth_service["Auth Service"]' in out
    assert 'jwt_module["JWT Module"]' in out
    assert 'login_flow["Login Flow"]' in out
    assert 'auth_adr["Auth ADR"]' in out
    assert 'auth_api["Auth API"]' in out
    assert "class auth_service service;" in out
    assert "class jwt_module module;" in out
    assert "class login_flow feature;" in out
    assert "class auth_adr document;" in out
    assert "class auth_api contract;" in out
    assert 'jwt_module -->|"belongs_to"| auth_service' in out


def test_dot_export_groups_mixed_role_nodes_by_typed_service_links(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)

    out = render_dot(wiki)

    assert "subgraph cluster_auth_service" in out
    assert 'label="Auth Service cluster";' in out
    assert '"auth-service" [label="Auth Service", fillcolor="#E94B43"' in out
    assert '"jwt-module" [label="JWT Module", fillcolor="#16A34A"' in out
    assert '"login-flow" [label="Login Flow", fillcolor="#2563EB"' in out
    assert '"auth-adr" [label="Auth ADR", fillcolor="#111111"' in out
    assert '"auth-api" [label="Auth API", fillcolor="#F97316"' in out
    assert '"jwt-module" -> "auth-service" [label="belongs_to"];' in out


def test_graph_export_clis_write_default_graph_files(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)

    mermaid = CliRunner().invoke(mermaid_cli, ["--wiki-dir", str(wiki)])
    dot = CliRunner().invoke(dot_cli, ["--wiki-dir", str(wiki)])

    assert mermaid.exit_code == 0, mermaid.output
    assert dot.exit_code == 0, dot.output
    assert (wiki / "graph" / "graph.mmd").exists()
    assert (wiki / "graph" / "graph.dot").exists()


def test_html_export_writes_static_read_only_site(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)

    out = render_html(wiki)

    assert (out / "index.html").exists()
    assert (out / "style.css").exists()
    assert (out / "services" / "auth-service.html").exists()
    assert (out / "graph" / "graph.mmd").exists()
    assert (out / "graph" / "graph.dot").exists()
    index = (out / "index.html").read_text()
    service = (out / "services" / "auth-service.html").read_text()
    decision = (out / "decisions" / "auth-adr.html").read_text()
    assert "Alpha-Wiki Export" in index
    assert 'href="services/auth-service.html"' in index
    assert 'href="wiki/services/auth-service.html"' not in index
    assert 'href="../services/auth-service.html"' in decision
    assert 'href="../modules/jwt-module.html"' in decision
    assert '<span class="missing-link">[[missing-page]]</span>' in decision
    assert "Auth Service" in service
    assert "Static read-only export" in index


def test_html_export_cli_writes_custom_output_dir(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)
    out = tmp_path / "site"

    result = CliRunner().invoke(html_cli, ["--wiki-dir", str(wiki), "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert (out / "index.html").exists()


def test_html_export_preserves_unrelated_custom_output_files(tmp_path: Path):
    wiki = _mixed_cluster_wiki(tmp_path)
    out = tmp_path / "site"
    out.mkdir()
    keep = out / "operator-note.txt"
    keep.write_text("keep me\n")

    render_html(wiki, out_dir=out)

    assert keep.read_text() == "keep me\n"


def test_navigation_is_retained_and_graph_rebuilds_are_deterministic(tmp_path):
    from tools.wiki_engine import rebuild_context_brief, rebuild_open_questions, scan_wiki
    wiki = _mixed_cluster_wiki(tmp_path)
    _write_page(wiki / "contracts/_index.md",
                "title: API Catalog\nslug: api-catalog\nbelongs_to: '[[auth-service]]'",
                "See [[auth-api]].\n")
    _write_page(wiki / "specs/_index.md",
                "title: Specs Catalog\nslug: specs-catalog\nbelongs_to: '[[contracts/_index]]'",
                "See [[contracts/_index|API Catalog]].\n")
    assert "api-catalog" in {page.slug for page in scan_wiki(wiki)}

    def snapshot():
        rebuild_edges(wiki)
        rebuild_context_brief(wiki)
        rebuild_open_questions(wiki)
        return (
            (wiki / "graph/edges.jsonl").read_bytes(),
            (wiki / "graph/context_brief.md").read_bytes(),
            (wiki / "graph/open_questions.md").read_bytes(),
            render_mermaid(wiki), render_dot(wiki),
        )

    before = snapshot()
    assert snapshot() == before
    assert 'api_catalog["API Catalog"]' in before[3]
    assert "class auth_service service;" in before[3]
    assert "class jwt_module module;" in before[3]
    assert "class login_flow feature;" in before[3]
    assert "class auth_adr document;" in before[3]
    assert "class auth_api contract;" in before[3]
    assert "subgraph cluster_auth_service" in before[3]
    assert 'specs_catalog -->|"belongs_to"| api_catalog' in before[3]
    assert '"specs-catalog" -> "api-catalog"' in before[4]
    out = render_html(wiki)
    assert 'href="contracts/_index.html"' in (out / "index.html").read_text()
    assert 'href="../contracts/rest/auth-api.html"' in (out / "contracts/_index.html").read_text()
    assert (out / "contracts/../contracts/rest/auth-api.html").resolve().is_file()
    assert 'href="../contracts/_index.html"' in (out / "specs/_index.html").read_text()


def test_module_root_groups_real_documentation_without_inventing_a_service(tmp_path):
    wiki = tmp_path / "wiki"
    _write_page(wiki / "modules/runtime.md", "title: Runtime\nslug: runtime")
    _write_page(wiki / "security/auth.md",
                "title: Auth Rules\nslug: auth-rules\nbelongs_to: '[[runtime]]'")
    mermaid = render_mermaid(wiki)
    dot = render_dot(wiki)
    assert 'subgraph cluster_runtime["Runtime cluster"]' in mermaid
    assert "class runtime module;" in mermaid
    assert "class auth_rules document;" in mermaid
    assert '"auth-rules" [label="Auth Rules", fillcolor="#111111"' in dot
    assert "class runtime service;" not in mermaid


def test_transitive_ownership_uses_one_group_in_both_exports(tmp_path):
    from tools.render_mermaid import _ownership_clusters
    from tools.wiki_engine import collect_edges, scan_wiki
    wiki = tmp_path / "wiki"
    _write_page(wiki / "services/api.md", "title: API\nslug: api")
    _write_page(wiki / "modules/core.md",
                "title: Core\nslug: core\nbelongs_to: '[[api]]'")
    _write_page(wiki / "specs/behavior.md",
                "title: Behavior\nslug: behavior\nbelongs_to: '[[core]]'")
    assert _ownership_clusters(wiki, scan_wiki(wiki), collect_edges(wiki)) == {
        "api": {"api", "core", "behavior"},
    }
    for output in (render_mermaid(wiki), render_dot(wiki)):
        assert "subgraph cluster_api" in output
        assert "subgraph cluster_core" not in output
        assert output.count('["Behavior"]') + output.count('[label="Behavior"') == 1


def test_ambiguous_owner_is_not_duplicated_or_assigned_arbitrarily(tmp_path):
    from tools.render_mermaid import _ownership_clusters
    from tools.wiki_engine import collect_edges, scan_wiki
    wiki = tmp_path / "wiki"
    for slug in ("a", "b"):
        _write_page(wiki / f"services/{slug}.md", f"title: {slug}\nslug: {slug}")
    _write_page(wiki / "specs/bridge.md",
                "title: Bridge\nslug: bridge\nowned_by: ['[[a]]', '[[b]]']")
    assert _ownership_clusters(wiki, scan_wiki(wiki), collect_edges(wiki)) == {}
    assert render_dot(wiki).count('"bridge" [label="Bridge"') == 1


def test_cyclic_ownership_terminates_without_fabricating_a_root(tmp_path):
    from tools.render_mermaid import _ownership_clusters
    from tools.wiki_engine import collect_edges, scan_wiki
    wiki = tmp_path / "wiki"
    _write_page(wiki / "modules/a.md", "title: A\nslug: a\nbelongs_to: '[[b]]'")
    _write_page(wiki / "modules/b.md", "title: B\nslug: b\nbelongs_to: '[[a]]'")
    assert _ownership_clusters(wiki, scan_wiki(wiki), collect_edges(wiki)) == {}
    assert 'a -->|"belongs_to"| b' in render_mermaid(wiki)
