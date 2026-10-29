"""Render pipeline: InterviewConfig → target file tree."""
from __future__ import annotations
import json
import hashlib
import shlex
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
    "AGENTS.md",
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
    from tools.document_maintenance import _safe

    target = target.resolve()
    _safe(target, config.wiki_dir)
    config_path = target / ".alpha-wiki/config.yaml"
    if config_path.is_file():
        merged = yaml.safe_load(config_path.read_text())
        if not isinstance(merged, dict) or not isinstance(merged.get("entity_types"), list):
            raise ValueError("Existing .alpha-wiki/config.yaml must contain an entity_types list; preserved.")
    else:
        merged = {**_resolve_merged_config(config), "wiki_dir": config.wiki_dir,
                  "schema_evolve_mode": config.schema_evolve_mode}
    for entity in merged["entity_types"]:
        if not isinstance(entity, dict) or not isinstance(entity.get("dir"), str):
            raise ValueError("Each entity type must define a directory")
        _safe(target / config.wiki_dir, entity["dir"])
    overlay_dirs = merged.get("overlay_dirs", [])
    if not isinstance(overlay_dirs, list) or any(not isinstance(path, str) for path in overlay_dirs):
        raise ValueError("overlay_dirs must be a list of directory paths")
    for directory in overlay_dirs:
        _safe(target / config.wiki_dir, directory)
    ctx = _render_context(config, merged)
    report = BootstrapReport(dry_run=dry_run)

    if dry_run:
        _render_top_level_files(target, ctx, upgrade=upgrade, report=report, dry_run=True, safe_existing=safe_existing)
        _copy_assets(target, config, report, dry_run=True)
        _plan_path(report, target / config.wiki_dir)
        _plan_path(report, target / "raw")
        _plan_path(report, target / ".alpha-wiki" / "config.yaml")
        _plan_path(report, target / ".alpha-wiki" / "run.py")
        _plan_path(report, target / ".alpha-wiki" / "runtime" / "pyproject.toml")
        if _uses_session_hooks(config.hooks):
            _plan_path(report, target / ".codex" / "hooks.json")
            _plan_path(report, target / ".codex" / "hooks" / "alpha_wiki_hook.py")
        return report

    target.mkdir(parents=True, exist_ok=True)
    _render_top_level_files(target, ctx, upgrade=upgrade, report=report, dry_run=False, safe_existing=safe_existing)
    _create_wiki_dirs(target, config, merged)
    _initialize_wiki_files(target, ctx, upgrade=upgrade)
    _copy_assets(target, config, report)
    _copy_tools(target)
    _copy_runtime(target)
    _initialize_graph(target, config, upgrade=upgrade or safe_existing)
    _write_new_text(target, config_path, yaml.safe_dump(merged, sort_keys=False), report)
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
        return _retarget_document_governance(preset, config.wiki_dir)
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
    return _retarget_document_governance(merged, config.wiki_dir)


def _retarget_document_governance(merged: dict, wiki_dir: str) -> dict:
    governance = merged.get("document_governance")
    if not isinstance(governance, dict) or wiki_dir == "wiki":
        return merged

    def retarget(value: str) -> str:
        if value == "wiki":
            return wiki_dir
        if value.startswith("wiki/"):
            return f"{wiki_dir}/{value.removeprefix('wiki/')}"
        return value

    updated = dict(merged)
    updated_governance = dict(governance)
    updated_governance["global_log"] = retarget(governance.get("global_log", "wiki/log.md"))
    for key in ("canonical_files", "canonical_roots", "excluded_files", "excluded_roots"):
        updated_governance[key] = [retarget(value) for value in governance.get(key, [])]
    updated["document_governance"] = updated_governance
    return updated


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
                   "/alpha-wiki:review", "/alpha-wiki:rollup", "/alpha-wiki:audit-project",
                   "/alpha-wiki:orchestrate", "/alpha-wiki:backlog", "/alpha-wiki:handoff",
                   "/alpha-wiki:release-check"],
        "codex_skills": ["$alpha-wiki:init", "$alpha-wiki:doctor", "$alpha-wiki:ingest", "$alpha-wiki:query",
                         "$alpha-wiki:lint", "$alpha-wiki:evolve", "$alpha-wiki:status",
                         "$alpha-wiki:spawn-agent", "$alpha-wiki:render", "$alpha-wiki:review",
                         "$alpha-wiki:rollup", "$alpha-wiki:audit-project", "$alpha-wiki:orchestrate",
                         "$alpha-wiki:backlog", "$alpha-wiki:handoff", "$alpha-wiki:release-check"],
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
        ("agents-md.j2", "AGENTS.md"),
        ("readme.j2", "README.md"),
        ("gitignore.j2", ".gitignore"),
    ]
    for tmpl_name, out_name in files:
        out_path = target / out_name
        content = env.get_template(tmpl_name).render(**ctx)
        _write_protected_text(out_path, content, report, dry_run, safe_existing, upgrade)
    _copy_protected_file(ASSETS / "env.example", target / ".env.example", report, dry_run, safe_existing, upgrade)


