"""Alpha-Wiki install and lifecycle verification."""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import click
import yaml

from tools._models import LintSeverity
from tools.lint import run_all_checks
from tools.wiki_engine import rebuild_context_brief, rebuild_edges, rebuild_open_questions, scan_wiki

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

TOOL_MODULES = [
    "tools.doctor",
    "tools.init_audit",
    "tools.wiki_engine",
    "tools.lint",
    "tools.status",
    "tools.review",
    "tools.rollup",
    "tools.classify",
    "tools.claims_check",
    "tools.contracts_check",
    "tools.contradiction_detector",
]

GRAPH_ARTIFACTS = [
    "edges.jsonl",
    "context_brief.md",
    "open_questions.md",
]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    message: str
    action: str | None = None


@dataclass(frozen=True)
class DoctorResult:
    project_dir: Path
    wiki_dir: Path
    platform: str
    checks: list[DoctorCheck]

    @property
    def failures(self) -> list[DoctorCheck]:
        return [check for check in self.checks if check.status == FAIL]

    @property
    def warnings(self) -> list[DoctorCheck]:
        return [check for check in self.checks if check.status == WARN]

    @property
    def passes(self) -> list[DoctorCheck]:
        return [check for check in self.checks if check.status == PASS]

    def to_markdown(self) -> str:
        lines = [
            "# Alpha-Wiki Doctor",
            "",
            f"- Project: `{self.project_dir}`",
            f"- Wiki dir: `{self.wiki_dir}`",
            f"- Platform: `{self.platform}`",
            "",
            "## Summary",
            "",
            f"- Pass: {len(self.passes)}",
            f"- Warn: {len(self.warnings)}",
            f"- Fail: {len(self.failures)}",
            "",
            "## Checks",
            "",
        ]
        for check in self.checks:
            lines.append(f"- {check.status} `{check.name}`: {check.message}")
            if check.action:
                lines.append(f"  Action: {check.action}")
        return "\n".join(lines) + "\n"


def run_doctor(
    project_dir: Path,
    wiki_dir: Path | None = None,
    platform: str = "auto",
    refresh: bool = False,
) -> DoctorResult:
    project = project_dir.resolve()
    wiki = _resolve_wiki_dir(project, wiki_dir)
    checks: list[DoctorCheck] = []

    checks.extend(_check_python_and_tools())
    checks.extend(_check_project_config(project))
    checks.extend(_check_wiki(project, wiki, refresh=refresh))
    checks.extend(_check_lint(project, wiki))
    checks.extend(_check_platform(project, platform))

    return DoctorResult(project_dir=project, wiki_dir=wiki, platform=platform, checks=checks)


def doctor_report(
    project_dir: Path,
    wiki_dir: Path | None = None,
    platform: str = "auto",
    refresh: bool = False,
) -> str:
    return run_doctor(project_dir, wiki_dir=wiki_dir, platform=platform, refresh=refresh).to_markdown()


