from pathlib import Path
import os
from tools._env import load_env

def test_load_env_reads_local_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO=bar\nBAZ=qux\n")
    load_env()
    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux"

def test_load_env_local_overrides_home(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("FOO=home\n")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".env").write_text("FOO=local\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(proj)
    load_env()
    assert os.environ["FOO"] == "local"
