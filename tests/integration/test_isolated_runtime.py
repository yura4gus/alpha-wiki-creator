"""Execute the generated runtime, not imports from the development environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.install_codex import install_codex


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not shutil.which("uv"), reason="isolated runtime acceptance requires uv")


def execute(args, cwd, env=None, payload=None):
    result = subprocess.run(
        [str(arg) for arg in args], cwd=cwd, env=env, input=payload,
        capture_output=True, text=True, check=False, timeout=90,
    )
    assert result.returncode == 0, f"{args}\n{result.stdout}\n{result.stderr}"
    return result.stdout


@pytest.mark.parametrize("platform", ["claude", "codex"])
@pytest.mark.parametrize("existing", [False, True], ids=["fresh", "brownfield"])
def test_generated_runtime_lifecycle_and_hooks(tmp_path: Path, platform: str, existing: bool):
    project = tmp_path / "product with spaces"
    project.mkdir()
    wiki_dir = ".wiki" if existing else "wiki"
    originals = {}
    if existing:
        originals = {
            "pyproject.toml": '[project]\nname="existing-product"\nversion="1.0.0"\nrequires-python=">=3.12"\ndependencies=[]\n[tool.uv]\npackage=false\n[tool.uv.workspace]\nmembers=[]\n',
            "uv.lock": "product lock must not be read or rewritten by Alpha-Wiki\n",
            "requirements.txt": "# product requirements\n",
            "package.json": '{"name":"existing-product","private":true}\n',
            ".gitignore": ".venv/\n",
        }
        for name, text in originals.items():
            (project / name).write_text(text)
        execute(["uv", "venv", "--python", sys.executable, project / ".venv"], ROOT)
    entry_python = project / ".venv/bin/python" if existing else Path(sys.executable)
    environment = {**os.environ, "UV_OFFLINE": "1"}
    environment.pop("PYTHONPATH", None)
    if existing:
        environment["VIRTUAL_ENV"] = str(project / ".venv")
        environment["UV_PROJECT_ENVIRONMENT"] = str(project / ".venv")
        missing = subprocess.run(
            [str(entry_python), "-c", "import click"], cwd=project,
            capture_output=True, text=True, check=False,
        )
        assert missing.returncode != 0 and "No module named 'click'" in missing.stderr

    bootstrap_root = ROOT
    if platform == "codex":
        plugin = tmp_path / "plugins/alpha-wiki"
        marketplace = tmp_path / ".agents/plugins/marketplace.json"
        install_codex(plugin_dir=plugin, marketplace_path=marketplace, activate=False)
        bootstrap_root = plugin
        environment.update(ALPHA_WIKI_CODEX_PLUGIN_DIR=str(plugin),
                           ALPHA_WIKI_CODEX_MARKETPLACE=str(marketplace),
                           ALPHA_WIKI_CODEX_SKILLS_DIR=str(tmp_path / ".agents/skills"))

    bootstrap = [sys.executable, "-m", "scripts.bootstrap_cli", "--target", project,
                 "--project-name", "runtime-test", "--wiki-dir", wiki_dir, "--ci"]
    execute(bootstrap, bootstrap_root)
    assert (project / "pyproject.toml").exists() == existing
    launcher = project / ".alpha-wiki/run.py"
    wiki = project / wiki_dir
    module = wiki / "modules/service.md"
    module.write_text("---\ntitle: Service\nslug: service\nstatus: stable\ndate_updated: 2026-10-17\n---\n# Service\n")
    with (wiki / "index.md").open("a") as stream:
        stream.write("\n[[service]]\n")
    source = project / "raw/docs/project-brief.md"
    source.write_text("# Project Brief\n\nThe runtime acceptance project supports isolated agent memory.\n")
    execute(["git", "init"], project)
    execute(["git", "config", "user.email", "runtime@example.test"], project)
    execute(["git", "config", "user.name", "Runtime Test"], project)
    execute(["git", "add", "."], project)
    execute(["git", "commit", "-m", "bootstrap"], project)

    nested = project / "src"
    nested.mkdir()

    def run(name, *args):
        return execute([entry_python, launcher, "-m", "tools." + name, *args], nested, environment)

    report = run("doctor", "--project-dir", ".", "--platform", platform, "--refresh")
    assert "- Fail: 0" in report
    assert "PASS `isolated runtime`" in report
    run("ingest_pipeline", "--wiki-dir", wiki_dir, "--slot", "specs", "--belongs-to", "service", source)
    assert "project-brief" in run("wiki_search", "--wiki-dir", wiki_dir, "--query", "isolated agent memory")
    assert "Gap Check" in run("status", "--wiki-dir", wiki_dir)
    run("lint", "--wiki-dir", wiki_dir, "--config", ".alpha-wiki/config.yaml", "--fix")
    assert "Wiki Review" in run("review", "--wiki-dir", wiki_dir, "--config", ".alpha-wiki/config.yaml")
    run("render_mermaid", "--wiki-dir", wiki_dir)
    run("render_dot", "--wiki-dir", wiki_dir)
    run("render_html", "--wiki-dir", wiki_dir)
    assert (wiki / "render/html/index.html").is_file()
    assert (wiki / "graph/graph.mmd").is_file()
    assert (wiki / "graph/graph.dot").is_file()

    payload = json.dumps({"cwd": str(project / "removed-worktree"), "tool_name": "Write",
                          "tool_input": {"file_path": str(module)}})
    if platform == "claude":
        environment["CLAUDE_PROJECT_DIR"] = str(project)

    def hook(event):
        command = (["bash", project / ".claude/hooks" / (event + ".sh")]
                   if platform == "claude" else
                   [entry_python, project / ".codex/hooks/alpha_wiki_hook.py",
                    {"session-start": "session-start", "session-end": "session-end",
                     "pre-tool-use": "pre-tool", "post-tool-use": "post-tool"}[event],
                    "--wiki-dir", wiki_dir])
        return execute(command, nested, environment, payload)

    for name in ("edges.jsonl", "context_brief.md", "open_questions.md"):
        (wiki / "graph" / name).write_text("STALE\n")
    hook("pre-tool-use")
    post = hook("post-tool-use")
    assert "failed" not in post.lower()
    for name in ("edges.jsonl", "context_brief.md", "open_questions.md"):
        assert (wiki / "graph" / name).read_text() != "STALE\n"
    assert "context" in hook("session-start").lower()
    log = (wiki / "log.md").read_bytes()
    hook("session-end")
    assert (wiki / "log.md").read_bytes().startswith(log)
    assert "session-end |" in (wiki / "log.md").read_text()

    runtime_python = project / ".alpha-wiki/runtime/.venv/bin/python"
    assert runtime_python.is_file()
    execute([runtime_python, "-I", "-c", "import click, yaml, jinja2"], project)
    manifest = project / ".alpha-wiki/runtime/pyproject.toml"
    marker = runtime_python.parents[1] / ".alpha-wiki-manifest"
    previous = marker.read_text()
    manifest.write_text(manifest.read_text() + "\n# Changed runtime manifest\n")
    assert "Gap Check" in run("status", "--wiki-dir", wiki_dir)
    assert marker.read_text() != previous
    preserved = {path: path.read_bytes() for path in (
        project / ".alpha-wiki/config.yaml", project / "AGENTS.md", project / "CLAUDE.md",
        project / ".claude/settings.local.json", project / ".codex/hooks.json",
        project / ".github/workflows/wiki-lint.yml", wiki / "index.md", wiki / "log.md",
    )}
    upgrade = [sys.executable, "-m", "scripts.bootstrap_cli", "--target", project, "--runtime-only"]
    if platform == "codex":
        upgrade = ["uv", "run", "--project", bootstrap_root, "--directory", bootstrap_root,
                   "--no-dev", "python", "-m", "scripts.bootstrap_cli", "--target", project, "--runtime-only"]
        upgrade_environment = {**environment, "UV_PROJECT_ENVIRONMENT": str(bootstrap_root / ".venv")}
    else:
        upgrade_environment = environment
    execute(upgrade, bootstrap_root, upgrade_environment)
    for path, content in preserved.items():
        assert path.read_bytes() == content, path
    assert "Gap Check" in run("status", "--wiki-dir", wiki_dir)
    without_uv = {**environment, "PATH": "/usr/bin:/bin"}
    assert shutil.which("uv", path=without_uv["PATH"]) is None
    assert "Gap Check" in execute(
        [entry_python, launcher, "-m", "tools.status", "--wiki-dir", wiki_dir], nested, without_uv,
    )
    for name, text in originals.items():
        assert (project / name).read_text() == text, name
    if existing:
        still_missing = subprocess.run([str(entry_python), "-c", "import click"], cwd=project,
                                       capture_output=True, text=True, check=False)
        assert still_missing.returncode != 0 and "No module named 'click'" in still_missing.stderr
