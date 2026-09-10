"""Markdown backlog operations for the optional Alpha-Wiki AgentOps layer."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from tools._agentops import (
    AgentOpsError,
    BACKLOG_STATUSES,
    append_wiki_log,
    body_section,
    link_for,
    list_entities,
    load_entity,
    normalized_list,
    write_entity,
)


def backlog_items(wiki_dir: Path) -> list[dict]:
    return [dict(item.frontmatter) for item in list_entities(wiki_dir, "backlog_item")]


def dependency_gaps(items: list[dict]) -> list[str]:
    by_id = {str(item.get("id")): item for item in items}
    gaps: list[str] = []
    graph: dict[str, list[str]] = {}
    for item_id, item in by_id.items():
        dependencies = [str(value) for value in item.get("dependencies", [])]
        graph[item_id] = dependencies
        for dependency in dependencies:
            target = by_id.get(dependency)
            if target is None:
                gaps.append(f"{item_id}: missing dependency {dependency}")
            elif target.get("status") not in {"DONE", "CANCELLED"} and item.get("status") in {"IN_PROGRESS", "REVIEW", "DONE"}:
                gaps.append(f"{item_id}: dependency {dependency} is {target.get('status')}")
    gaps.extend(_cycles(graph))
    return sorted(set(gaps))


def validate_backlog(wiki_dir: Path) -> list[str]:
    entities = list_entities(wiki_dir, "backlog_item")
    items = [dict(entity.frontmatter) for entity in entities]
    findings = dependency_gaps(items)
    agent_ids = {str(entity.frontmatter.get("id")) for entity in list_entities(wiki_dir, "agent")}
    track_ids = {str(entity.frontmatter.get("id")) for entity in list_entities(wiki_dir, "track")}
    item_ids = Counter(str(item.get("id")) for item in items)
    for duplicate in sorted(item_id for item_id, count in item_ids.items() if count > 1):
        findings.append(f"duplicate backlog id: {duplicate}")
    for item in items:
        item_id = item.get("id", "unknown")
        status = str(item.get("status", ""))
        if status not in BACKLOG_STATUSES:
            findings.append(f"{item_id}: invalid status {status}")
        for field in (
            "title", "description", "owner", "agent_role", "priority", "track",
            "dependencies", "contracts", "files", "acceptance_criteria", "evidence",
            "created_at", "updated_at",
        ):
            if field not in item:
                findings.append(f"{item_id}: missing {field}")
        for field in ("title", "description", "owner", "agent_role", "track"):
            if not str(item.get(field, "")).strip():
                findings.append(f"{item_id}: empty {field}")
        if str(item.get("agent_role")) not in agent_ids:
            findings.append(f"{item_id}: unknown agent_role {item.get('agent_role')}")
        if str(item.get("track")) not in track_ids:
            findings.append(f"{item_id}: unknown track {item.get('track')}")
        try:
            priority = int(item.get("priority"))
        except (TypeError, ValueError):
            findings.append(f"{item_id}: invalid priority {item.get('priority')}")
        else:
            if priority not in range(4):
                findings.append(f"{item_id}: invalid priority {priority}")
        if not normalized_list(item.get("acceptance_criteria", [])):
            findings.append(f"{item_id}: acceptance_criteria is empty")
        if status == "DONE" and not normalized_list(item.get("evidence", [])):
            findings.append(f"{item_id}: DONE requires evidence")
        if status == "BLOCKED" and not str(item.get("blocked_reason", "")).strip():
            findings.append(f"{item_id}: BLOCKED requires blocked_reason")
    return sorted(set(findings))


def backlog_report(
    wiki_dir: Path,
    *,
    status: str | None = None,
    owner: str | None = None,
    role: str | None = None,
    track: str | None = None,
) -> str:
    items = backlog_items(wiki_dir)
    if status:
        items = [item for item in items if item.get("status") == status]
    if owner:
        items = [item for item in items if item.get("owner") == owner]
    if role:
        items = [item for item in items if item.get("agent_role") == role]
    if track:
        items = [item for item in items if item.get("track") == track]
    lines = ["# AgentOps Backlog", "", f"- Items: {len(items)}", ""]
    if not items:
        lines.append("_(none)_")
    else:
        lines.extend(
            f"- {item['id']} [{item['status']}] P{item['priority']} {item['title']} | track={item['track']} owner={item['owner']}"
            for item in sorted(items, key=lambda item: (int(item.get("priority", 9)), str(item.get("id"))))
        )
    return "\n".join(lines).rstrip() + "\n"


@click.group()
def cli() -> None:
    """Manage one-file-per-item AgentOps backlog state."""


@cli.command("add")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--id", "item_id", required=True)
@click.option("--title", required=True)
@click.option("--description", required=True)
@click.option("--owner", required=True)
@click.option("--role", required=True)
@click.option("--priority", type=click.IntRange(0, 3), required=True)
@click.option("--status", type=click.Choice(sorted(BACKLOG_STATUSES)), default="TODO", show_default=True)
@click.option("--track", required=True)
@click.option("--dependency", multiple=True)
@click.option("--contract", multiple=True)
@click.option("--file", "files", multiple=True)
@click.option("--acceptance", multiple=True, required=True)
@click.option("--evidence", multiple=True)
@click.option("--blocked-reason", default="")
def add_item(
    wiki_dir: Path,
    item_id: str,
    title: str,
    description: str,
    owner: str,
    role: str,
    priority: int,
    status: str,
    track: str,
    dependency: tuple[str, ...],
    contract: tuple[str, ...],
    files: tuple[str, ...],
    acceptance: tuple[str, ...],
    evidence: tuple[str, ...],
    blocked_reason: str,
) -> None:
    load_entity(wiki_dir, "track", track)
    load_entity(wiki_dir, "agent", role)
    dependencies = normalized_list(dependency)
    accepted = normalized_list(acceptance)
    proof = normalized_list(evidence)
    if status == "DONE" and not proof:
        raise click.UsageError("DONE requires at least one --evidence")
    if status == "BLOCKED" and not blocked_reason.strip():
        raise click.UsageError("BLOCKED requires --blocked-reason")
    path = write_entity(
        wiki_dir,
        "backlog_item",
        item_id,
        {
            "title": title,
            "status": status,
            "description": description,
            "owner": owner,
            "agent_role": role,
            "owned_by": link_for("agent", role),
            "priority": priority,
            "track": track,
            "dependencies": dependencies,
            "depends_on": [link_for("backlog_item", item) for item in dependencies],
            "contracts": normalized_list(contract),
            "files": normalized_list(files),
            "acceptance_criteria": accepted,
            "evidence": proof,
            "blocked_reason": blocked_reason.strip(),
            "belongs_to": link_for("track", track),
        },
        f"# {title}\n\n{description}\n\n{body_section('Acceptance Criteria', accepted)}\n{body_section('Evidence', proof)}",
    )
    findings = validate_backlog(wiki_dir)
    if findings:
        path.unlink(missing_ok=True)
        from tools._agentops import refresh_index

        refresh_index(wiki_dir)
        raise AgentOpsError("backlog validation failed: " + "; ".join(findings))
    append_wiki_log(wiki_dir, "backlog", f"created {item_id} status={status}")
    click.echo(f"created {path}")


@cli.command("update")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.argument("item_id")
@click.option("--status", type=click.Choice(sorted(BACKLOG_STATUSES)), required=True)
@click.option("--evidence", multiple=True)
@click.option("--blocked-reason", default=None)
def update_item(
    wiki_dir: Path,
    item_id: str,
    status: str,
    evidence: tuple[str, ...],
    blocked_reason: str | None,
) -> None:
    entity = load_entity(wiki_dir, "backlog_item", item_id)
    original = entity.path.read_text()
    fields = dict(entity.frontmatter)
    for key in ("title", "slug", "agentops_type", "id", "created_at", "updated_at", "date_updated"):
        fields.pop(key, None)
    proof = normalized_list(evidence) or normalized_list(fields.get("evidence", []))
    reason = blocked_reason if blocked_reason is not None else str(fields.get("blocked_reason", ""))
    if status == "DONE" and not proof:
        raise click.UsageError("DONE requires at least one --evidence")
    if status == "BLOCKED" and not reason.strip():
        raise click.UsageError("BLOCKED requires --blocked-reason")
    fields.update(status=status, evidence=proof, blocked_reason=reason.strip())
    body = f"# {entity.frontmatter['title']}\n\n{fields['description']}\n\n"
    body += body_section("Acceptance Criteria", fields.get("acceptance_criteria", [])) + "\n"
    body += body_section("Evidence", proof)
    path = write_entity(
        wiki_dir,
        "backlog_item",
        item_id,
        {"title": entity.frontmatter["title"], **fields},
        body,
        overwrite=True,
    )
    findings = validate_backlog(wiki_dir)
    if findings:
        entity.path.write_text(original)
        from tools._agentops import refresh_index

        refresh_index(wiki_dir)
        raise AgentOpsError("backlog validation failed: " + "; ".join(findings))
    append_wiki_log(wiki_dir, "backlog", f"updated {item_id} status={status}")
    click.echo(f"updated {path}")


@cli.command("list")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--status", type=click.Choice(sorted(BACKLOG_STATUSES)), default=None)
@click.option("--owner", default=None)
@click.option("--role", default=None)
@click.option("--track", default=None)
def list_items(wiki_dir: Path, status: str | None, owner: str | None, role: str | None, track: str | None) -> None:
    click.echo(backlog_report(wiki_dir, status=status, owner=owner, role=role, track=track))


@cli.command("blocked")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def blocked_items(wiki_dir: Path) -> None:
    click.echo(backlog_report(wiki_dir, status="BLOCKED"))


@cli.command("dependencies")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.argument("item_id", required=False)
def dependencies(wiki_dir: Path, item_id: str | None) -> None:
    items = backlog_items(wiki_dir)
    if item_id:
        items = [item for item in items if item.get("id") == item_id]
        if not items:
            raise click.ClickException(f"unknown backlog item: {item_id}")
    lines = ["# Backlog Dependencies", ""]
    for item in items:
        deps = ", ".join(item.get("dependencies", [])) or "none"
        lines.append(f"- {item['id']}: {deps}")
    gaps = dependency_gaps(backlog_items(wiki_dir))
    lines.extend(["", "## Gaps", ""] + ([f"- {gap}" for gap in gaps] if gaps else ["_(none)_"]))
    click.echo("\n".join(lines) + "\n")


@cli.command("validate")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def validate(wiki_dir: Path) -> None:
    findings = validate_backlog(wiki_dir)
    if findings:
        raise click.ClickException("\n".join(findings))
    click.echo("backlog: valid")


def _cycles(graph: dict[str, list[str]]) -> list[str]:
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in path:
            cycle = path[path.index(node):] + [node]
            cycles.add(tuple(cycle))
            return
        if node not in graph:
            return
        for target in graph[node]:
            visit(target, [*path, node])

    for node in graph:
        visit(node, [])
    return ["dependency cycle: " + " -> ".join(cycle) for cycle in sorted(cycles)]


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
