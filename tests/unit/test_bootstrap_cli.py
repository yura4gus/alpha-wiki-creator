from pathlib import Path

from scripts.bootstrap_cli import bootstrap_project


def test_bootstrap_cli_backend_creates_codex_project_runtime(tmp_path: Path):
    project = tmp_path / "fresh-project"

    report = bootstrap_project(
        project,
        description="Fresh Codex project",
        hooks="session",
        ci=False,
    )

    assert not report.has_conflicts
    assert (project / "AGENTS.md").exists()
    assert (project / "CLAUDE.md").exists()
    assert (project / ".codex" / "hooks.json").exists()
    assert (project / ".codex" / "hooks" / "alpha_wiki_hook.py").exists()
    assert (project / "wiki" / "graph" / "context_brief.md").exists()


def test_bootstrap_cli_backend_supports_read_only_dry_run(tmp_path: Path):
    project = tmp_path / "planned-project"

    report = bootstrap_project(project, dry_run=True)

    assert report.dry_run
    assert any(path.endswith("AGENTS.md") for path in report.planned)
    assert any(path.endswith(".codex/hooks.json") for path in report.planned)
    assert not project.exists()
