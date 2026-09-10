"""Deterministic state operations for Alpha-Wiki AgentOps orchestration."""
from __future__ import annotations

from pathlib import Path

import click

from tools._agentops import (
    AgentOpsError,
    SESSION_STATUSES,
    append_wiki_log,
    body_section,
    initialize_agentops,
    link_for,
    list_entities,
    load_entity,
    normalized_list,
    update_orchestrator,
    write_entity,
)
from tools.worktree_snapshot import build_snapshot


def current_snapshot(root: Path | None = None) -> str:
    try:
        return build_snapshot(root or Path.cwd()).snapshot_id
    except RuntimeError:
        return "UNVERSIONED"


def orchestrator_report(wiki_dir: Path) -> str:
    orchestrator = load_entity(wiki_dir, "orchestrator", "orchestrator")
    tracks = list_entities(wiki_dir, "track")
    sessions = list_entities(wiki_dir, "session")
    active = [item for item in sessions if item.frontmatter.get("status") == "IN_PROGRESS"]
    fm = orchestrator.frontmatter
    lines = [
        "# AgentOps Orchestrator",
        "",
        f"- Goal: {fm.get('goal', '')}",
        f"- Current objective: {fm.get('current_objective', '')}",
        f"- Governance: {fm.get('governance_status', 'WARNING')}",
        f"- Snapshot: {fm.get('snapshot', '')}",
        f"- Tracks: {len(tracks)}",
        f"- Sessions: {len(sessions)} ({len(active)} active)",
    ]
    if fm.get("next_master_prompt"):
        lines.extend(["", "## Next Master Prompt", "", str(fm["next_master_prompt"])])
    return "\n".join(lines).rstrip() + "\n"


@click.group()
def cli() -> None:
    """Manage the optional Alpha-Wiki AgentOps control layer."""


@cli.command("init")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--goal", required=True)
@click.option("--objective", required=True)
@click.option("--snapshot", default=None, help="Pinned snapshot; auto-detected when omitted.")
def init_command(wiki_dir: Path, goal: str, objective: str, snapshot: str | None) -> None:
    snapshot = snapshot or current_snapshot(wiki_dir.resolve().parent)
    written = initialize_agentops(wiki_dir, goal=goal, current_objective=objective, snapshot=snapshot)
    append_wiki_log(wiki_dir, "init", f"goal={goal}; created={len(written)}")
    click.echo(f"initialized {wiki_dir / 'agentops'} ({len(written)} new file(s))")


@cli.command("set-objective")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--objective", required=True)
@click.option("--goal", default=None)
@click.option("--governance", type=click.Choice(["GREEN", "WARNING", "BLOCKED"]), default=None)
@click.option("--next-prompt", default=None)
def set_objective(
    wiki_dir: Path,
    objective: str,
    goal: str | None,
    governance: str | None,
    next_prompt: str | None,
) -> None:
    snapshot = current_snapshot(wiki_dir.resolve().parent)
    path = update_orchestrator(
        wiki_dir,
        current_objective=objective,
        goal=goal,
        snapshot=snapshot,
        governance_status=governance,
        next_master_prompt=next_prompt,
    )
    append_wiki_log(wiki_dir, "objective", objective)
    click.echo(f"updated {path}")


@cli.command("add-track")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--id", "track_id", required=True)
@click.option("--title", required=True)
@click.option("--objective", required=True)
@click.option("--owner", required=True)
@click.option("--role", required=True)
@click.option("--depends-on", multiple=True)
@click.option("--acceptance", multiple=True)
def add_track(
    wiki_dir: Path,
    track_id: str,
    title: str,
    objective: str,
    owner: str,
    role: str,
    depends_on: tuple[str, ...],
    acceptance: tuple[str, ...],
) -> None:
    load_entity(wiki_dir, "agent", role)
    for dependency in normalized_list(depends_on):
        load_entity(wiki_dir, "track", dependency)
    dependencies = normalized_list(depends_on)
    path = write_entity(
        wiki_dir,
        "track",
        track_id,
        {
            "title": title,
            "status": "PLANNED",
            "objective": objective,
            "owner": owner,
            "agent_role": role,
            "owned_by": link_for("agent", role),
            "dependencies": dependencies,
            "depends_on": [link_for("track", item) for item in dependencies],
            "acceptance_criteria": normalized_list(acceptance),
            "belongs_to": link_for("orchestrator", "orchestrator"),
        },
        f"# {title}\n\n{body_section('Objective', objective)}\n{body_section('Acceptance Criteria', acceptance)}",
    )
    click.echo(f"created {path}")


