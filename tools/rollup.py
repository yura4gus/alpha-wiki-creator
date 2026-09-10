"""Period rollup generation for wiki activity."""
from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path

import click
import yaml

from tools.wiki_engine import scan_wiki

LOG_ENTRY_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*(.*)$")


def rollup_report(
    wiki_dir: Path,
    period: str = "month",
    today: _date | None = None,
    scope: str = "wiki",
) -> tuple[str, str]:
    """Return `(label, markdown)` for a week or month rollup."""
    today = today or _date.today()
    label = _period_label(period, today)
    if scope not in {"wiki", "agentops", "all"}:
        raise ValueError(f"unsupported scope: {scope}")
    log_entries = _log_entries_for_period(wiki_dir, period, today)
    if scope == "agentops":
        log_entries = [entry for entry in log_entries if "agentops-" in entry]
    updated_pages = _pages_updated_for_period(wiki_dir, period, today) if scope in {"wiki", "all"} else []

    title = "AgentOps Rollup" if scope == "agentops" else "Alpha-Wiki and AgentOps Rollup" if scope == "all" else "Wiki Rollup"
    parts = [
        f"# {title} - {label}",
        "",
        f"_Generated: {today.isoformat()}_",
        "",
        f"## Activity ({scope})",
        "",
    ]
    if log_entries:
        parts.extend(f"- {entry}" for entry in log_entries)
    else:
        parts.append("_(no log entries for this period)_")

    parts.extend(["", "## Updated Pages", ""])
    if updated_pages:
        parts.extend(f"- [[{slug}]] - {updated}" for slug, updated in updated_pages)
    else:
        parts.append("_(no pages with date_updated in this period)_")

    if scope in {"agentops", "all"}:
        parts.extend(["", "## AgentOps Sessions", ""])
        sessions = _agentops_entities_for_period(wiki_dir, "sessions", period, today)
        parts.extend(_agentops_lines(sessions) or ["_(none)_"])
        parts.extend(["", "## AgentOps Handoffs", ""])
        handoffs = _agentops_entities_for_period(wiki_dir, "handoffs", period, today)
        parts.extend(_agentops_lines(handoffs) or ["_(none)_"])
        parts.extend(["", "## AgentOps Backlog Updates", ""])
        backlog = _agentops_entities_for_period(wiki_dir, "backlog", period, today)
        parts.extend(_agentops_lines(backlog) or ["_(none)_"])

    parts.extend([
        "",
        "## Follow-ups",
        "",
        "- Review open questions and stale pages before the next rollup.",
        "- Run `/alpha-wiki:review` if this rollup will be shared externally.",
    ])
    return label, "\n".join(parts).rstrip() + "\n"


def write_rollup(
    wiki_dir: Path,
    period: str = "month",
    today: _date | None = None,
    scope: str = "wiki",
) -> Path:
    if scope == "agentops":
        from tools._agentops import load_entity

        load_entity(wiki_dir, "orchestrator", "orchestrator")
    label, report = rollup_report(wiki_dir, period, today, scope)
    out_dir = wiki_dir / "agentops" / "rollups" if scope == "agentops" else wiki_dir / "rollups"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{label}.md"
    if scope == "agentops":
        frontmatter = {
            "title": f"AgentOps Rollup {label}",
            "slug": f"agentops-rollup-{label}",
            "agentops_type": "rollup",
            "status": "GENERATED",
            "date_updated": (today or _date.today()).isoformat(),
            "belongs_to": "[[agentops-orchestrator-orchestrator]]",
        }
        report = f"---\n{yaml.safe_dump(frontmatter, sort_keys=False).rstrip()}\n---\n{report}"
    out.write_text(report)
    if scope == "agentops":
        from tools._agentops import refresh_index

        refresh_index(wiki_dir)
    return out


def _period_label(period: str, today: _date) -> str:
    if period == "week":
        year, week, _ = today.isocalendar()
        return f"{year}-W{week:02d}"
    if period == "month":
        return today.strftime("%Y-%m")
    raise ValueError(f"unsupported period: {period}")


def _date_in_period(value: str, period: str, today: _date) -> bool:
    try:
        parsed = _date.fromisoformat(value)
    except ValueError:
        return False
    if period == "month":
        return parsed.year == today.year and parsed.month == today.month
    if period == "week":
        return parsed.isocalendar()[:2] == today.isocalendar()[:2]
    raise ValueError(f"unsupported period: {period}")


def _log_entries_for_period(wiki_dir: Path, period: str, today: _date) -> list[str]:
    log_path = wiki_dir / "log.md"
    if not log_path.exists():
        return []
    entries: list[str] = []
    for line in log_path.read_text().splitlines():
        match = LOG_ENTRY_RE.match(line)
        if not match:
            continue
        when, rest = match.groups()
        if _date_in_period(when, period, today):
            entries.append(f"{when} {rest.strip()}")
    return entries


def _pages_updated_for_period(wiki_dir: Path, period: str, today: _date) -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    for page in scan_wiki(wiki_dir):
        updated = page.frontmatter.get("date_updated")
        if updated and _date_in_period(str(updated), period, today):
            pages.append((page.slug, str(updated)))
    return sorted(pages, key=lambda item: (item[1], item[0]), reverse=True)


def _agentops_entities_for_period(
    wiki_dir: Path,
    directory: str,
    period: str,
    today: _date,
) -> list[tuple[str, str, str, str]]:
    from tools.wiki_engine import parse_page

    root = wiki_dir / "agentops" / directory
    if not root.exists():
        return []
    entities: list[tuple[str, str, str, str]] = []
    for path in sorted(root.glob("*.md")):
        page = parse_page(path)
        updated = str(page.frontmatter.get("date_updated", ""))
        if updated and _date_in_period(updated, period, today):
            entities.append(
                (
                    page.slug,
                    page.title,
                    str(page.frontmatter.get("status", "UNKNOWN")),
                    updated,
                )
            )
    return sorted(entities, key=lambda item: (item[3], item[0]), reverse=True)


def _agentops_lines(entities: list[tuple[str, str, str, str]]) -> list[str]:
    return [f"- [[{slug}]] - {title} [{status}] ({updated})" for slug, title, status, updated in entities]


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--period", type=click.Choice(["week", "month"]), default="month", show_default=True)
@click.option("--scope", type=click.Choice(["wiki", "agentops", "all"]), default="wiki", show_default=True)
@click.option("--write", "write_file", is_flag=True, help="Write to <wiki-dir>/rollups/<period>.md.")
def cli(wiki_dir: Path, period: str, scope: str, write_file: bool) -> None:
    if write_file:
        out = write_rollup(wiki_dir, period, scope=scope)
        click.echo(f"wrote {out}")
        return
    _, report = rollup_report(wiki_dir, period, scope=scope)
    click.echo(report)


if __name__ == "__main__":
    cli()
