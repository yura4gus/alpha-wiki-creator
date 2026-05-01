import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_obsidian_graph_color_groups_match_semantic_contract():
    graph = json.loads((ROOT / "assets" / "obsidian" / "graph.json").read_text())
    groups = graph["colorGroups"]

    assert groups[0]["color"]["rgb"] == int("E94B43", 16)
    assert "path:services/" in groups[0]["query"]
    assert "path:repos/" in groups[0]["query"]

    assert groups[1]["color"]["rgb"] == int("16A34A", 16)
    assert "path:modules/" in groups[1]["query"]
    assert "path:domains/" in groups[1]["query"]
    assert "path:adapters/" in groups[1]["query"]

    assert groups[2]["color"]["rgb"] == int("2563EB", 16)
    assert "path:features/" in groups[2]["query"]
    assert "path:flows/" in groups[2]["query"]
    assert "path:application/" in groups[2]["query"]

    assert groups[3]["color"]["rgb"] == int("111111", 16)
    assert "path:decisions/" in groups[3]["query"]
    assert "path:papers/" in groups[3]["query"]

    assert groups[4]["color"]["rgb"] == int("F97316", 16)
    assert "path:contracts/" in groups[4]["query"]


def test_obsidian_legend_explains_graph_grouping():
    legend = (ROOT / "assets" / "obsidian" / "COLOR-LEGEND.md").read_text()

    for phrase in [
        "Repo / service",
        "Module / domain",
        "Feature / function",
        "Document / evidence",
        "Color is not cluster",
        "Grouping rule",
    ]:
        assert phrase in legend
