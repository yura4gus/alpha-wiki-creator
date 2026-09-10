"""Non-interactive bootstrap entry point for plugin-driven agent workflows."""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.bootstrap import BootstrapReport, bootstrap
from scripts.interview import InterviewConfig


PRESETS = ("software-project", "research", "product", "personal", "knowledge-base")
OVERLAYS = ("none", "clean", "hexagonal", "ddd", "ddd+clean", "ddd+hexagonal", "layered")


def bootstrap_project(
    target: Path,
    *,
    project_name: str | None = None,
    description: str = "",
    wiki_dir: str = "wiki",
    preset: str = "software-project",
    overlay: str = "none",
    hooks: str = "all",
    ci: bool = False,
    schema_evolve_mode: str = "gated",
    obsidian: bool = True,
    upgrade: bool = False,
    dry_run: bool = False,
) -> BootstrapReport:
    target = target.expanduser().resolve()
    config = InterviewConfig(
        project_name=project_name or target.name,
        project_description=description or f"Alpha-Wiki memory for {project_name or target.name}",
        wiki_dir=wiki_dir,
        preset=preset,
        overlay=overlay,
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks=hooks,
        ci=ci,
        schema_evolve_mode=schema_evolve_mode,
        obsidian=obsidian,
    )
    return bootstrap(target, config, upgrade=upgrade, dry_run=dry_run)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Alpha-Wiki into a target project.")
    parser.add_argument("--target", type=Path, required=True, help="Target project directory.")
    parser.add_argument("--project-name", help="Project name. Defaults to the target directory name.")
    parser.add_argument("--description", default="", help="One-line project purpose.")
    parser.add_argument("--wiki-dir", default="wiki")
    parser.add_argument("--preset", choices=PRESETS, default="software-project")
    parser.add_argument("--overlay", choices=OVERLAYS, default="none")
    parser.add_argument("--hooks", choices=("all", "session", "git", "none"), default="all")
    parser.add_argument("--ci", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--schema-evolve-mode", choices=("gated", "auto"), default="gated")
    parser.add_argument("--obsidian", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = bootstrap_project(
        args.target,
        project_name=args.project_name,
        description=args.description,
        wiki_dir=args.wiki_dir,
        preset=args.preset,
        overlay=args.overlay,
        hooks=args.hooks,
        ci=args.ci,
        schema_evolve_mode=args.schema_evolve_mode,
        obsidian=args.obsidian,
        upgrade=args.upgrade,
        dry_run=args.dry_run,
    )
    print(report.to_markdown())


if __name__ == "__main__":
    cli()
