# tests/unit/test_wiki_engine_edges.py
from pathlib import Path
from tools.wiki_engine import rebuild_edges, add_edge, read_edges


def test_rebuild_edges_writes_jsonl_from_frontmatter(sample_wiki: Path):
    rebuild_edges(sample_wiki / "wiki")
    edges = read_edges(sample_wiki / "wiki" / "graph" / "edges.jsonl")
    relations = {(e.source, e.target, e.relation) for e in edges}
    assert ("m1", "m2", "depends_on") in relations
    assert ("d1", "m1", "affects") in relations
    assert ("c1", "m1", "service") in relations


def test_rebuild_edges_includes_cluster_ownership_relations(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "decisions").mkdir(parents=True)
    (wiki / "modules").mkdir()
    (wiki / "decisions" / "d1.md").write_text(
        "---\ntitle: D1\nslug: d1\nstatus: accepted\nbelongs_to: '[[auth-service]]'\nowned_by: '[[platform-team]]'\nsource: '[[raw-auth-prd]]'\n---\n# D1\n"
    )
    (wiki / "modules" / "auth-service.md").write_text(
        "---\ntitle: Auth\nslug: auth-service\nstatus: stable\n---\n# Auth\n"
    )

    rebuild_edges(wiki)
    relations = {(edge.source, edge.target, edge.relation) for edge in read_edges(wiki / "graph" / "edges.jsonl")}

    assert ("d1", "auth-service", "belongs_to") in relations
    assert ("d1", "platform-team", "owned_by") in relations
    assert ("d1", "raw-auth-prd", "source") in relations


def test_add_edge_bidirectional_writes_reverse(sample_wiki: Path):
    """Forward `depends_on` from m3 → m2 must add m3 to m2.dependents."""
    add_edge(sample_wiki / "wiki", source="m3", target="m2", relation="depends_on", bidirectional=True)
    m2_text = (sample_wiki / "wiki" / "modules" / "m2.md").read_text()
    assert "m3" in m2_text  # appears in dependents