def _create_wiki_dirs(target: Path, config: InterviewConfig, merged: dict) -> None:
    wiki = target / config.wiki_dir
    wiki.mkdir(parents=True, exist_ok=True)
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
    if not (wiki / "index.md").exists():
        (wiki / "index.md").write_text(env.get_template("index-md.j2").render(**ctx))
    log_path = wiki / "log.md"
    if not log_path.exists():
        log_path.write_text(env.get_template("log-md.j2").render(**ctx))


def _copy_assets(target: Path, config: InterviewConfig, report: BootstrapReport, *, dry_run: bool = False) -> None:
    env = Environment(loader=FileSystemLoader(str(ASSETS)), keep_trailing_newline=True)
    _write_new_text(target, target / ".claude/CLAUDE.md",
                    env.get_template("claude-md.j2").render(), report, dry_run=dry_run)
    if config.obsidian:
        for source in (ASSETS / "obsidian").iterdir():
            _write_new_text(target, target / config.wiki_dir / ".obsidian" / source.name,
                            source.read_text(), report, dry_run=dry_run)
    for name in sorted(_hook_files_for_mode(config.hooks)):
        source = ASSETS / "hooks" / name
        _write_new_text(target, target / ".claude/hooks" / name,
                        _render_runtime_asset(source.read_text(), config), report,
                        dry_run=dry_run, executable=True)
    if _uses_session_hooks(config.hooks):
        for template, destination in (
            ("settings-local.j2", ".claude/settings.local.json"),
            ("codex-hooks/hooks.json.j2", ".codex/hooks.json"),
        ):
            _write_new_text(target, target / destination,
                            env.get_template(template).render(wiki_dir=config.wiki_dir),
                            report, dry_run=dry_run)
        _write_new_text(target, target / ".codex/hooks/alpha_wiki_hook.py",
                        (ASSETS / "codex-hooks/alpha_wiki_hook.py").read_text(),
                        report, dry_run=dry_run, executable=True)
    if config.ci:
        for source in (ASSETS / "workflows").iterdir():
            _write_new_text(target, target / ".github/workflows" / source.name,
                            _render_runtime_asset(source.read_text(), config),
                            report, dry_run=dry_run)


def _write_new_text(target: Path, path: Path, content: str, report: BootstrapReport,
                    *, dry_run: bool = False, executable: bool = False) -> None:
    from tools.document_maintenance import _safe

    try:
        _safe(target, path)
    except ValueError as exc:
        report.skipped.append(BootstrapConflict(str(path), str(exc)))
        return
    if path.exists():
        if not path.is_file() or path.read_text() != content:
            report.skipped.append(BootstrapConflict(str(path), "existing user file was preserved; review/merge explicitly"))
        return
    _plan_path(report, path)
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x") as stream:
            stream.write(content)
    except FileExistsError:
        report.skipped.append(BootstrapConflict(str(path), "file appeared during setup; preserved"))
        return
    if executable:
        path.chmod(0o755)
    report.written.append(str(path))


def _copy_tools(target: Path) -> None:
    tools_dst = target / "tools"
    tools_dst.mkdir(exist_ok=True)
    for f in TOOLS.iterdir():
        if f.is_file() and f.suffix == ".py":
            dest = tools_dst / f.name
            if f.resolve() == dest.resolve():
                continue
            shutil.copy(f, dest)


def _copy_runtime(target: Path) -> None:
    runtime = target / ".alpha-wiki" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    for source, destination in (
        (ASSETS / "runtime" / "run.py", runtime.parent / "run.py"),
        (ASSETS / "runtime" / "pyproject.toml", runtime / "pyproject.toml"),
    ):
        if source.resolve() != destination.resolve():
            shutil.copy(source, destination)
    (runtime / ".gitignore").write_text(".venv/\nuv.lock\n")


