"""Execute the generated runtime, not imports from the development environment."""
from __future__ import annotations

import json
import hashlib
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


def tree_state(root):
    return {
        str(path.relative_to(root)): (
            path.stat().st_mode, path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


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
    environment = dict(os.environ)
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
    navigation = wiki / "contracts/_index.md"
    navigation.write_text(
        "---\ntitle: Contract Catalog\nslug: contracts-index\ndate_updated: 2026-10-19\n"
        "belongs_to: '[[service]]'\n---\n# Contract Catalog\n\nSee [[service]].\n"
    )
    navigation_before = navigation.read_bytes()
    with (wiki / "index.md").open("a") as stream:
        stream.write("\n[[service]]\n[[contracts/_index|Contract Catalog]]\n")
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
    execute(["git", "add", "."], project)
    execute(["git", "commit", "-m", "initial memory"], project)
    page = wiki / "specs/project-brief.md"
    source.write_text(source.read_text() + "Upstream change: maintain existing documents in place.\n")
    plan = json.loads(run("document_worker", "plan", "--document", f"{wiki_dir}/specs/project-brief.md"))
    assert len(plan["jobs"]) == 1
    assert "Pending source-bound documents: 1" in run("status", "--wiki-dir", wiki_dir)
    maintenance = project / ".alpha-wiki/maintenance"
    maintenance.mkdir()
    plan_path, edits_path = maintenance / "plan.json", maintenance / "edits.json"
    plan_path.write_text(json.dumps(plan))
    edits_path.write_text(json.dumps({"summary": "Reflect upstream maintenance rule", "updates": [
        {"document": f"{wiki_dir}/specs/project-brief.md",
         "text": page.read_text() + "\n## Maintained Context\n\nMaintain existing documents in place.\nRepeated context.\nRepeated context.\n"}
    ]}))
    run("document_worker", "apply", "--plan", plan_path, "--edits", edits_path)
    log_before = (wiki / "log.md").read_bytes()
    assert json.loads(run("document_worker", "apply", "--plan", plan_path, "--edits", edits_path))["status"] == "unchanged"
    assert (wiki / "log.md").read_bytes() == log_before
    assert "Pending source-bound documents: 0" in run("status", "--wiki-dir", wiki_dir)
    plan = json.loads(run("document_worker", "plan", "--compact", "--document", f"{wiki_dir}/specs/project-brief.md"))
    plan_path.write_text(json.dumps(plan))
    edits_path.write_text(json.dumps({"summary": "Compact repeated context without losing requirements", "updates": [
        {"document": f"{wiki_dir}/specs/project-brief.md", "text": page.read_text().replace("Repeated context.\n", "", 1)}
    ]}))
    run("document_worker", "apply", "--plan", plan_path, "--edits", edits_path)
    assert page.read_text().count("Repeated context.") == 1
    run("document_worker", "check")
    run("ingest_pipeline", "--wiki-dir", wiki_dir, source)
    assert not (wiki / "specs/project-brief-2.md").exists()
    assert "project-brief" in run("wiki_search", "--wiki-dir", wiki_dir, "--query", "isolated agent memory")
    assert "Gap Check" in run("status", "--wiki-dir", wiki_dir)
    assert "- Cluster link gaps: 0" in run("status", "--wiki-dir", wiki_dir, "--read-only")
    run("lint", "--wiki-dir", wiki_dir, "--config", ".alpha-wiki/config.yaml", "--fix")
    assert "Wiki Review" in run("review", "--wiki-dir", wiki_dir, "--config", ".alpha-wiki/config.yaml")
    run("render_mermaid", "--wiki-dir", wiki_dir)
    run("render_dot", "--wiki-dir", wiki_dir)
    run("render_html", "--wiki-dir", wiki_dir)
    assert (wiki / "render/html/index.html").is_file()
    assert (wiki / "graph/graph.mmd").is_file()
    assert (wiki / "graph/graph.dot").is_file()
    assert navigation.read_bytes() == navigation_before
    assert (wiki / "render/html/contracts/_index.html").is_file()
    assert 'href="contracts/_index.html"' in (wiki / "render/html/index.html").read_text()
    assert 'href="../modules/service.html"' in (wiki / "render/html/contracts/_index.html").read_text()
    assert 'contracts_index["Contract Catalog"]' in (wiki / "graph/graph.mmd").read_text()
    assert '"contracts-index" [label="Contract Catalog"' in (wiki / "graph/graph.dot").read_text()

    payload = json.dumps({"cwd": str(project / "removed-worktree"), "tool_name": "Write",
                          "tool_input": {"file_path": str(module)}})
    if platform == "claude":
        environment["CLAUDE_PROJECT_DIR"] = str(project)

    recovered = ([project / ".claude/hooks" / (event + ".sh") for event in
                  ("session-start", "session-end", "pre-tool-use", "post-tool-use")]
                 if platform == "claude" else [project / ".codex/hooks/alpha_wiki_hook.py"])
    expected = {path: path.read_bytes() for path in recovered}
    for path in recovered:
        path.unlink()
    user_hook = project / ".claude/hooks/user-owned.sh"
    user_hook.write_text("#!/bin/sh\n# Independent user hook.\nexit 0\n")
    user_hook.chmod(0o700)
    existing_hook = (project / ".codex/hooks/alpha_wiki_hook.py" if platform == "claude"
                     else project / ".claude/hooks/session-start.sh")
    existing_hook.write_text(existing_hook.read_text() + "\n# Preserve user customization.\n")
    protected = {path: (path.read_bytes(), path.stat().st_mode) for path in
                 (user_hook, existing_hook, project / ".claude/settings.local.json",
                  project / ".codex/hooks.json", project / ".alpha-wiki/config.yaml")}
    upgrade = [sys.executable, "-m", "scripts.bootstrap_cli", "--target", project, "--runtime-only"]
    before = tree_state(project)
    assert "completed writes: 0" in execute([*upgrade, "--dry-run"], bootstrap_root)
    assert tree_state(project) == before
    assert f"completed writes: {len(recovered)}" in execute(upgrade, bootstrap_root)
    for path, content in expected.items():
        assert path.read_bytes() == content
        assert path.stat().st_mode & 0o111 == 0o111
    for path, state in protected.items():
        assert (path.read_bytes(), path.stat().st_mode) == state
    repaired = tree_state(project)
    assert "completed writes: 0" in execute(upgrade, bootstrap_root)
    assert tree_state(project) == repaired

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
    assert (wiki / "log.md").read_bytes() == log

    runtime_python = project / ".alpha-wiki/runtime/.venv/bin/python"
    assert runtime_python.is_file()
    execute([runtime_python, "-I", "-c", "import click, yaml, jinja2"], project)
    manifest = project / ".alpha-wiki/runtime/pyproject.toml"
    marker = runtime_python.parents[1] / ".alpha-wiki-manifest"
    previous = marker.read_text()
    manifest.write_text(manifest.read_text() + "\n# Changed runtime manifest\n")
    assert "Gap Check" in run("status", "--wiki-dir", wiki_dir)
    assert marker.read_text() != previous
    execute([*bootstrap, "--upgrade"], bootstrap_root)
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
