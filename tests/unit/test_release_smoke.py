from pathlib import Path

from tools.release_smoke import run_release_smoke


def test_release_smoke_passes_on_fresh_project(tmp_path: Path):
    result = run_release_smoke(base_dir=tmp_path)
    report = result.to_markdown()

    assert result.passed
    assert "Smoke verdict: PASS" in report
    assert "Claude/Codex doctor" in report
    assert "Ingest/query/status/review" in report
    assert "Render exports" in report