def _resolve_wiki_dir(project_dir: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit if explicit.is_absolute() else project_dir / explicit
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        match = re.search(r"Wiki dir.*?`([^`]+)`", claude_md.read_text())
        if match:
            return project_dir / match.group(1).rstrip("/")
    return project_dir / "wiki"


def _check_python_and_tools() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if sys.version_info >= (3, 12):
        checks.append(DoctorCheck("python", PASS, f"{sys.version.split()[0]}"))
    else:
        checks.append(DoctorCheck("python", FAIL, f"{sys.version.split()[0]} is below 3.12"))

    if shutil.which("uv"):
        checks.append(DoctorCheck("uv", PASS, "uv is available on PATH"))
    else:
        checks.append(DoctorCheck("uv", WARN, "uv is not available on PATH", "Install uv or run tools with the active Python environment."))

    missing = [name for name in TOOL_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        checks.append(DoctorCheck("tool imports", FAIL, f"missing modules: {', '.join(missing)}"))
    else:
        checks.append(DoctorCheck("tool imports", PASS, f"{len(TOOL_MODULES)} deterministic tool modules import"))
    return checks


def _check_project_config(project_dir: Path) -> list[DoctorCheck]:
    config = project_dir / ".alpha-wiki" / "config.yaml"
    if not config.exists():
        return [DoctorCheck("config", FAIL, ".alpha-wiki/config.yaml is missing", "Run /alpha-wiki:init or restore the generated config.")]
    try:
        data = yaml.safe_load(config.read_text()) or {}
    except yaml.YAMLError as exc:
        return [DoctorCheck("config", FAIL, f".alpha-wiki/config.yaml is invalid YAML: {exc}")]
    entity_count = len(data.get("entity_types", []))
    return [DoctorCheck("config", PASS, f".alpha-wiki/config.yaml loaded ({entity_count} entity type(s))")]


def _check_wiki(project_dir: Path, wiki_dir: Path, refresh: bool) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if not wiki_dir.exists():
        return [DoctorCheck("wiki directory", FAIL, f"{wiki_dir} does not exist", "Run /alpha-wiki:init first.")]

    for name in ("index.md", "log.md"):
        path = wiki_dir / name
        if path.exists():
            checks.append(DoctorCheck(name, PASS, f"{_display_path(path, project_dir)} exists"))
        else:
            checks.append(DoctorCheck(name, FAIL, f"{_display_path(path, project_dir)} is missing"))

    if refresh:
        try:
            edges = rebuild_edges(wiki_dir)
            rebuild_context_brief(wiki_dir)
            rebuild_open_questions(wiki_dir)
            checks.append(DoctorCheck("graph refresh", PASS, f"rebuilt graph artifacts ({len(edges)} edge(s))"))
        except Exception as exc:  # pragma: no cover - defensive boundary
            checks.append(DoctorCheck("graph refresh", FAIL, f"graph rebuild failed: {exc}"))

    graph_dir = wiki_dir / "graph"
    if graph_dir.exists():
        checks.append(DoctorCheck("graph directory", PASS, f"{_display_path(graph_dir, project_dir)} exists"))
    else:
        checks.append(DoctorCheck("graph directory", WARN, f"{_display_path(graph_dir, project_dir)} is missing", "Run doctor --refresh or /alpha-wiki:status."))

    for artifact in GRAPH_ARTIFACTS:
        path = graph_dir / artifact
        if path.exists():
            checks.append(DoctorCheck(f"graph/{artifact}", PASS, f"{_display_path(path, project_dir)} exists"))
        else:
            checks.append(DoctorCheck(f"graph/{artifact}", WARN, f"{_display_path(path, project_dir)} is missing", "Run doctor --refresh or /alpha-wiki:status."))

    pages = scan_wiki(wiki_dir)
    if pages:
        checks.append(DoctorCheck("wiki pages", PASS, f"{len(pages)} source page(s) detected"))
    else:
        checks.append(DoctorCheck("wiki pages", WARN, "no durable wiki pages detected yet", "Run /alpha-wiki:ingest on the first durable source."))

    obsidian = project_dir / ".obsidian" / "graph.json"
    legend = project_dir / ".obsidian" / "COLOR-LEGEND.md"
    if obsidian.exists() and legend.exists():
        checks.append(DoctorCheck("obsidian graph config", PASS, ".obsidian graph config and color legend exist"))
    else:
        checks.append(DoctorCheck("obsidian graph config", WARN, "Obsidian graph config or color legend is missing", "Run /alpha-wiki:init with Obsidian enabled or /alpha-wiki:render."))
    return checks


def _check_lint(project_dir: Path, wiki_dir: Path) -> list[DoctorCheck]:
    if not wiki_dir.exists():
        return []
    config = _load_lint_config(project_dir / ".alpha-wiki" / "config.yaml")
    findings = run_all_checks(wiki_dir, *config)
    errors = [finding for finding in findings if finding.severity == LintSeverity.ERROR]
    warnings = [finding for finding in findings if finding.severity == LintSeverity.WARNING]
    if errors:
        return [DoctorCheck("lint", FAIL, f"{len(errors)} error(s), {len(warnings)} warning(s)", "Run /alpha-wiki:lint --fix, then handle remaining errors.")]
    if warnings:
        return [DoctorCheck("lint", WARN, f"0 error(s), {len(warnings)} warning(s)", "Run /alpha-wiki:lint --suggest for repair guidance.")]
    return [DoctorCheck("lint", PASS, "0 error(s), 0 warning(s)")]


def _load_lint_config(config_path: Path) -> tuple[dict, dict, list]:
    if not config_path.exists():
        return {}, {}, []
    data = yaml.safe_load(config_path.read_text()) or {}
    schema = {t["name"]: t.get("frontmatter_required", []) for t in data.get("entity_types", [])}
    dir_to_type = {t["dir"].rstrip("/"): t["name"] for t in data.get("entity_types", [])}
    return schema, dir_to_type, data.get("dependency_rules", [])


def _check_platform(project_dir: Path, platform: str) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    selected = {"claude", "codex"} if platform in {"auto", "both"} else {platform}
    if "claude" in selected:
        checks.extend(_check_claude(project_dir))
    if "codex" in selected:
        checks.extend(_check_codex())
    return checks


def _check_claude(project_dir: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    hooks = project_dir / ".claude" / "hooks"
    if hooks.exists():
        hook_count = len(list(hooks.glob("*.sh")))
        checks.append(DoctorCheck("claude hooks", PASS, f"{hook_count} hook script(s) installed"))
    else:
        checks.append(DoctorCheck("claude hooks", WARN, ".claude/hooks is missing", "Install hooks via /alpha-wiki:init or rerun init with hooks enabled."))

    settings = project_dir / ".claude" / "settings.local.json"
    if settings.exists():
        checks.append(DoctorCheck("claude settings", PASS, ".claude/settings.local.json exists"))
    else:
        checks.append(DoctorCheck("claude settings", WARN, ".claude/settings.local.json is missing", "Session hooks need settings.local.json to route wiki writes."))

    workflows = project_dir / ".github" / "workflows"
    expected = {"wiki-lint.yml", "wiki-review.yml", "wiki-rollup.yml"}
    present = {path.name for path in workflows.glob("*.yml")} if workflows.exists() else set()
    missing = sorted(expected - present)
    if missing:
        checks.append(DoctorCheck("github workflows", WARN, f"missing generated workflow(s): {', '.join(missing)}", "Enable CI during init or copy assets/workflows."))
    else:
        checks.append(DoctorCheck("github workflows", PASS, "lint/review/rollup workflows exist"))
    return checks


def _check_codex() -> list[DoctorCheck]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    skills_dir = codex_home / "skills"
    expected = skills_dir / "alpha-wiki-init" / "SKILL.md"
    if expected.exists():
        return [DoctorCheck("codex skills", PASS, f"Alpha-Wiki Codex skills detected in {skills_dir}")]
    return [DoctorCheck("codex skills", WARN, f"Alpha-Wiki Codex skills not detected in {skills_dir}", "Run python3 scripts/install_codex.py from the plugin repository.")]


def _display_path(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


@click.command()
@click.option("--project-dir", type=click.Path(path_type=Path, exists=True, file_okay=False), default=Path("."), show_default=True)
@click.option("--wiki-dir", type=click.Path(path_type=Path), help="Override wiki directory. Defaults to CLAUDE.md Wiki dir or wiki/.")
@click.option("--platform", type=click.Choice(["auto", "claude", "codex", "both"]), default="auto", show_default=True)
@click.option("--refresh", is_flag=True, help="Rebuild graph artifacts before checking them.")
@click.option("--strict", is_flag=True, help="Exit nonzero on warnings as well as failures.")
def cli(project_dir: Path, wiki_dir: Path | None, platform: str, refresh: bool, strict: bool) -> None:
    result = run_doctor(project_dir, wiki_dir=wiki_dir, platform=platform, refresh=refresh)
    click.echo(result.to_markdown())
    if result.failures:
        raise SystemExit(1)
    if strict and result.warnings:
        raise SystemExit(2)


if __name__ == "__main__":
    cli()
