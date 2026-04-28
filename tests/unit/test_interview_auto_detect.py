from pathlib import Path
from scripts.interview import auto_detect_wiki_dir


def test_auto_detect_greenfield_returns_wiki(tmp_path: Path):
    assert auto_detect_wiki_dir(tmp_path) == "wiki"


def test_auto_detect_existing_codebase_returns_dot_wiki(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text("{}")
    assert auto_detect_wiki_dir(tmp_path) == ".wiki"


def test_auto_detect_python_project_returns_dot_wiki(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert auto_detect_wiki_dir(tmp_path) == ".wiki"
