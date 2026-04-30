from pathlib import Path

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig


SESSION_HOOKS = {
    "session-start.sh",
    "session-end.sh",
    "pre-tool-use.sh",
    "post-tool-use.sh",
}
GIT_HOOKS = {
    "pre-commit.sh",
    "install-hooks.sh",
}


def _cfg(hooks: str) -> InterviewConfig:
    return InterviewConfig(
        project_name="demo",
        project_description="d",
        wiki_dir="wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks=hooks,
        ci=False,
        schema_evolve_mode="gated",
    )


def _installed_hooks(root: Path) -> set[str]:
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.exists():
        return set()
    return {p.name for p in hooks_dir.iterdir() if p.is_file()}


def test_hook_mode_all_installs_session_and_git_hooks(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg("all"))

    assert _installed_hooks(tmp_path) == SESSION_HOOKS | GIT_HOOKS
    assert (tmp_path / ".claude" / "settings.local.json").exists()


def test_hook_mode_session_installs_only_session_hooks(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg("session"))

    assert _installed_hooks(tmp_path) == SESSION_HOOKS
    assert (tmp_path / ".claude" / "settings.local.json").exists()


def test_hook_mode_git_installs_only_git_hooks(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg("git"))

    assert _installed_hooks(tmp_path) == GIT_HOOKS
    assert not (tmp_path / ".claude" / "settings.local.json").exists()


def test_hook_mode_none_installs_no_hooks_or_settings(tmp_path: Path):
    bootstrap(target=tmp_path, config=_cfg("none"))

    assert _installed_hooks(tmp_path) == set()
    assert not (tmp_path / ".claude" / "settings.local.json").exists()
