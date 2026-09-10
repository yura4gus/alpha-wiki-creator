"""Shared storage and validation for the optional Alpha-Wiki AgentOps layer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml
import click

from tools.wiki_engine import parse_page


AGENTOPS_VERSION = "0.2"
BACKLOG_STATUSES = {
    "TODO",
    "PLANNED",
    "IN_PROGRESS",
    "BLOCKED",
    "REVIEW",
    "DONE",
    "CANCELLED",
}
GOVERNANCE_STATUSES = {"GREEN", "WARNING", "BLOCKED"}
SESSION_STATUSES = {"IN_PROGRESS", "GREEN", "FIXES_REQUIRED", "BLOCKED", "UNPROVEN", "STALE_SNAPSHOT"}

ROLE_DEFINITIONS = {
    "cto": {
        "title": "CTO Agent",
        "owns": ["technical direction", "architecture decisions", "tradeoffs", "technical roadmap"],
    },
    "architect": {
        "title": "Architect Agent",
        "owns": ["system boundaries", "API contracts", "code contracts", "integration contracts"],
    },
    "backend": {
        "title": "Backend Agent",
        "owns": ["backend implementation", "APIs", "database", "migrations"],
    },
    "frontend": {
        "title": "Frontend Agent",
        "owns": ["UI", "user flows", "frontend contracts"],
    },
    "devops": {
        "title": "DevOps Agent",
        "owns": ["CI/CD", "environments", "deployment", "secrets and configuration"],
    },
    "qa": {
        "title": "QA Agent",
        "owns": ["unit tests", "integration tests", "end-to-end tests", "regression evidence"],
    },
    "documentation": {
        "title": "Documentation Agent",
        "owns": ["wiki freshness", "documentation consolidation", "stale detection", "missing contracts"],
    },
    "release": {
        "title": "Release Agent",
        "owns": ["staging readiness", "production checklist", "deployment verification", "release evidence"],
    },
}

ENTITY_DIRS = {
    "track": "tracks",
    "agent": "agents",
    "session": "sessions",
    "handoff": "handoffs",
    "decision": "decisions",
    "backlog_item": "backlog",
    "release": "releases",
}


class AgentOpsError(click.ClickException):
    """Raised when AgentOps state violates its deterministic contract."""


@dataclass(frozen=True)
class StoredEntity:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return date.today().isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise AgentOpsError("value must contain at least one letter or number")
    return slug


def agentops_root(wiki_dir: Path) -> Path:
    return wiki_dir.resolve() / "agentops"


def entity_slug(entity_type: str, entity_id: str) -> str:
    return f"agentops-{entity_type.replace('_', '-')}-{slugify(entity_id)}"


def entity_path(wiki_dir: Path, entity_type: str, entity_id: str) -> Path:
    if entity_type == "orchestrator":
        return agentops_root(wiki_dir) / "orchestrator.md"
    try:
        directory = ENTITY_DIRS[entity_type]
    except KeyError as exc:
        raise AgentOpsError(f"unsupported AgentOps entity type: {entity_type}") from exc
    return agentops_root(wiki_dir) / directory / f"{slugify(entity_id)}.md"


def link_for(entity_type: str, entity_id: str) -> str:
    return f"[[{entity_slug(entity_type, entity_id)}]]"


def write_entity(
    wiki_dir: Path,
    entity_type: str,
    entity_id: str,
    fields: dict[str, Any],
    body: str,
    *,
    overwrite: bool = False,
) -> Path:
    path = entity_path(wiki_dir, entity_type, entity_id)
    if path.exists() and not overwrite:
        raise AgentOpsError(f"entity already exists: {path}")
    now = utc_now()
    existing_created = None
    if path.exists():
        existing_created = parse_page(path).frontmatter.get("created_at")
    payload = dict(fields)
    frontmatter = {
        "title": payload.pop("title", entity_id),
        "slug": entity_slug(entity_type, entity_id),
        "agentops_type": entity_type,
        "id": entity_id,
        **payload,
        "created_at": existing_created or now,
        "updated_at": now,
        "date_updated": today(),
    }
    _atomic_write(path, _markdown(frontmatter, body))
    refresh_index(wiki_dir)
    return path


def load_entity(wiki_dir: Path, entity_type: str, entity_id: str) -> StoredEntity:
    path = entity_path(wiki_dir, entity_type, entity_id)
    if not path.exists():
        raise AgentOpsError(f"entity does not exist: {entity_type} {entity_id}")
    page = parse_page(path)
    return StoredEntity(path=path, frontmatter=page.frontmatter, body=page.body)


def list_entities(wiki_dir: Path, entity_type: str) -> list[StoredEntity]:
    if entity_type == "orchestrator":
        path = entity_path(wiki_dir, entity_type, "orchestrator")
        return [load_entity(wiki_dir, entity_type, "orchestrator")] if path.exists() else []
    directory = agentops_root(wiki_dir) / ENTITY_DIRS[entity_type]
    if not directory.exists():
        return []
    entities: list[StoredEntity] = []
    for path in sorted(directory.glob("*.md")):
        page = parse_page(path)
        entities.append(StoredEntity(path=path, frontmatter=page.frontmatter, body=page.body))
    return entities


def initialize_agentops(
    wiki_dir: Path,
    *,
    goal: str,
    current_objective: str,
    snapshot: str,
) -> list[Path]:
    if not wiki_dir.exists():
        raise AgentOpsError(f"wiki directory does not exist: {wiki_dir}")
    root = agentops_root(wiki_dir)
    for directory in ENTITY_DIRS.values():
        (root / directory).mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    orchestrator = entity_path(wiki_dir, "orchestrator", "orchestrator")
    if not orchestrator.exists():
        written.append(
            write_entity(
                wiki_dir,
                "orchestrator",
                "orchestrator",
                {
                    "title": "Master Orchestrator",
                    "status": "ACTIVE",
                    "goal": goal,
                    "current_objective": current_objective,
                    "snapshot": snapshot,
                    "governance_status": "WARNING",
                },
                _orchestrator_body(goal, current_objective),
            )
        )

    general_track = entity_path(wiki_dir, "track", "general")
    if not general_track.exists():
        written.append(
            write_entity(
                wiki_dir,
                "track",
                "general",
                {
                    "title": "General Track",
                    "status": "PLANNED",
                    "objective": current_objective,
                    "owner": "cto",
                    "agent_role": "cto",
                    "owned_by": link_for("agent", "cto"),
                    "belongs_to": link_for("orchestrator", "orchestrator"),
                    "dependencies": [],
                    "acceptance_criteria": [],
                },
                "# General Track\n\nDefault track for work that has not been split yet.\n",
            )
        )

    for role, definition in ROLE_DEFINITIONS.items():
        path = entity_path(wiki_dir, "agent", role)
        if path.exists():
            continue
        owns = definition["owns"]
        written.append(
            write_entity(
                wiki_dir,
                "agent",
                role,
                {
                    "title": definition["title"],
                    "status": "AVAILABLE",
                    "role": role,
                    "scope": owns,
                    "permissions": ["read assigned context", "write only assigned files"],
                    "belongs_to": link_for("orchestrator", "orchestrator"),
                },
                f"# {definition['title']}\n\n## Owns\n\n" + "\n".join(f"- {item}" for item in owns) + "\n",
            )
        )

    schema_path = root / "SCHEMA.md"
    if not schema_path.exists():
        _atomic_write(schema_path, _schema_document())
        written.append(schema_path)
    refresh_index(wiki_dir)
    return written


def update_orchestrator(
    wiki_dir: Path,
    *,
    current_objective: str | None = None,
    goal: str | None = None,
    snapshot: str | None = None,
    governance_status: str | None = None,
    next_master_prompt: str | None = None,
) -> Path:
    entity = load_entity(wiki_dir, "orchestrator", "orchestrator")
    fields = dict(entity.frontmatter)
    for generated in ("title", "slug", "agentops_type", "id", "created_at", "updated_at", "date_updated"):
        fields.pop(generated, None)
    if goal is not None:
        fields["goal"] = goal
    if current_objective is not None:
        fields["current_objective"] = current_objective
    if snapshot is not None:
        fields["snapshot"] = snapshot
    if governance_status is not None:
        normalized = governance_status.upper()
        if normalized not in GOVERNANCE_STATUSES:
            raise AgentOpsError(f"invalid governance status: {governance_status}")
        fields["governance_status"] = normalized
    if next_master_prompt is not None:
        fields["next_master_prompt"] = next_master_prompt
    body = _orchestrator_body(str(fields.get("goal", "")), str(fields.get("current_objective", "")))
    if fields.get("next_master_prompt"):
        body += f"\n## Next Master Prompt\n\n{fields['next_master_prompt']}\n"
    return write_entity(
        wiki_dir,
        "orchestrator",
        "orchestrator",
        {"title": "Master Orchestrator", **fields},
        body,
        overwrite=True,
    )


def refresh_index(wiki_dir: Path) -> Path:
    root = agentops_root(wiki_dir)
    root.mkdir(parents=True, exist_ok=True)
    sections: list[str] = [
        "# AgentOps Control Layer",
        "",
        f"_Optional Alpha-Wiki execution memory. Schema version: {AGENTOPS_VERSION}._",
        "",
        "Core Alpha-Wiki works without this directory. AgentOps state is summarized markdown, not raw agent logs.",
        "",
    ]
    orchestrator = entity_path(wiki_dir, "orchestrator", "orchestrator")
    if orchestrator.exists():
        sections.extend(["## Orchestrator", "", f"- {link_for('orchestrator', 'orchestrator')}", ""])
    schema = root / "SCHEMA.md"
    if schema.exists():
        sections.extend(["## Schema", "", "- [[SCHEMA]]", ""])
    labels = {
        "track": "Tracks",
        "agent": "Agents",
        "backlog_item": "Backlog",
        "session": "Sessions",
        "handoff": "Handoffs",
        "decision": "Decisions",
        "release": "Releases",
    }
    for entity_type, label in labels.items():
        entities = list_entities(wiki_dir, entity_type)
        sections.extend([f"## {label}", ""])
        if entities:
            for entity in entities:
                fm = entity.frontmatter
                status = f" [{fm.get('status')}]" if fm.get("status") else ""
                sections.append(f"- [[{fm['slug']}]] - {fm.get('title', fm['id'])}{status}")
        else:
            sections.append("_(none)_")
        sections.append("")
    rollups = sorted((root / "rollups").glob("*.md")) if (root / "rollups").exists() else []
    sections.extend(["## Rollups", ""])
    if rollups:
        for path in rollups:
            page = parse_page(path)
            sections.append(f"- [[{page.slug}]] - {page.title}")
    else:
        sections.append("_(none)_")
    sections.append("")
    path = root / "index.md"
    _atomic_write(path, "\n".join(sections).rstrip() + "\n")
    return path


def append_wiki_log(wiki_dir: Path, operation: str, description: str) -> None:
    log = wiki_dir / "log.md"
    if not log.exists():
        return
    safe_operation = re.sub(r"[^a-z0-9-]+", "-", operation.strip().lower()).strip("-") or "update"
    safe_description = " ".join(description.split())[:500]
    with log.open("a") as stream:
        stream.write(f"\n## [{today()}] agentops-{safe_operation} | {safe_description}\n")


def normalized_list(values: Iterable[str] | None) -> list[str]:
    return [value.strip() for value in (values or []) if value and value.strip()]


def body_section(title: str, values: Iterable[str] | str | None) -> str:
    if isinstance(values, str):
        content = values.strip() or "_(none)_"
        return f"## {title}\n\n{content}\n"
    items = normalized_list(values)
    content = "\n".join(f"- {item}" for item in items) if items else "_(none)_"
    return f"## {title}\n\n{content}\n"


def _orchestrator_body(goal: str, objective: str) -> str:
    return (
        "# Master Orchestrator\n\n"
        "The orchestrator is controller-owned state. It is not a background agent.\n\n"
        f"## Master Goal\n\n{goal}\n\n"
        f"## Current Objective\n\n{objective}\n"
    )


def _markdown(frontmatter: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).rstrip()
    return f"---\n{dumped}\n---\n{body.lstrip()}".rstrip() + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def _schema_document() -> str:
    return f"""# AgentOps Schema v{AGENTOPS_VERSION}

Operational state lives only under this directory. The schema is intentionally
small and is independent of Alpha-Wiki's project entity schema.

## Entities

- `orchestrator`: master goal, current objective, snapshot, governance status, next prompt.
- `track`: objective, owner, role, dependencies, acceptance criteria.
- `agent`: role declaration, scope, permissions. Native platform agents execute it.
- `session`: one summarized execution-wave result with files, contracts, tests, risks and next steps.
- `handoff`: summarized transfer between roles; raw logs are forbidden.
- `decision`: execution decision linked to source session and affected contracts/files.
- `backlog_item`: one task per file for scalable filtering and disjoint writes.
- `release`: deterministic readiness evidence and blockers for one target.

## Status Models

- Backlog: `TODO`, `PLANNED`, `IN_PROGRESS`, `BLOCKED`, `REVIEW`, `DONE`, `CANCELLED`.
- Governance: `GREEN`, `WARNING`, `BLOCKED`.
- Session terminal: `GREEN`, `FIXES_REQUIRED`, `BLOCKED`, `UNPROVEN`, `STALE_SNAPSHOT`.
"""
