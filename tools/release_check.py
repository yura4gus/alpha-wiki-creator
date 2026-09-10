"""Project release readiness for the optional Alpha-Wiki AgentOps layer."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from tools._agentops import StoredEntity, append_wiki_log, link_for, list_entities, load_entity, update_orchestrator, write_entity
from tools.backlog import backlog_items, validate_backlog
from tools.handoff import validate_handoffs
from tools._models import LintSeverity
from tools.lint import _load_config, run_all_checks


def release_check_report(
    wiki_dir: Path,
    version: str,
    config_path: Path | None = None,
) -> tuple[str, str, list[str], list[str]]:
    items = backlog_items(wiki_dir)
    counts = Counter(str(item.get("status", "UNKNOWN")) for item in items)
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(validate_backlog(wiki_dir))
    blockers.extend(validate_handoffs(wiki_dir))
    for item in items:
        if item.get("status") == "BLOCKED":
            blockers.append(f"{item['id']}: {item.get('blocked_reason', 'blocked')}")
        elif item.get("status") in {"TODO", "PLANNED", "IN_PROGRESS"}:
            blockers.append(f"{item['id']}: release work is {item.get('status')}")
        elif item.get("status") == "REVIEW":
            warnings.append(f"{item['id']}: still in REVIEW")

    if not items:
        warnings.append("backlog is empty; release scope is unproven")
    sessions = list_entities(wiki_dir, "session")
    if not sessions:
        warnings.append("no AgentOps session evidence exists")
    latest_sessions: dict[tuple[str, str], StoredEntity] = {}
    for session in sessions:
        key = (str(session.frontmatter.get("belongs_to", "")), str(session.frontmatter.get("agent_role", "")))
        current = latest_sessions.get(key)
        if current is None or str(session.frontmatter.get("updated_at", "")) > str(current.frontmatter.get("updated_at", "")):
            latest_sessions[key] = session
    for session in latest_sessions.values():
        status = str(session.frontmatter.get("status", "UNPROVEN"))
        session_id = session.frontmatter.get("session_id", session.frontmatter.get("id", "unknown"))
        if status in {"IN_PROGRESS", "FIXES_REQUIRED", "BLOCKED", "UNPROVEN", "STALE_SNAPSHOT"}:
            blockers.append(f"session {session_id}: terminal evidence is {status}")
    lint_requested = bool(config_path and config_path.exists())
    if lint_requested:
        schema, dir_to_type, dependency_rules = _load_config(config_path)
        findings = run_all_checks(wiki_dir, schema, dir_to_type, dependency_rules)
        blockers.extend(f"wiki lint: {item.message}" for item in findings if item.severity == LintSeverity.ERROR)
        warnings.extend(f"wiki lint: {item.message}" for item in findings if item.severity == LintSeverity.WARNING)

    verdict = "BLOCKED" if blockers else "WARNING" if warnings else "GREEN"
    lines = [
        f"# AgentOps Release Check - {version}",
        "",
        f"- Verdict: {verdict}",
        f"- Backlog items: {len(items)}",
        f"- Sessions: {len(sessions)}",
        f"- Status counts: {dict(sorted(counts.items()))}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("_(none)_")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("_(none)_")
    lines.extend([
        "",
        "## Evidence",
        "",
        "- Backlog validation",
        "- Handoff validation",
        "- Session summaries",
        "- Alpha-Wiki structural lint" if lint_requested else "- Alpha-Wiki structural lint not requested",
    ])
    return verdict, "\n".join(lines).rstrip() + "\n", blockers, warnings


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--version", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=Path(".alpha-wiki/config.yaml"))
@click.option("--write", "write_file", is_flag=True)
def cli(wiki_dir: Path, version: str, config_path: Path, write_file: bool) -> None:
    verdict, report, blockers, warnings = release_check_report(wiki_dir, version, config_path)
    if write_file:
        load_entity(wiki_dir, "orchestrator", "orchestrator")
        path = write_entity(
            wiki_dir,
            "release",
            version,
            {
                "title": f"Release {version}",
                "status": verdict,
                "version": version,
                "governance_status": verdict,
                "blockers": blockers,
                "warnings": warnings,
                "evidence": ["backlog validation", "handoff validation", "session summaries", "wiki lint"],
                "belongs_to": link_for("orchestrator", "orchestrator"),
            },
            report,
            overwrite=True,
        )
        append_wiki_log(wiki_dir, "release-check", f"version={version} verdict={verdict}")
        update_orchestrator(wiki_dir, governance_status=verdict)
        click.echo(f"wrote {path}")
    click.echo(report)
    if verdict == "BLOCKED":
        raise SystemExit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
