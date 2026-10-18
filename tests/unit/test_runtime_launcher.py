import importlib.util
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "assets/runtime/run.py"


def load_launcher(tmp_path, monkeypatch, args):
    spec = importlib.util.spec_from_file_location("isolated_launcher", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "__file__", str(tmp_path / ".alpha-wiki/run.py"))
    monkeypatch.setattr(module.sys, "argv", [str(SOURCE), *args])
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/status.py").write_text("# fixture\n")
    manifest = tmp_path / ".alpha-wiki/runtime/pyproject.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("[project]\n")
    return module


def test_missing_uv_reports_runtime_setup_not_product_pip_install(tmp_path, monkeypatch, capsys):
    module = load_launcher(tmp_path, monkeypatch, ["-m", "tools.status"])
    monkeypatch.setattr(module.shutil, "which", lambda _: None)

    assert module.main() == 1
    error = capsys.readouterr().err
    assert "Install uv" in error
    assert ".alpha-wiki/runtime" in error
    assert "pip install" not in error
    assert "Traceback" not in error


def test_missing_tool_does_not_install_any_dependencies(tmp_path, monkeypatch, capsys):
    module = load_launcher(tmp_path, monkeypatch, ["-m", "tools.absent"])
    monkeypatch.setattr(module.shutil, "which", lambda _: (_ for _ in ()).throw(AssertionError("must not install")))

    assert module.main() == 1
    assert "Rerun init/upgrade" in capsys.readouterr().err


def test_launcher_rejects_non_tool_module(tmp_path, monkeypatch, capsys):
    module = load_launcher(tmp_path, monkeypatch, ["-m", "pip", "install", "click"])

    assert module.main() == 2
    assert "Usage:" in capsys.readouterr().err


def test_runtime_setup_failure_preserves_exit_code(tmp_path, monkeypatch, capsys):
    import subprocess

    module = load_launcher(tmp_path, monkeypatch, ["-m", "tools.status"])
    manifest = tmp_path / ".alpha-wiki/runtime/pyproject.toml"
    manifest.write_text("[project]\n")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(tmp_path / ".venv"))
    monkeypatch.setattr(module.shutil, "which", lambda _: "/uv")

    def fail(command, **kwargs):
        assert kwargs["env"]["UV_PROJECT_ENVIRONMENT"] == str(manifest.parent / ".venv")
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(module.subprocess, "run", fail)
    assert module.main() == 7
    assert "runtime setup failed" in capsys.readouterr().err
