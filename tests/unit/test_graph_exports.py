from pathlib import Path

from click.testing import CliRunner

from tools.render_dot import cli as dot_cli
from tools.render_dot import render_dot
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
        "# Auth ADR\n",
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
    assert 'jwt_module --|"belongs_to"| auth_service' in out


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
