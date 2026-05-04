"""Render pipeline: InterviewConfig → target file tree."""
from __future__ import annotations
import shutil
from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader
from scripts.interview import InterviewConfig

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PLUGIN_ROOT / "assets"
PRESETS = PLUGIN_ROOT / "references" / "presets"
OVERLAYS = PLUGIN_ROOT / "references" / "overlays"
TOOLS = PLUGIN_ROOT / "tools"

PROTECTED_TOP_LEVEL_FILES = {
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
    ".gitignore",
    ".env.example",
}
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


@dataclass(frozen=True)
class BootstrapConflict:
    path: str
    reason: str


@dataclass
class BootstrapReport:
    dry_run: bool = False
    planned: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    skipped: list[BootstrapConflict] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.skipped)

    def to_markdown(self) -> str:
        lines = [
            "# Alpha-Wiki bootstrap report",
            "",
            f"- dry_run: {str(self.dry_run).lower()}",
            f"- planned writes: {len(self.planned)}",
            f"- completed writes: {len(self.written)}",
            f"- protected skips: {len(self.skipped)}",
            "",
        ]
        if self.skipped:
            lines.extend(["## Protected skips", ""])
            for conflict in self.skipped:
                lines.append(f"- `{conflict.path}`: {conflict.reason}")
            lines.append("")
        if self.planned:
            lines.extend(["## Planned writes", ""])
            for path in self.planned:
                lines.append(f"- `{path}`")
            lines.append("")
        if self.written:
            lines.extend(["## Completed writes", ""])
            for path in self.written:
                lines.append(f"- `{path}`")
            lines.append("")
        return "\n".join(lines)


def bootstrap(
    target: Path,
    config: InterviewConfig,
    upgrade: bool = False,
    dry_run: bool = False,
    safe_existing: bool = True,
) -> BootstrapReport:
    merged = _resolve_merged_config(config)
    ctx = _render_context(config, merged)
    report = BootstrapReport(dry_run=dry_run)

    if dry_run:
        _render_top_level_files(target, ctx, upgrade=upgrade, report=report, dry_run=True, safe_existing=safe_existing)
        _plan_path(report, target / config.wiki_dir)
        _plan_path(report, target / "raw")
        _plan_path(report, target / ".alpha-wiki" / "config.yaml")
        return report

    target.mkdir(parents=True, exist_ok=True)
    _render_top_level_files(target, ctx, upgrade=upgrade, report=report, dry_run=False, safe_existing=safe_existing)
    _create_wiki_dirs(target, config, merged)
    _initialize_wiki_files(target, ctx, upgrade=upgrade)
    _copy_assets(target, config)
    _copy_tools(target)
    _initialize_graph(target, config, upgrade=upgrade)
    _write_merged_config(target, merged)
    _write_bootstrap_report(target, report)
    return report


def _resolve_merged_config(config: InterviewConfig) -> dict:
    preset = yaml.safe_load((PRESETS / f"{config.preset}.yaml").read_text()) if config.preset != "custom" \
             else {"name": "custom", "entity_types": [
                 {"name": t.name, "dir": t.dir,
                  "frontmatter_required": t.frontmatter_required,
                  "frontmatter_optional": t.frontmatter_optional,
                  "sections_required": t.sections_required} for t in (config.custom_entity_types or [])],
              "cross_ref_rules": []}
    if config.overlay == "none":
        return preset
    overlay_names = config.overlay.split("+")
    if "clean" in overlay_names and "hexagonal" in overlay_names:
        raise ValueError("clean+hexagonal not combinable")
    merged = dict(preset)
    merged["overlay_dirs"] = []
    merged["dependency_rules"] = []
    for ov_name in overlay_names:
        ov = yaml.safe_load((OVERLAYS / f"{ov_name}.yaml").read_text())
        merged["overlay_dirs"].extend(ov.get("top_level_dirs", []))
        merged["dependency_rules"].extend(ov.get("dependency_rules", []))
        merged["cross_ref_rules"].extend(ov.get("extra_cross_ref_rules", []))
    return merged


