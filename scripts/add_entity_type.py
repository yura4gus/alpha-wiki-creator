"""Config-backed schema evolution with validation and rollback on write failure."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import yaml

from tools.document_maintenance import _atomic_text, _safe


def add_entity_type(target: Path, spec: dict, trigger: str = "manual", wiki_dir: str | None = None) -> None:
    """Add one type to config, create its directory and journal the change.

    Existing instruction files are never rewritten. Ordinary write failures
    roll back this call's config/log writes and newly created empty directories.
    This is not an atomic multi-file transaction against process termination.
    """
    from tools.doctor import _resolve_wiki_dir

    root = target.resolve()
    if not isinstance(spec, dict) or not re.fullmatch(r"[a-z][a-z0-9_-]*", str(spec.get("name", ""))):
        raise ValueError("entity name must be a lowercase slug")
    value = spec.get("dir")
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute() or "\\" in value:
        raise ValueError("entity directory must be repository-relative")
    if any(part in {"", ".", ".."} for part in value.rstrip("/").split("/")):
        raise ValueError("entity directory must not contain empty, dot or parent components")
    if value.split("/")[0] in {"graph", "render", ".obsidian", "agentops"}:
        raise ValueError("entity directory must not own generated or optional AgentOps state")
    if any(char in value for char in ("\n", "\r", "`")):
        raise ValueError("entity directory must fit a single journal line")

    fields = {"name": spec["name"], "dir": value.rstrip("/")}
    for key in ("frontmatter_required", "frontmatter_optional", "sections_required"):
        items = spec.get(key, [])
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            raise ValueError(f"{key} must be a list of nonempty strings")
        fields[key] = items

    wiki = _safe(root, _resolve_wiki_dir(root, Path(wiki_dir) if wiki_dir is not None else None))
    directory = _safe(wiki, fields["dir"])
    config_path = _safe(root, ".alpha-wiki/config.yaml")
    log_path = _safe(root, wiki / "log.md")
    if not wiki.is_dir() or not config_path.is_file() or not log_path.is_file():
        raise ValueError("schema evolution requires initialized config and wiki/log.md")
    if directory.exists() and not directory.is_dir():
        raise ValueError("entity directory is occupied by a file")
    original = {path: path.read_text() for path in (config_path, log_path)}
    config = yaml.safe_load(original[config_path])
    if not isinstance(config, dict) or not isinstance(config.get("entity_types"), list):
        raise ValueError("config must contain an entity_types list")
    types = config["entity_types"]
    if any(not isinstance(item, dict) for item in types):
        raise ValueError("entity_types entries must be mappings")
    if any(item.get("name") == fields["name"] for item in types):
        raise ValueError(f"entity type already exists: {fields['name']}")
    if any(str(item.get("dir", "")).rstrip("/") == fields["dir"] for item in types):
        raise ValueError(f"entity directory already exists: {fields['dir']}")
    types.append(fields)
    reason = " ".join(str(trigger).split())
    payloads = {
        config_path: yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        log_path: original[log_path].rstrip() + f"\n\n## [{date.today().isoformat()}] schema-change | added type: {fields['name']} ({fields['dir']}/) | trigger: {reason}\n",
    }
    missing = []
    parent = directory
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    created = []
    written = []
    try:
        for parent in reversed(missing):
            parent.mkdir()
            created.append(parent)
        for path, content in payloads.items():
            if path.read_text() != original[path]:
                raise ValueError(f"concurrent edit detected; preserved: {path}")
            _atomic_text(path, content)
            written.append(path)
    except (OSError, ValueError):
        for path in reversed(written):
            if path.read_text() == payloads[path]:
                _atomic_text(path, original[path])
        for parent in reversed(created):
            try:
                parent.rmdir()
            except OSError:
                pass  # Never delete concurrent user files in a created directory.
        raise
