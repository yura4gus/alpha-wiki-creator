"""Interactive interview → InterviewConfig."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class EntityTypeSpec:
    name: str
    dir: str
    frontmatter_required: list[str]
    frontmatter_optional: list[str] = field(default_factory=list)
    sections_required: list[str] = field(default_factory=list)


@dataclass
class InterviewConfig:
    project_name: str
    project_description: str
    wiki_dir: str  # "wiki" or ".wiki"
    preset: str  # software-project | research | product | personal | knowledge-base | custom
    overlay: str  # none | clean | hexagonal | ddd | ddd+clean | ddd+hexagonal | layered
    custom_entity_types: list[EntityTypeSpec] | None
    i18n_languages: list[str]
    hooks: str  # all | session | git | none
    ci: bool
    schema_evolve_mode: str  # gated | auto
    obsidian: bool = True
    python_version: str = "3.12"
    package_manager: str = "uv"


CODE_MARKERS = {
    "src",
    "lib",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "tsconfig.json",
    "deno.json",
}


def auto_detect_wiki_dir(cwd: Path) -> str:
    """If existing codebase markers found → .wiki/, else wiki/."""
    for marker in CODE_MARKERS:
        if (cwd / marker).exists():
            return ".wiki"
    return "wiki"


def config_from_answers(answers: dict) -> InterviewConfig:
    return InterviewConfig(
        project_name=answers["project_name"],
        project_description=answers["project_description"],
        wiki_dir=answers["wiki_dir"],
        preset=answers["preset"],
        overlay=answers.get("overlay", "none"),
        custom_entity_types=answers.get("custom_entity_types"),
        i18n_languages=(
            [answers["i18n"]]
            if isinstance(answers.get("i18n"), str)
            else answers.get("i18n", ["en"])
        ),
        hooks=answers.get("hooks", "all"),
        ci=bool(answers.get("ci", False)),
        schema_evolve_mode=answers.get("schema_evolve_mode", "gated"),
    )
