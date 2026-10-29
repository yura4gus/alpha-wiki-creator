"""Install Alpha-Wiki skills and commands for OpenCode v2 without editing config."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex


ROOT = Path(__file__).resolve().parents[1]
MANAGED_BY = "alpha-wiki-opencode-v1"
PACKAGE_DIRS = ("assets", "references", "scripts", "skills", "tools", "docs")
PACKAGE_FILES = ("pyproject.toml", "uv.lock", "README.md", "CHANGELOG.md", "LICENSE")


def default_config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "opencode"


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def transform_skill(text: str, operation: str, runtime: Path) -> str:
    if not text.startswith("---\n"):
        raise ValueError(f"skill has no frontmatter: {operation}")
    _, frontmatter, body = text.split("---", 2)
    skill_id = f"alpha-wiki-{operation}"
    frontmatter = re.sub(r"(?m)^name:\s*.*$", f"name: {skill_id}", frontmatter, count=1)
    body = re.sub(r"(?ms)^## Codex Native Delegation\n.*?(?=^## |\Z)", "", body)
    body = re.sub(r"(?:/|\$)alpha-wiki:([a-z][a-z0-9-]*)", r"/alpha-wiki/\1", body)
    body = body.replace("--platform both", "--platform opencode")
    if operation == "spawn-agent":
        frontmatter = frontmatter.replace("native Codex subagents", "native OpenCode subagents")
        body = body.replace("`.codex/agents/<name>.toml`; Claude Code writes",
                            "`.codex/agents/<name>.toml`; OpenCode writes `.opencode/agents/<name>.md` with `mode: subagent`; Claude Code writes")
    note = (
        "\n## OpenCode v2 Adapter\n\n"
        f"- Skill ID: `{skill_id}`. Command: `/alpha-wiki/{operation}`.\n"
        "- Continue the user's deliverable; loading a skill does not authorize parallel audits.\n"
        "- Read project `AGENTS.md`, `.alpha-wiki/config.yaml` and the configured wiki brief. "
        "OpenCode v2 does not load CLAUDE.md as a fallback. Preserve user instructions.\n"
        "- After init use `python3 .alpha-wiki/run.py -m tools.<module>` from the target project. "
        "Never add Alpha-Wiki dependencies to its product environment.\n"
        f"- Installed runtime and shared reference base: `{runtime}`. Resolve Alpha-Wiki "
        "`references/`, `assets/`, and packaged documentation there; project source paths stay project-relative.\n"
        f"- Read `{runtime / 'references/opencode-adapter.md'}` for bootstrap and platform-specific behavior. "
        "Codex TOML, /hooks trust and Claude hook/profile instructions below apply only on those platforms. "
        "Do not install them as OpenCode automation.\n"
    )
    return f"---{frontmatter.rstrip()}\n---\n{note}\n{body.lstrip()}"


def _desired_files(config: Path) -> dict[str, bytes]:
    runtime = config / "alpha-wiki"
    desired: dict[str, bytes] = {}
    for directory in PACKAGE_DIRS:
        for source in sorted((ROOT / directory).rglob("*")):
            relative = source.relative_to(ROOT)
            if not source.is_file() or source.is_symlink():
                continue
            if any(part in {"__pycache__", ".venv", ".git"} for part in relative.parts):
                continue
            if source.suffix in {".pyc", ".zip"} or source.name == ".DS_Store":
                continue
            if directory == "docs" and source.suffix != ".md":
                continue
            desired[(Path("alpha-wiki") / relative).as_posix()] = source.read_bytes()
    for filename in PACKAGE_FILES:
        if (ROOT / filename).is_file():
            desired[f"alpha-wiki/{filename}"] = (ROOT / filename).read_bytes()

    for source in sorted((ROOT / "skills").glob("*/SKILL.md")):
        operation = source.parent.name
        desired[f"skills/alpha-wiki-{operation}/SKILL.md"] = transform_skill(
            source.read_text(), operation, runtime
        ).encode()
        command = (
            "---\n"
            f"description: Alpha-Wiki {operation}\n"
            "subagent: false\n"
            "---\n\n"
            f"Load skill `alpha-wiki-{operation}` with the skill tool, then follow its workflow "
            "for the current project. Keep the user's actual task and scope.\n\n"
            "User input:\n$ARGUMENTS\n"
        )
        desired[f"commands/alpha-wiki/{operation}.md"] = command.encode()
    return desired


def install_opencode(config_dir: Path | None = None, *, dry_run: bool = False,
                     upgrade: bool = False) -> dict:
    config = (config_dir or default_config_dir()).expanduser().resolve()
    runtime = config / "alpha-wiki"
    if ROOT == runtime.resolve() or ROOT in runtime.resolve().parents or runtime.resolve() in ROOT.parents:
        raise ValueError("installation runtime must not overlap the source checkout")
    manifest_path = runtime / "install-manifest.json"
    old: dict = {}
    if manifest_path.is_symlink():
        raise ValueError(f"preserve user symlink: {manifest_path}")
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if not isinstance(old, dict) or old.get("managed_by") != MANAGED_BY or not isinstance(old.get("files"), dict):
            raise ValueError(f"not an Alpha-Wiki managed installation: {manifest_path}")
    elif runtime.exists() and (not runtime.is_dir() or any(runtime.iterdir())):
        raise ValueError(f"preserve existing unmanaged runtime: {runtime}")

    desired = _desired_files(config)
    writes: list[str] = []
    conflicts: list[str] = []
    # Preflight the complete write set before touching any user-owned path.
    for relative, content in desired.items():
        dest = config / relative
        parents = [dest, *list(dest.parents)[:len(dest.relative_to(config).parts)]]
        if any(p.is_symlink() for p in parents):
            conflicts.append(f"symlink: {dest}")
            continue
        if any(p.exists() and not p.is_dir() for p in dest.parents):
            conflicts.append(f"not a directory: {dest.parent}")
            continue
        if dest.exists():
            if not dest.is_file() or relative not in old.get("files", {}):
                conflicts.append(f"unmanaged: {dest}")
                continue
            current = _digest(dest.read_bytes())
            if current != old["files"][relative]:
                conflicts.append(f"user modified: {dest}")
                continue
            if current == _digest(content):
                continue
            if not upgrade:
                conflicts.append(f"update needs --upgrade: {dest}")
                continue
        writes.append(relative)
    if conflicts:
        raise ValueError("No changes made; preserve existing files:\n" + "\n".join(conflicts))

    version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
    manifest = {
        "managed_by": MANAGED_BY,
        "base_version": version,
        "platform": "opencode-v2",
        "files": {name: _digest(data) for name, data in desired.items()},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    write_manifest = not manifest_path.is_file() or manifest_path.read_bytes() != manifest_bytes
    if not dry_run:
        for relative in writes:
            dest = config / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(desired[relative])
        if write_manifest:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_bytes(manifest_bytes)
    return {
        "config_dir": str(config), "runtime": str(runtime), "base_version": version,
        "skills": sum(name.startswith("skills/") for name in desired),
        "commands": sum(name.startswith("commands/") for name in desired),
        "dry_run": dry_run, "writes": writes,
        "manifest_changed": write_manifest,
        "prepare_runtime": (
            f"UV_PROJECT_ENVIRONMENT={shlex.quote(str(runtime / '.venv'))} "
            f"uv sync --project {shlex.quote(str(runtime))} --no-dev"
        ),
    }


def cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, help="Default: XDG_CONFIG_HOME/opencode or ~/.config/opencode.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--upgrade", action="store_true", help="Update unchanged installer-owned files only.")
    args = parser.parse_args()
    try:
        result = install_opencode(args.config_dir, dry_run=args.dry_run, upgrade=args.upgrade)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
