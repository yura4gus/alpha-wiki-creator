"""Render pipeline: InterviewConfig → target file tree."""
from __future__ import annotations
import shutil
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


def bootstrap(target: Path, config: InterviewConfig, upgrade: bool = False) -> None:
    target.mkdir(parents=True, exist_ok=True)
    merged = _resolve_merged_config(config)
    ctx = _render_context(config, merged)

    _render_top_level_files(target, ctx, upgrade=upgrade)
    _create_wiki_dirs(target, config, merged)
    _initialize_wiki_files(target, ctx, upgrade=upgrade)
    _copy_assets(target, config)
    _copy_tools(target)
    _initialize_graph(target, config)
    _write_merged_config(target, merged)


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
        "skills": ["/wiki-init", "/wiki-ingest", "/wiki-query", "/wiki-lint",
                   "/wiki-evolve", "/wiki-spawn-agent", "/wiki-render"],
        "schema_evolve_mode": config.schema_evolve_mode,
        "ci": config.ci,
    }


def _render_top_level_files(target: Path, ctx: dict, upgrade: bool) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    files = [
        ("claude-md.j2", "CLAUDE.md"),
        ("readme.j2", "README.md"),
        ("pyproject.j2", "pyproject.toml"),
        ("gitignore.j2", ".gitignore"),
    ]
    for tmpl_name, out_name in files:
        out_path = target / out_name
        if out_path.exists() and upgrade and out_name in ("README.md",):
            continue  # Don't overwrite user-edited README
        out_path.write_text(env.get_template(tmpl_name).render(**ctx))
    shutil.copy(ASSETS / "env.example", target / ".env.example")


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
        log_path.write_text(log_path.read_text() + f"\n## [{ctx['date']}] upgrade | re-bootstrapped via /wiki-init\n")


def _copy_assets(target: Path, config: InterviewConfig) -> None:
    if config.obsidian:
        obsidian = target / ".obsidian"
        obsidian.mkdir(exist_ok=True)
        for f in (ASSETS / "obsidian").iterdir():
            shutil.copy(f, obsidian / f.name)
    if config.hooks in ("all", "session", "git"):
        hooks_dir = target / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "hooks").iterdir():
            dest = hooks_dir / f.name
            shutil.copy(f, dest)
            dest.chmod(0o755)
        env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
        (target / ".claude" / "settings.local.json").write_text(
            env.get_template("settings-local.j2").render(wiki_dir=config.wiki_dir))
    if config.ci:
        wf_dir = target / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / "workflows").iterdir():
            shutil.copy(f, wf_dir / f.name)
    (target / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    (target / ".claude" / "skills").mkdir(parents=True, exist_ok=True)


def _copy_tools(target: Path) -> None:
    tools_dst = target / "tools"
    tools_dst.mkdir(exist_ok=True)
    for f in TOOLS.iterdir():
        if f.is_file() and f.suffix == ".py":
            shutil.copy(f, tools_dst / f.name)


def _initialize_graph(target: Path, config: InterviewConfig) -> None:
    g = target / config.wiki_dir / "graph"
    (g / "edges.jsonl").write_text("")
    (g / "context_brief.md").write_text("# Context brief\n\n_(empty — will populate after first ingest)_\n")
    (g / "open_questions.md").write_text("# Open questions\n\n_(none yet)_\n")


def _write_merged_config(target: Path, merged: dict) -> None:
    cfg_dir = target / ".wiki-creator"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.yaml").write_text(yaml.safe_dump(merged, sort_keys=False))
