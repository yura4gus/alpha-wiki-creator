"""Contract/config migration through packaged CLI subprocesses, without model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from scripts.install_codex import install_codex

ROOT = Path(__file__).resolve().parents[2]


def execute(args, cwd):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, capture_output=True,
                            text=True, timeout=90, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.mark.parametrize("platform", ["claude", "codex"])
@pytest.mark.parametrize("existing", [False, True], ids=["fresh", "brownfield"])
def test_contract_schema_migration_preserves_user_files(tmp_path, platform, existing):
    project = tmp_path / "product with spaces"
    project.mkdir()
    wiki_dir = ".memory" if existing else "wiki"
    originals = {}
    if existing:
        originals = {
            "AGENTS.md": "# Existing user contract\nKeep API compatibility.\n",
            "CLAUDE.md": "# Existing user instructions\n**Wiki dir:** `.memory/`\n",
            "README.md": "# User product\n",
            "pyproject.toml": '[project]\nname="product"\nversion="1.0.0"\ndependencies=[]\n',
            "uv.lock": "user lockfile\n",
            ".alpha-wiki/config.yaml": "entity_types: []\ncross_ref_rules: []\nuser_setting: keep\n",
            ".claude/settings.local.json": '{"hooks": {}, "env": {"USER_MARKER":"keep"}}\n',
            ".codex/hooks.json": '{"hooks": {}, "user_setting":"keep"}\n',
            ".claude/hooks/session-start.sh": "#!/bin/sh\n# user hook\nexit 0\n",
            ".memory/index.md": "# User index\n",
            ".memory/log.md": "# User log\n",
            ".memory/graph/context_brief.md": "# User context\n",
            ".memory/.obsidian/graph.json": '{"user_view":true}\n',
        }
        for relative, content in originals.items():
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    bootstrap_root = ROOT
    if platform == "codex":
        bootstrap_root = tmp_path / "plugins/alpha-wiki"
        install_codex(plugin_dir=bootstrap_root,
                      marketplace_path=tmp_path / ".agents/plugins/marketplace.json", activate=False)
    command = [sys.executable, "-m", "scripts.bootstrap_cli", "--target", project, "--ci"]
    before = {str(path.relative_to(project)): (path.read_bytes(), path.stat().st_mode)
              for path in project.rglob("*") if path.is_file()}
    execute([*command, "--dry-run"], bootstrap_root)
    assert {str(path.relative_to(project)): (path.read_bytes(), path.stat().st_mode)
            for path in project.rglob("*") if path.is_file()} == before
    execute(command, bootstrap_root)
    adapter = project / ".claude/CLAUDE.md"
    assert "@../AGENTS.md" in adapter.read_text()
    assert adapter.parent.joinpath("../AGENTS.md").resolve() == (project / "AGENTS.md").resolve()
    assert not (project / wiki_dir / "agentops").exists()
    if existing:
        assert not (project / "wiki").exists()
    else:
        assert not (project / "CLAUDE.md").exists()
        assert "## Engineering Writing" in (project / "AGENTS.md").read_text()
        assert "Never shorten away an unresolved question." in (project / "AGENTS.md").read_text()
        assert "docs/roadmap-execution.md" not in (project / "AGENTS.md").read_text()
        assert yaml.safe_load((project / ".alpha-wiki/config.yaml").read_text())["wiki_dir"] == wiki_dir
    for relative, content in originals.items():
        assert (project / relative).read_text() == content, relative
    execute([*command, "--upgrade"], bootstrap_root)
    for relative, content in originals.items():
        assert (project / relative).read_text() == content, relative
    config = project / ".alpha-wiki/config.yaml"
    old = yaml.safe_load(config.read_text())
    instructions = {path: path.read_bytes() for path in
                    (project / "AGENTS.md", adapter, project / "CLAUDE.md") if path.exists()}
    spec = {"name": "migration", "dir": "data/migrations", "frontmatter_required": ["title", "slug"]}
    script = "from pathlib import Path; from scripts.add_entity_type import add_entity_type; add_entity_type(Path(" + repr(str(project)) + "), " + repr(spec) + ")"
    execute([sys.executable, "-c", script], bootstrap_root)
    new = yaml.safe_load(config.read_text())
    assert new["entity_types"][:-1] == old["entity_types"]
    assert new["cross_ref_rules"] == old["cross_ref_rules"]
    assert (project / wiki_dir / "data/migrations").is_dir()
    assert "schema-change" in (project / wiki_dir / "log.md").read_text()
    assert all(path.read_bytes() == content for path, content in instructions.items())
    # Directly execute the generated Claude route; quote handling must survive spaces.
    if not existing:
        settings = json.loads((project / ".claude/settings.local.json").read_text())
        route = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        result = subprocess.run(["bash", "-c", route], cwd=project,
                                env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert "Context brief" in result.stdout
