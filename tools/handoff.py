"""Create and validate summarized AgentOps handoffs."""
from __future__ import annotations

from pathlib import Path

import click

from tools._agentops import (
    AgentOpsError,
    append_wiki_log,
    body_section,
    link_for,
    list_entities,
    load_entity,
    normalized_list,
    write_entity,
)


MAX_CONTEXT_SUMMARY = 4000


def validate_handoffs(wiki_dir: Path) -> list[str]:
    findings: list[str] = []
    agent_ids = {str(entity.frontmatter.get("id")) for entity in list_entities(wiki_dir, "agent")}
    session_ids = {str(entity.frontmatter.get("id")) for entity in list_entities(wiki_dir, "session")}
    for handoff in list_entities(wiki_dir, "handoff"):
        fm = handoff.frontmatter
        handoff_id = fm.get("id", handoff.path.stem)
        for field in ("from_agent", "to_agent", "context_summary", "completed_work", "unfinished_work", "files", "contracts", "risks", "decisions", "next_action"):
            if field not in fm:
                findings.append(f"{handoff_id}: missing {field}")
        summary = str(fm.get("context_summary", ""))
        if not summary.strip():
            findings.append(f"{handoff_id}: empty context_summary")
        if len(summary) > MAX_CONTEXT_SUMMARY:
            findings.append(f"{handoff_id}: context_summary exceeds {MAX_CONTEXT_SUMMARY} characters")
        if not str(fm.get("next_action", "")).strip():
            findings.append(f"{handoff_id}: empty next_action")
        for field in ("from_agent", "to_agent"):
            if str(fm.get(field)) not in agent_ids:
                findings.append(f"{handoff_id}: unknown {field} {fm.get(field)}")
        session = str(fm.get("session", "")).strip()
        if session and session not in session_ids:
            findings.append(f"{handoff_id}: unknown session {session}")
    return findings


@click.group()
def cli() -> None:
    """Manage concise role-to-role transfers without raw logs."""


@cli.command("create")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--id", "handoff_id", required=True)
@click.option("--from-agent", required=True)
@click.option("--to-agent", required=True)
@click.option("--session", default=None)
@click.option("--context", "context_summary", required=True)
@click.option("--completed", multiple=True)
@click.option("--unfinished", multiple=True)
@click.option("--file", "files", multiple=True)
@click.option("--contract", multiple=True)
@click.option("--risk", multiple=True)
@click.option("--decision", multiple=True)
@click.option("--next-action", required=True)
def create_handoff(
    wiki_dir: Path,
    handoff_id: str,
    from_agent: str,
    to_agent: str,
    session: str | None,
    context_summary: str,
    completed: tuple[str, ...],
    unfinished: tuple[str, ...],
    files: tuple[str, ...],
    contract: tuple[str, ...],
    risk: tuple[str, ...],
    decision: tuple[str, ...],
    next_action: str,
) -> None:
    load_entity(wiki_dir, "agent", from_agent)
    load_entity(wiki_dir, "agent", to_agent)
    if session:
        load_entity(wiki_dir, "session", session)
    if len(context_summary) > MAX_CONTEXT_SUMMARY:
        raise click.UsageError(f"--context exceeds {MAX_CONTEXT_SUMMARY} characters; summarize it")
    fields = {
        "title": f"Handoff {handoff_id}",
        "status": "OPEN",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "from_agent_link": link_for("agent", from_agent),
        "to_agent_link": link_for("agent", to_agent),
        "session": session or "",
        "context_summary": context_summary,
        "completed_work": normalized_list(completed),
        "unfinished_work": normalized_list(unfinished),
        "files": normalized_list(files),
        "contracts": normalized_list(contract),
        "risks": normalized_list(risk),
        "decisions": normalized_list(decision),
        "next_action": next_action,
        "belongs_to": link_for("orchestrator", "orchestrator"),
    }
    body = f"# Handoff {handoff_id}\n\n"
    for title, value in (
        ("From", from_agent),
        ("To", to_agent),
        ("Context Summary", context_summary),
        ("Completed Work", completed),
        ("Unfinished Work", unfinished),
        ("Files", files),
        ("Contracts", contract),
        ("Risks", risk),
        ("Decisions", decision),
        ("Next Action", next_action),
    ):
        body += body_section(title, value) + "\n"
    path = write_entity(wiki_dir, "handoff", handoff_id, fields, body)
    append_wiki_log(wiki_dir, "handoff", f"{from_agent} -> {to_agent}; id={handoff_id}")
    click.echo(f"created {path}")


@cli.command("validate")
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def validate(wiki_dir: Path) -> None:
    findings = validate_handoffs(wiki_dir)
    if findings:
        raise click.ClickException("\n".join(findings))
    click.echo("handoffs: valid")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
