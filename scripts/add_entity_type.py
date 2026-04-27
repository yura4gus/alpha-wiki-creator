"""Schema evolution: append a new entity type to CLAUDE.md, create dir, log it."""
from __future__ import annotations
from datetime import date as _date
from pathlib import Path

PAGE_TYPES_HEADER = "## Page Types"


def add_entity_type(target: Path, spec: dict, trigger: str = "manual") -> None:
    """Add a new entity type to CLAUDE.md, create its directory, and log the change.

    Args:
        target: Root wiki directory (contains CLAUDE.md and wiki/)
        spec: Entity type specification with keys:
            - name: Type name (e.g., "migration")
            - dir: Relative path in wiki/ (e.g., "data/migrations")
            - frontmatter_required: List of required frontmatter keys
            - frontmatter_optional: (optional) List of optional frontmatter keys
            - sections_required: (optional) List of required markdown sections
        trigger: Description of what triggered this change (for logging)
    """
    claude_path = target / "CLAUDE.md"
    text = claude_path.read_text()
    new_section = _render_type_section(spec)

    if PAGE_TYPES_HEADER in text:
        # Append after the Page Types header section (before next ## section)
        idx = text.index(PAGE_TYPES_HEADER)
        next_h2 = text.find("\n## ", idx + len(PAGE_TYPES_HEADER))
        insert_at = next_h2 if next_h2 != -1 else len(text)
        text = text[:insert_at] + "\n" + new_section + "\n" + text[insert_at:]
    else:
        text = text + f"\n\n{PAGE_TYPES_HEADER}\n\n" + new_section + "\n"

    claude_path.write_text(text)

    new_dir = target / "wiki" / spec["dir"]
    new_dir.mkdir(parents=True, exist_ok=True)

    log_path = target / "wiki" / "log.md"
    today = _date.today().isoformat()
    log_path.write_text(
        log_path.read_text()
        + f"\n## [{today}] schema-change | added type: {spec['name']} ({spec['dir']}/) | trigger: {trigger}\n"
    )


def _render_type_section(spec: dict) -> str:
    """Render a type section for CLAUDE.md."""
    lines = [
        f"### {spec['name']} (`wiki/{spec['dir']}/`)\n",
        f"- **Required frontmatter:** {', '.join(spec.get('frontmatter_required', []))}",
    ]
    if spec.get("frontmatter_optional"):
        lines.append(f"- **Optional frontmatter:** {', '.join(spec['frontmatter_optional'])}")
    if spec.get("sections_required"):
        lines.append(f"- **Required sections:** {', '.join(spec['sections_required'])}")
    return "\n".join(lines)
