from pathlib import Path

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig


def test_custom_wiki_dir_is_rendered_into_hooks_and_workflows(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="legacy",
        project_description="d",
        wiki_dir=".wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="all",
        ci=True,
        schema_evolve_mode="gated",
    )

    bootstrap(target=tmp_path, config=cfg)

    for hook in [
        "session-start.sh",
        "session-end.sh",
        "pre-tool-use.sh",
        "post-tool-use.sh",
        "pre-commit.sh",
    ]:
        assert 'WIKI_DIR="${WIKI_DIR:-.wiki}"' in (tmp_path / ".claude" / "hooks" / hook).read_text()

    settings = (tmp_path / ".claude" / "settings.local.json").read_text()
    assert '"path_glob": ".wiki/**"' in settings

    lint_workflow = (tmp_path / ".github" / "workflows" / "wiki-lint.yml").read_text()
    assert "--wiki-dir .wiki --dry-run" in lint_workflow
    assert "--wiki-dir wiki" not in lint_workflow

    review_workflow = (tmp_path / ".github" / "workflows" / "wiki-review.yml").read_text()
    assert 'claude -p "/alpha-wiki:review" > review.md' in review_workflow
    assert "/wiki-review" not in review_workflow

    rollup_workflow = (tmp_path / ".github" / "workflows" / "wiki-rollup.yml").read_text()
    assert 'claude -p "/alpha-wiki:rollup month --write"' in rollup_workflow
    assert "git add .wiki/rollups/ || true" in rollup_workflow
    assert "/wiki-rollup" not in rollup_workflow
    assert "git add wiki/rollups/" not in rollup_workflow


def test_post_tool_hook_rebuilds_full_graph(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="legacy",
        project_description="d",
        wiki_dir=".wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="session",
        ci=False,
        schema_evolve_mode="gated",
    )

    bootstrap(target=tmp_path, config=cfg)

    hook = (tmp_path / ".claude" / "hooks" / "post-tool-use.sh").read_text()
    assert 'WIKI_DIR="${WIKI_DIR:-.wiki}"' in hook
    assert "rebuild-edges --wiki-dir \"$WIKI_DIR\"" in hook
    assert "rebuild-context-brief --wiki-dir \"$WIKI_DIR\"" in hook
    assert "rebuild-open-questions --wiki-dir \"$WIKI_DIR\"" in hook
