from pathlib import Path
import shutil
import subprocess
import tarfile

import pytest


@pytest.mark.skipif(not shutil.which("uv"), reason="source packaging acceptance requires uv")
def test_source_archive_excludes_private_recovery_payloads(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    project = tmp_path / "package"
    shutil.copytree(root, project, ignore=shutil.ignore_patterns(
        ".git", ".venv", "dist", "__pycache__", ".pytest_cache", "*.egg-info",
        "maintenance", ".coverage",
    ))
    pending = project / ".alpha-wiki/maintenance"
    pending.mkdir(parents=True)
    (pending / "pending.json").write_text('{"text":"private recovery canary"}')
    runtime = project / ".alpha-wiki/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "uv.lock").write_text("local runtime lock canary")
    (runtime / ".venv").mkdir()
    (runtime / ".venv/private-canary").write_text("local runtime environment canary")
    graph = project / "wiki/graph"
    graph.mkdir(parents=True, exist_ok=True)
    (graph / "ingest_state.json").write_text('{"text":"private recovery canary"}')
    output = tmp_path / "distributions"
    result = subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(output)], cwd=project,
        capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with tarfile.open(next(output.glob("*.tar.gz"))) as archive:
        names = archive.getnames()
    assert any(name.endswith("/assets/runtime/run.py") for name in names)
    assert not any("/maintenance/" in name or name.endswith("/ingest_state.json") for name in names)
    assert not any("/runtime/.venv/" in name or name.endswith("/runtime/uv.lock") for name in names)
