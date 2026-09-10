"""Install or upgrade Alpha-Wiki for current Codex plugin and skill runtimes."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = ROOT / "skills"
DEFAULT_TARGET = Path.home() / ".agents" / "skills"
DEFAULT_PLUGIN_DIR = Path.home() / "plugins" / "alpha-wiki"
DEFAULT_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
DEFAULT_LEGACY_TARGET = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"
PLUGIN_PACKAGE_DIRS = ("assets", "references", "scripts", "skills", "tools")
PLUGIN_PACKAGE_FILES = ("CHANGELOG.md", "LICENSE", "README.md", "pyproject.toml")
PLUGIN_PACKAGE_DOCS = (
    "ADR-006-spawn-agent-boundary.md",
    "ADR-007-optional-agentops-control-layer.md",
    "codex-adapter.md",
    "examples/codex-parallel-audit-prompt.md",
    "final-release-hardening-plan.md",
    "project-audit.md",
)


@dataclass(frozen=True)
class CodexInstallResult:
    skills: list[Path]
    plugin_dir: Path | None
    marketplace_name: str | None
    activated: bool
    standalone_removed: list[Path]
    legacy_removed: list[Path]


def codex_skill_name(source_name: str) -> str:
    return f"alpha-wiki-{source_name}"


def _map_invocations(text: str, style: str) -> str:
    def replace(match: re.Match[str]) -> str:
        operation = match.group(1)
        if style == "plugin":
            return f"$alpha-wiki:{operation}"
        return f"$alpha-wiki-{operation}"

    return re.sub(r"/alpha-wiki:([a-z][a-z0-9-]*)", replace, text)


def transform_skill_for_codex(
    text: str,
    source_name: str,
    *,
    style: str = "standalone",
    runtime_root: Path | None = None,
) -> str:
    if not text.startswith("---\n"):
        raise ValueError(f"skill has no frontmatter: {source_name}")
    if style not in {"standalone", "plugin"}:
        raise ValueError(f"unknown Codex skill style: {style}")

    _, frontmatter, body = text.split("---", 2)
    invocation = f"$alpha-wiki:{source_name}" if style == "plugin" else f"${codex_skill_name(source_name)}"
    if style == "standalone":
        codex_name = codex_skill_name(source_name)
        frontmatter = re.sub(r"(?m)^name:\s*.*$", f"name: {codex_name}", frontmatter, count=1)
        frontmatter = re.sub(
            r'(?m)^description:\s*"?',
            f'description: "Codex adapter for Alpha-Wiki `{source_name}`. ',
            frontmatter,
            count=1,
        )
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"

    runtime_line = ""
    if runtime_root is not None:
        runtime_line = (
            f"\n- Installed Alpha-Wiki runtime: `{runtime_root}`. "
            "Use project-local `tools/` after init; before init, resolve bootstrap assets from this runtime.\n"
        )
    adapter_note = (
        "\n## Codex Adapter\n\n"
        f"- Invoke this workflow as `{invocation}`.\n"
        "- Prefer the installed `alpha-wiki` plugin namespace; standalone prefixed skills are an IDE fallback.\n"
        "- Read project `AGENTS.md` and `wiki/graph/context_brief.md` before substantial work.\n"
        "- Use project-local deterministic `python -m tools.*` commands when the wiki is initialized.\n"
        f"{runtime_line}"
    )
    return f"---{frontmatter}---{adapter_note}{_map_invocations(body.lstrip(), style)}"


def install_codex_skills(
    target: Path = DEFAULT_TARGET,
    dry_run: bool = False,
    runtime_root: Path | None = DEFAULT_PLUGIN_DIR,
) -> list[Path]:
    installed: list[Path] = []
    for skill_path in sorted(SOURCE_SKILLS.glob("*/SKILL.md")):
        source_name = skill_path.parent.name
        dest = target / codex_skill_name(source_name) / "SKILL.md"
        installed.append(dest)
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            transform_skill_for_codex(
                skill_path.read_text(),
                source_name,
                style="standalone",
                runtime_root=runtime_root,
            )
        )
    return installed


def install_codex_plugin(plugin_dir: Path, *, dry_run: bool = False) -> Path:
    if dry_run:
        return plugin_dir

    staging = plugin_dir.with_name(plugin_dir.name + ".installing")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(ROOT / ".codex-plugin", staging / ".codex-plugin")
    for directory in PLUGIN_PACKAGE_DIRS:
        shutil.copytree(
            ROOT / directory,
            staging / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
    for filename in PLUGIN_PACKAGE_FILES:
        shutil.copy2(ROOT / filename, staging / filename)
    (staging / "docs").mkdir()
    for filename in PLUGIN_PACKAGE_DOCS:
        destination = staging / "docs" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "docs" / filename, destination)

    manifest_path = staging / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    base_version = manifest["version"].split("+", 1)[0]
    cachebuster = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    manifest["version"] = f"{base_version}+codex.local-{cachebuster}"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    for skill_path in sorted((staging / "skills").glob("*/SKILL.md")):
        source_name = skill_path.parent.name
        skill_path.write_text(
            transform_skill_for_codex(
                skill_path.read_text(),
                source_name,
                style="plugin",
                runtime_root=plugin_dir,
            )
        )

    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    staging.replace(plugin_dir)
    return plugin_dir


def ensure_personal_marketplace(
    marketplace_path: Path,
    plugin_dir: Path,
    *,
    dry_run: bool = False,
) -> str:
    if marketplace_path.exists():
        data = json.loads(marketplace_path.read_text())
    else:
        data = {
            "name": "personal",
            "interface": {"displayName": "Personal Plugins"},
            "plugins": [],
        }

    marketplace_name = data.get("name") or "personal"
    parent = marketplace_path.parent
    marketplace_root = parent.parent.parent if parent.name == "plugins" and parent.parent.name == ".agents" else parent
    relative_plugin = os.path.relpath(plugin_dir, marketplace_root).replace(os.sep, "/")
    source_path = relative_plugin if relative_plugin.startswith(".") else f"./{relative_plugin}"
    entry = {
        "name": "alpha-wiki",
        "source": {"source": "local", "path": source_path},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }
    plugins = [item for item in data.get("plugins", []) if item.get("name") != "alpha-wiki"]
    plugins.append(entry)
    data["plugins"] = plugins

    if not dry_run:
        marketplace_path.parent.mkdir(parents=True, exist_ok=True)
        marketplace_path.write_text(json.dumps(data, indent=2) + "\n")
    return marketplace_name


def activate_codex_plugin(marketplace_name: str, *, upgrade: bool = False) -> None:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI is not on PATH; install it with npm install -g @openai/codex@latest")
    selector = f"alpha-wiki@{marketplace_name}"
    subprocess.run([codex, "plugin", "add", selector, "--json"], check=True)


def find_managed_codex_skills(target: Path) -> list[Path]:
    managed: list[Path] = []
    if not target.exists():
        return managed
    expected_names = {
        codex_skill_name(skill_path.parent.name)
        for skill_path in SOURCE_SKILLS.glob("*/SKILL.md")
    }
    for path in sorted(target.glob("alpha-wiki-*")):
        skill_path = path / "SKILL.md"
        if path.name not in expected_names or not skill_path.is_file():
            continue
        text = skill_path.read_text()
        if (
            f"name: {path.name}" in text
            and "Codex adapter for Alpha-Wiki" in text
        ):
            managed.append(path)
    return managed


def remove_managed_codex_skills(target: Path) -> list[Path]:
    removed: list[Path] = []
    for path in find_managed_codex_skills(target):
        shutil.rmtree(path)
        removed.append(path)
    return removed


def remove_or_plan_managed_codex_skills(target: Path, *, dry_run: bool) -> list[Path]:
    if dry_run:
        return find_managed_codex_skills(target)
    return remove_managed_codex_skills(target)


def remove_legacy_codex_skills(legacy_target: Path = DEFAULT_LEGACY_TARGET) -> list[Path]:
    return remove_managed_codex_skills(legacy_target)


def install_codex(
    *,
    skills_target: Path = DEFAULT_TARGET,
    plugin_dir: Path = DEFAULT_PLUGIN_DIR,
    marketplace_path: Path = DEFAULT_MARKETPLACE_PATH,
    install_standalone: bool = False,
    install_plugin: bool = True,
    activate: bool = True,
    upgrade: bool = False,
    remove_standalone: bool = False,
    remove_legacy: bool = False,
    legacy_target: Path = DEFAULT_LEGACY_TARGET,
    dry_run: bool = False,
) -> CodexInstallResult:
    if install_standalone and remove_standalone:
        raise ValueError("cannot install and remove standalone skills in the same run")
    if install_standalone and install_plugin:
        raise ValueError("standalone fallback and plugin mode cannot be installed together")
    skills = (
        install_codex_skills(skills_target, dry_run=dry_run, runtime_root=plugin_dir)
        if install_standalone
        else []
    )
    installed_plugin = install_codex_plugin(plugin_dir, dry_run=dry_run) if install_plugin else None
    marketplace_name = (
        ensure_personal_marketplace(marketplace_path, plugin_dir, dry_run=dry_run)
        if install_plugin
        else None
    )
    activated = False
    if install_plugin and activate and not dry_run:
        activate_codex_plugin(marketplace_name or "personal", upgrade=upgrade)
        activated = True
    standalone_removed = (
        remove_or_plan_managed_codex_skills(skills_target, dry_run=dry_run)
        if remove_standalone
        else []
    )
    legacy_removed = (
        remove_or_plan_managed_codex_skills(legacy_target, dry_run=dry_run)
        if remove_legacy
        else []
    )
    return CodexInstallResult(
        skills=skills,
        plugin_dir=installed_plugin,
        marketplace_name=marketplace_name,
        activated=activated,
        standalone_removed=standalone_removed,
        legacy_removed=legacy_removed,
    )


def cli() -> None:
    parser = argparse.ArgumentParser(description="Install or upgrade Alpha-Wiki for current Codex.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="Standalone Codex skills directory.")
    parser.add_argument("--plugin-dir", type=Path, default=DEFAULT_PLUGIN_DIR, help="Personal Alpha-Wiki plugin directory.")
    parser.add_argument("--marketplace-path", type=Path, default=DEFAULT_MARKETPLACE_PATH, help="Personal marketplace.json path.")
    standalone = parser.add_mutually_exclusive_group()
    standalone.add_argument(
        "--standalone",
        action="store_true",
        help="Install standalone IDE fallback skills instead of the Codex plugin.",
    )
    standalone.add_argument(
        "--remove-standalone",
        action="store_true",
        help="Remove only managed Alpha-Wiki standalone fallback skills.",
    )
    parser.add_argument("--no-plugin", action="store_true", help="Skip Codex plugin package installation.")
    parser.add_argument("--no-activate", action="store_true", help="Do not run codex plugin add.")
    parser.add_argument("--upgrade", action="store_true", help="Reinstall the plugin so Codex refreshes its cached package.")
    parser.add_argument("--remove-legacy", action="store_true", help="Remove managed Alpha-Wiki skills from legacy ~/.codex/skills.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned installation without writing.")
    args = parser.parse_args()

    result = install_codex(
        skills_target=args.target.expanduser(),
        plugin_dir=args.plugin_dir.expanduser(),
        marketplace_path=args.marketplace_path.expanduser(),
        install_standalone=args.standalone,
        install_plugin=not args.no_plugin and not args.standalone,
        activate=not args.no_activate,
        upgrade=args.upgrade,
        remove_standalone=args.remove_standalone,
        remove_legacy=args.remove_legacy,
        dry_run=args.dry_run,
    )
    action = "would install" if args.dry_run else "installed"
    for path in result.skills:
        print(f"{action}: {path}")
    if result.plugin_dir:
        print(f"{action} Codex plugin: {result.plugin_dir}")
        print(f"marketplace: {result.marketplace_name}")
    if result.activated:
        print("activated Codex plugin: alpha-wiki")
    for path in result.standalone_removed:
        verb = "would remove" if args.dry_run else "removed"
        print(f"{verb} standalone skill: {path}")
    for path in result.legacy_removed:
        verb = "would remove" if args.dry_run else "removed"
        print(f"{verb} legacy skill: {path}")
    print(f"{action} {len(result.skills)} standalone Alpha-Wiki Codex skill(s)")


if __name__ == "__main__":
    cli()
