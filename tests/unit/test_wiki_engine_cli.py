# tests/unit/test_wiki_engine_cli.py
from pathlib import Path
from click.testing import CliRunner
from tools.wiki_engine import cli


def test_cli_rebuild_edges(sample_wiki: Path):
    r = CliRunner().invoke(cli, ["rebuild-edges", "--wiki-dir", str(sample_wiki / "wiki")])
    assert r.exit_code == 0, r.output
    edges_path = sample_wiki / "wiki" / "graph" / "edges.jsonl"
    assert edges_path.read_text().strip(), "edges.jsonl should be non-empty"


def test_cli_add_edge(sample_wiki: Path):
    r = CliRunner().invoke(cli, [
        "add-edge", "--wiki-dir", str(sample_wiki / "wiki"),
        "--source", "m3", "--target", "m1", "--relation", "depends_on", "--bidirectional",
    ])
    assert r.exit_code == 0, r.output
    m1 = (sample_wiki / "wiki" / "modules" / "m1.md").read_text()
    assert "m3" in m1