def _render_context(config: InterviewConfig, merged: dict) -> dict:
    return {
        "project_name": config.project_name,
        "project_description": config.project_description,
        "wiki_dir": config.wiki_dir,
        "preset": config.preset,
        "overlay": config.overlay,
        "date": _date.today().isoformat(),
        "entity_types": merged.get("entity_types", []),
        "cross_ref_rules": merged.get("cross_ref_rules", []),
        "skills": ["/alpha-wiki:init", "/alpha-wiki:doctor", "/alpha-wiki:ingest", "/alpha-wiki:query", "/alpha-wiki:lint",
                   "/alpha-wiki:evolve", "/alpha-wiki:spawn-agent", "/alpha-wiki:render", "/alpha-wiki:status",
                   "/alpha-wiki:review", "/alpha-wiki:rollup"],
        "schema_evolve_mode": config.schema_evolve_mode,
        "ci": config.ci,
    }


def _render_top_level_files(
    target: Path,
    ctx: dict,
    upgrade: bool,
    report: BootstrapReport,
    dry_run: bool,
    safe_existing: bool,
) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    files = [
        ("claude-md.j2", "CLAUDE.md"),
        ("readme.j2", "README.md"),
        ("pyproject.j2", "pyproject.toml"),
        ("gitignore.j2", ".gitignore"),
    ]
    for tmpl_name, out_name in files:
        out_path = target / out_name
        content = env.get_template(tmpl_name).render(**ctx)
        _write_protected_text(out_path, content, report, dry_run, safe_existing, upgrade)
    _copy_protected_file(ASSETS / "env.example", target / ".env.example", report, dry_run, safe_existing, upgrade)


def _create_wiki_dirs(target: Path, config: InterviewConfig, merged: dict) -> None:
    wiki = target / config.wiki_dir
    wiki.mkdir(exist_ok=True)
    if merged.get("overlay_dirs"):
        for d in merged["overlay_dirs"]:
            (wiki / d).mkdir(parents=True, exist_ok=True)
    else:
        for t in merged.get("entity_types", []):
            (wiki / t["dir"]).mkdir(parents=True, exist_ok=True)
    (wiki / "outputs").mkdir(exist_ok=True)
    (wiki / "graph").mkdir(exist_ok=True)
    # raw/
    (target / "raw" / "docs").mkdir(parents=True, exist_ok=True)
    (target / "raw" / "transcripts").mkdir(exist_ok=True)
    (target / "raw" / "chats").mkdir(exist_ok=True)
    (target / "raw" / "web").mkdir(exist_ok=True)


def _initialize_wiki_files(target: Path, ctx: dict, upgrade: bool) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    wiki = target / ctx["wiki_dir"]
    if not (wiki / "index.md").exists() or not upgrade:
        (wiki / "index.md").write_text(env.get_template("index-md.j2").render(**ctx))
    log_path = wiki / "log.md"
    if not log_path.exists():
        log_path.write_text(env.get_template("log-md.j2").render(**ctx))
    elif upgrade:
        log_path.write_text(log_path.read_text() + f"\n## [{ctx['date']}] upgrade | re-bootstrapped via /alpha-wiki:init\n")