def upgrade_runtime_assets(target: Path, wiki_dir: str | None = None, dry_run: bool = False,
                           refresh_hooks: bool = False) -> BootstrapReport:
    """Update managed runtime; recover missing routed hooks without replacing hooks."""
    from tools.doctor import _resolve_wiki_dir

    target = target.resolve()
    if not (target / ".alpha-wiki/config.yaml").is_file() or not (target / "tools").is_dir():
        raise ValueError("Runtime-only upgrade requires an initialized Alpha-Wiki project; run init first.")
    wiki = _resolve_wiki_dir(target, Path(wiki_dir) if wiki_dir is not None else None)
    relative_wiki = str(wiki.relative_to(target))
    config = InterviewConfig(
        project_name=target.name, project_description="", wiki_dir=relative_wiki,
        preset="software-project", overlay="none", custom_entity_types=None,
        i18n_languages=["en"], hooks="none", ci=False, schema_evolve_mode="gated",
    )
    report = BootstrapReport(dry_run=dry_run)
    copies = [(source, target / "tools" / source.name) for source in TOOLS.glob("*.py")]
    copies.extend([
        (ASSETS / "runtime/run.py", target / ".alpha-wiki/run.py"),
        (ASSETS / "runtime/pyproject.toml", target / ".alpha-wiki/runtime/pyproject.toml"),
    ])
    hooks = _missing_configured_hooks(target, report, refresh_hooks=refresh_hooks)
    previous_hooks = {destination: destination.read_bytes() for _, destination in hooks
                      if destination.is_file()}
    writes = [(destination, source.read_bytes()) for source, destination in copies]
    writes.append((target / ".alpha-wiki/runtime/.gitignore", b".venv/\nuv.lock\n"))
    writes = [(path, content) for path, content in writes
              if not path.is_file() or path.read_bytes() != content]
    writes.extend((destination, _render_runtime_asset(source.read_text(), config).encode())
                  for source, destination in hooks)
    report.planned = [str(path) for path, _ in writes]
    if dry_run:
        return report
    hook_paths = {destination for _, destination in hooks}
    for destination, content in writes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination in hook_paths:
            if destination in previous_hooks:
                if destination.is_symlink() or destination.read_bytes() != previous_hooks[destination]:
                    report.skipped.append(BootstrapConflict(str(destination), "hook changed after planning; preserved"))
                    continue
                destination.write_bytes(content)
                report.written.append(str(destination))
                continue
            # Exclusive creation preserves a user file created after planning too.
            try:
                with destination.open("xb") as stream:
                    stream.write(content)
            except FileExistsError:
                report.skipped.append(BootstrapConflict(str(destination), "hook path appeared; preserved"))
                continue
            destination.chmod(0o755)
        else:
            destination.write_bytes(content)
        report.written.append(str(destination))
    return report


def _missing_configured_hooks(target: Path, report: BootstrapReport,
                              *, refresh_hooks: bool = False) -> list[tuple[Path, Path]]:
    """Read project routing as data, never execute or expand a configured command."""
    configured: set[Path] = set()
    for relative in (".claude/settings.json", ".claude/settings.local.json", ".codex/hooks.json"):
        routing = target / relative
        if not routing.is_file():
            continue
        try:
            data = json.loads(routing.read_text())
            groups = data.get("hooks", {})
            if not isinstance(groups, dict):
                raise ValueError("hooks must be an object")
            for entries in groups.values():
                for entry in entries:
                    for hook in entry.get("hooks", []):
                        if hook.get("type") == "command" and isinstance(hook.get("command"), str):
                            path = _configured_hook_path(target, relative, hook["command"])
                            if path is not None:
                                configured.add(path)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"Invalid hook routing {routing}: {exc}") from exc

    missing = []
    for path in sorted(configured):
        parents = path.relative_to(target).parents
        if any((target / parent).is_symlink() or
               ((target / parent).exists() and not (target / parent).is_dir()) for parent in parents):
            report.skipped.append(BootstrapConflict(str(path), "hook parent is not a real directory; preserved"))
        elif path.is_symlink() or (path.exists() and not path.is_file()):
            report.skipped.append(BootstrapConflict(str(path), "occupied hook path; preserved"))
        elif not path.exists():
            source = (ASSETS / "hooks" / path.name if path.suffix == ".sh"
                      else ASSETS / "codex-hooks/alpha_wiki_hook.py")
            missing.append((source, path))
        elif refresh_hooks and path.name == "alpha_wiki_hook.py":
            source = ASSETS / "codex-hooks/alpha_wiki_hook.py"
            if path.read_bytes() == source.read_bytes():
                continue
            known = json.loads((ASSETS / "codex-hooks/legacy-sha256.json").read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest() in known:
                missing.append((source, path))
            else:
                report.skipped.append(BootstrapConflict(str(path), "custom or unknown Codex hook; review/merge explicitly"))
    return missing


def _configured_hook_path(target: Path, routing: str, command: str) -> Path | None:
    try:
        parts = shlex.split(command, comments=True)
    except ValueError:
        return None
    if not parts:
        return None
    claude = routing.startswith(".claude/")
    launchers = {"bash", "sh"} if claude else {"python", "python3"}
    script = parts[1] if Path(parts[0]).name in launchers and len(parts) > 1 else parts[0]
    relatives = ([f".claude/hooks/{name}" for name in sorted(SESSION_HOOKS | GIT_HOOKS)]
                 if claude else [".codex/hooks/alpha_wiki_hook.py"])
    for relative in relatives:
        aliases = {relative, f"./{relative}", str(target / relative)}
        if claude:
            aliases.update({f"$CLAUDE_PROJECT_DIR/{relative}", f"${{CLAUDE_PROJECT_DIR}}/{relative}"})
        else:
            aliases.add(f"$(git rev-parse --show-toplevel)/{relative}")
        if script in aliases:
            return target / relative
    return None


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
