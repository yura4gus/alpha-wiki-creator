from pathlib import Path

from scripts.bootstrap import upgrade_runtime_assets
from scripts.bootstrap_cli import bootstrap_project


def test_runtime_upgrade_preserves_user_schema_contracts_and_hook_routing(tmp_path: Path):
    bootstrap_project(tmp_path, wiki_dir=".wiki", hooks="all", ci=True)
    config = tmp_path / ".alpha-wiki/config.yaml"
    config.write_text(config.read_text() + "\nuser_schema_marker: preserve-me\n")
    contract = tmp_path / "CLAUDE.md"
    contract.write_text(contract.read_text() + "\nUser-owned project instructions.\n")
    routing = tmp_path / ".codex/hooks.json"
    routing.write_text(routing.read_text() + "\n")
    wiki = tmp_path / ".wiki"
    (wiki / "graph/edges.jsonl").write_text("preserve generated snapshot\n")
    protected = [config, contract, routing, tmp_path / "AGENTS.md", tmp_path / "README.md",
                 tmp_path / ".github/workflows/wiki-lint.yml", wiki / "log.md",
                 wiki / "graph/edges.jsonl"]
    before = {path: path.read_bytes() for path in protected}
    (tmp_path / ".alpha-wiki/run.py").unlink()

    report = upgrade_runtime_assets(tmp_path)

    assert report.written
    assert (tmp_path / ".alpha-wiki/run.py").is_file()
    assert not (tmp_path / "pyproject.toml").exists()
    assert 'WIKI_DIR="${WIKI_DIR:-.wiki}"' in (tmp_path / ".claude/hooks/post-tool-use.sh").read_text()
    for path, content in before.items():
        assert path.read_bytes() == content, path


def test_runtime_only_dry_run_writes_nothing(tmp_path: Path):
    bootstrap_project(tmp_path)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    report = upgrade_runtime_assets(tmp_path, dry_run=True)

    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert report.planned and not report.written
    assert after == before