def _copy_assets(target: Path, config: InterviewConfig) -> None:
    if config.obsidian:
        obsidian = target / ".obsidian"
        obsidian.mkdir(exist_ok=True)
        for f in (ASSETS / "obsidian").iterdir():
            shutil.copy(f, obsidian / f.name)
    hook_files = _hook_files_for_mode(config.hooks)
    if hook_files:
        hooks_dir = target / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "hooks").iterdir():
            if f.name not in hook_files:
                continue
            dest = hooks_dir / f.name
            dest.write_text(_render_runtime_asset(f.read_text(), config))
            dest.chmod(0o755)
    if _uses_session_hooks(config.hooks):
        env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
        (target / ".claude" / "settings.local.json").write_text(
            env.get_template("settings-local.j2").render(wiki_dir=config.wiki_dir))
    if config.ci:
        wf_dir = target / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "workflows").iterdir():
            (wf_dir / f.name).write_text(_render_runtime_asset(f.read_text(), config))
    (target / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    (target / ".claude" / "skills").mkdir(parents=True, exist_ok=True)


def _copy_tools(target: Path) -> None:
    tools_dst = target / "tools"
    tools_dst.mkdir(exist_ok=True)
    for f in TOOLS.iterdir():
        if f.is_file() and f.suffix == ".py":
            shutil.copy(f, tools_dst / f.name)


def _hook_files_for_mode(mode: str) -> set[str]:
    if mode == "all":
        return SESSION_HOOKS | GIT_HOOKS
    if mode == "session":
        return set(SESSION_HOOKS)
    if mode == "git":
        return set(GIT_HOOKS)
    return set()


def _uses_session_hooks(mode: str) -> bool:
    return mode in ("all", "session")


def _render_runtime_asset(text: str, config: InterviewConfig) -> str:
    return (
        text
        .replace('WIKI_DIR="${WIKI_DIR:-wiki}"', f'WIKI_DIR="${{WIKI_DIR:-{config.wiki_dir}}}"')
        .replace("--wiki-dir wiki", f"--wiki-dir {config.wiki_dir}")
        .replace("git add wiki/rollups/", f"git add {config.wiki_dir}/rollups/")
    )


def _initialize_graph(target: Path, config: InterviewConfig, upgrade: bool) -> None:
    g = target / config.wiki_dir / "graph"
    _write_graph_seed(g / "edges.jsonl", "", upgrade)
    _write_graph_seed(g / "context_brief.md", "# Context brief\n\n_(empty — will populate after first ingest)_\n", upgrade)
    _write_graph_seed(g / "open_questions.md", "# Open questions\n\n_(none yet)_\n", upgrade)


def _write_merged_config(target: Path, merged: dict) -> None:
    cfg_dir = target / ".alpha-wiki"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.yaml").write_text(yaml.safe_dump(merged, sort_keys=False))


def _write_protected_text(
    path: Path,
    content: str,
    report: BootstrapReport,
    dry_run: bool,
    safe_existing: bool,
    upgrade: bool,
) -> None:
    _plan_path(report, path)
    if path.exists():
        if path.read_text() == content:
            return
        if _should_protect_existing(path, safe_existing, upgrade):
            report.skipped.append(BootstrapConflict(str(path), "existing protected file was preserved"))
            return
    if dry_run:
        return
    path.write_text(content)
    report.written.append(str(path))


def _copy_protected_file(
    src: Path,
    dest: Path,
    report: BootstrapReport,
    dry_run: bool,
    safe_existing: bool,
    upgrade: bool,
) -> None:
    _plan_path(report, dest)
    content = src.read_text()
    if dest.exists():
        if dest.read_text() == content:
            return
        if _should_protect_existing(dest, safe_existing, upgrade):
            report.skipped.append(BootstrapConflict(str(dest), "existing protected file was preserved"))
            return
    if dry_run:
        return
    shutil.copy(src, dest)
    report.written.append(str(dest))


def _should_protect_existing(path: Path, safe_existing: bool, upgrade: bool) -> bool:
    if path.name not in PROTECTED_TOP_LEVEL_FILES:
        return False
    return safe_existing or upgrade


def _write_graph_seed(path: Path, content: str, upgrade: bool) -> None:
    if upgrade and path.exists():
        return
    path.write_text(content)


def _write_bootstrap_report(target: Path, report: BootstrapReport) -> None:
    if not report.has_conflicts:
        return
    cfg_dir = target / ".alpha-wiki"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "bootstrap-report.md").write_text(report.to_markdown())


def _plan_path(report: BootstrapReport, path: Path) -> None:
    value = str(path)
    if value not in report.planned:
        report.planned.append(value)
