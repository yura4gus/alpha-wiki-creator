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


def test_add_edge_bidirectional_writes_reverse(sample_wiki: Path):
    """Forward `depends_on` from m3 → m2 must add m3 to m2.dependents."""
    add_edge(sample_wiki / "wiki", source="m3", target="m2", relation="depends_on", bidirectional=True)
    m2_text = (sample_wiki / "wiki" / "modules" / "m2.md").read_text()
    assert "m3" in m2_text  # appears in dependents
