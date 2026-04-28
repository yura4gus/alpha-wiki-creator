"""Shared pytest fixtures for alpha-wiki tests."""
from pathlib import Path
import pytest
import shutil

FIXTURES_ROOT = Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_wiki(tmp_path: Path) -> Path:
    """Copy of tests/fixtures/sample-wiki/ in a tmp dir; tests can mutate freely."""
    src = FIXTURES_ROOT / "sample-wiki"
    dst = tmp_path / "sample-wiki"
    shutil.copytree(src, dst)
    return dst