@cli.command("session-start")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--id", "session_id", required=True)
@click.option("--role", required=True)
@click.option("--goal", required=True)
@click.option("--scope", required=True)
@click.option("--track", default="general")
@click.option("--snapshot", default=None)
def session_start(
    wiki_dir: Path,
    session_id: str,
    role: str,
    goal: str,
    scope: str,
    track: str,
    snapshot: str | None,
) -> None:
    load_entity(wiki_dir, "agent", role)
    load_entity(wiki_dir, "track", track)
    snapshot = snapshot or current_snapshot(wiki_dir.resolve().parent)
    path = write_entity(
        wiki_dir,
        "session",
        session_id,
        {
            "title": f"Session {session_id}",
            "status": "IN_PROGRESS",
            "session_id": session_id,
            "agent": link_for("agent", role),
            "agent_role": role,
            "owned_by": link_for("agent", role),
            "goal": goal,
            "scope": scope,
            "snapshot": snapshot,
            "files_changed": [],
            "contracts_changed": [],
            "decisions": [],
            "risks": [],
            "tests": [],
            "result": "",
            "next_steps": [],
            "belongs_to": link_for("track", track),
        },
        f"# Session {session_id}\n\n{body_section('Goal', goal)}\n{body_section('Scope', scope)}",
    )
    click.echo(f"created {path}")


@cli.command("session-complete")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.argument("session_id")
@click.option("--status", type=click.Choice(sorted(SESSION_STATUSES - {"IN_PROGRESS"})), required=True)
@click.option("--result", required=True)
@click.option("--file", "files_changed", multiple=True)
@click.option("--contract", "contracts_changed", multiple=True)
@click.option("--decision", "decisions", multiple=True)
@click.option("--risk", "risks", multiple=True)
@click.option("--test", "tests", multiple=True)
@click.option("--next-step", "next_steps", multiple=True)
def session_complete(
    wiki_dir: Path,
    session_id: str,
    status: str,
    result: str,
    files_changed: tuple[str, ...],
    contracts_changed: tuple[str, ...],
    decisions: tuple[str, ...],
    risks: tuple[str, ...],
    tests: tuple[str, ...],
    next_steps: tuple[str, ...],
) -> None:
    entity = load_entity(wiki_dir, "session", session_id)
    fields = dict(entity.frontmatter)
    for key in ("title", "slug", "agentops_type", "id", "created_at", "updated_at", "date_updated"):
        fields.pop(key, None)
    fields.update(
        status=status,
        result=result,
        files_changed=normalized_list(files_changed),
        contracts_changed=normalized_list(contracts_changed),
        decisions=normalized_list(decisions),
        risks=normalized_list(risks),
        tests=normalized_list(tests),
        next_steps=normalized_list(next_steps),
    )
    body = f"# Session {session_id}\n\n"
    for title, value in (
        ("Goal", str(fields.get("goal", ""))),
        ("Scope", str(fields.get("scope", ""))),
        ("Result", result),
        ("Files Changed", files_changed),
        ("Contracts Changed", contracts_changed),
        ("Decisions", decisions),
        ("Risks", risks),
        ("Tests", tests),
        ("Next Steps", next_steps),
    ):
        body += body_section(title, value) + "\n"
    path = write_entity(
        wiki_dir,
        "session",
        session_id,
        {"title": f"Session {session_id}", **fields},
        body,
        overwrite=True,
    )
    append_wiki_log(wiki_dir, "session", f"{session_id} status={status}")
    click.echo(f"updated {path}")


@cli.command("record-decision")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--id", "decision_id", required=True)
@click.option("--title", required=True)
@click.option("--owner", required=True)
@click.option("--context", required=True)
@click.option("--decision", required=True)
@click.option("--consequence", multiple=True, required=True)
@click.option("--affects", multiple=True)
@click.option("--source-session", default=None)
def record_decision(
    wiki_dir: Path,
    decision_id: str,
    title: str,
    owner: str,
    context: str,
    decision: str,
    consequence: tuple[str, ...],
    affects: tuple[str, ...],
    source_session: str | None,
) -> None:
    load_entity(wiki_dir, "agent", owner)
    if source_session:
        load_entity(wiki_dir, "session", source_session)
    affected_refs = normalized_list(affects)
    path = write_entity(
        wiki_dir,
        "decision",
        decision_id,
        {
            "title": title,
            "status": "ACCEPTED",
            "owner": owner,
            "owned_by": link_for("agent", owner),
            "context": context,
            "decision": decision,
            "consequences": normalized_list(consequence),
            "affected_refs": affected_refs,
            "affects": [
                item for item in affected_refs
                if item.startswith("[[") and item[-2:] == "]]"
            ],
            "source_session": source_session or "",
            "belongs_to": link_for("orchestrator", "orchestrator"),
        },
        f"# {title}\n\n{body_section('Context', context)}\n{body_section('Decision', decision)}\n"
        f"{body_section('Consequences', consequence)}\n{body_section('Affected References', affects)}",
    )
    append_wiki_log(wiki_dir, "decision", f"{decision_id} owner={owner}")
    click.echo(f"created {path}")


@cli.command("status")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def status_command(wiki_dir: Path) -> None:
    click.echo(orchestrator_report(wiki_dir))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
