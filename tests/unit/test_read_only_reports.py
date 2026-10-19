from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from click.testing import CliRunner
import pytest

from tools.review import cli as review_cli, review_report
from tools.status import cli as status_cli, status_report


def _snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (
            path.is_dir(), path.stat().st_mtime_ns,
            None if path.is_dir() else path.read_bytes(),
        )
        for path in root.rglob("*")
    }


def _current_page(root: Path, graph_exists: bool) -> Path:
    wiki = root / "wiki"
    (wiki / "modules").mkdir(parents=True)
    (wiki / "modules/current.md").write_text(
        "---\ntitle: Current\nslug: current\nstatus: stable\n"
        "depends_on: ['[[dependency]]']\n---\n# Current\n\n"
        "## Open questions\n- Who owns this?\n"
    )
    if graph_exists:
        (wiki / "graph").mkdir()
        (wiki / "graph/edges.jsonl").write_text("stale, not even JSON\n")
        (wiki / "graph/open_questions.md").write_text("stale\n")
        (wiki / "graph/context_brief.md").write_text("stale\n")
    return wiki


@pytest.mark.parametrize("report", [status_report, review_report])
@pytest.mark.parametrize("graph_exists", [False, True])
def test_read_only_reports_use_current_sources_without_any_writes(tmp_path, report, graph_exists):
    wiki = _current_page(tmp_path, graph_exists)
    before = _snapshot(tmp_path)

    result = report(wiki, refresh=False)

    assert "Edges: 1" in result
    assert "Open questions: 1" in result
    assert "Missing owner/timebox: 1" in result
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("cli", [status_cli, review_cli])
def test_read_only_rejects_saved_output_before_any_mutation(tmp_path, cli):
    wiki = _current_page(tmp_path, True)
    before = _snapshot(tmp_path)

    result = CliRunner().invoke(cli, [
        "--wiki-dir", str(wiki), "--read-only", "--out", str(tmp_path / "out/report.md"),
    ])

    assert result.exit_code == 2
    assert "--read-only cannot be combined with --out" in result.output
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("module,extra,expected", [
    ("tools.status", ["--read-only"], "# Wiki Status Report"),
    ("tools.review", ["--read-only"], "# Wiki Review"),
    ("tools.wiki_search", ["--query", "current"], "[[current]]"),
])
def test_read_only_cli_subprocess_does_not_mutate_target(tmp_path, module, extra, expected):
    wiki = _current_page(tmp_path, True)
    # A prepared external interpreter avoids creating a runtime in the target.
    # Copy the actual package to catch accidental bytecode writes as well.
    shutil.copytree(Path(__file__).resolve().parents[2] / "tools", tmp_path / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    before = _snapshot(tmp_path)

    result = subprocess.run(
        [sys.executable, "-B", "-m", module, "--wiki-dir", str(wiki), *extra],
        cwd=tmp_path, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    assert _snapshot(tmp_path) == before
