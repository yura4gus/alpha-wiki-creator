"""Install Alpha-Wiki skills into Codex skill home with safe prefixed names."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = ROOT / "skills"
DEFAULT_TARGET = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"


def codex_skill_name(source_name: str) -> str:
    return f"alpha-wiki-{source_name}"


def transform_skill_for_codex(text: str, source_name: str) -> str:
    if not text.startswith("---\n"):
        raise ValueError(f"skill has no frontmatter: {source_name}")
    _, frontmatter, body = text.split("---", 2)
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
    adapter_note = (
        "\n## Codex Adapter\n\n"
        f"In Codex, invoke this skill as `${codex_name}`. "
        f"Claude Code slash-command equivalent: `/alpha-wiki:{source_name}`.\n\n"
        "Use the repository-local `tools/` scripts for deterministic work, and keep "
        "the same Alpha-Wiki mutability rules: source pages are editable, "
        "`graph/` artifacts are generated, and schema changes are gated.\n"
    )
    return f"---{frontmatter}---{adapter_note}{body.lstrip()}"


def install_codex_skills(target: Path = DEFAULT_TARGET, dry_run: bool = False) -> list[Path]:
    installed: list[Path] = []
    for skill_path in sorted(SOURCE_SKILLS.glob("*/SKILL.md")):
        source_name = skill_path.parent.name
        dest = target / codex_skill_name(source_name) / "SKILL.md"
        installed.append(dest)
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(transform_skill_for_codex(skill_path.read_text(), source_name))
    return installed


def cli() -> None:
    parser = argparse.ArgumentParser(description="Install Alpha-Wiki skills for Codex.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="Codex skills directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing.")
    args = parser.parse_args()

    installed = install_codex_skills(args.target.expanduser(), dry_run=args.dry_run)
    action = "would install" if args.dry_run else "installed"
    for path in installed:
        print(f"{action}: {path}")
    print(f"{action} {len(installed)} Alpha-Wiki Codex skill(s)")


if __name__ == "__main__":
    cli()
