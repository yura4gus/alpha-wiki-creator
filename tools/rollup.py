"""Period rollup generation for wiki activity."""
from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path

import click

from tools.wiki_engine import scan_wiki

LOG_ENTRY_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*(.*)$")


def rollup_report(wiki_dir: Path, period: str = "month", today: _date | None = None) -> tuple[str, str]:
    """Return `(label, markdown)` for a week or month rollup."""
    today = today or _date.today()
    label = _period_label(period, today)
    log_entries = _log_entries_for_period(wiki_dir, period, today)
    updated_pages = _pages_updated_for_period(wiki_dir, period, today)

    parts = [
        f"# Wiki Rollup - {label}",
        "",
        f"_Generated: {today.isoformat()}_",
        "",
        "## Activity",
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

    parts.extend([
        "",
        "## Follow-ups",
        "",
        "- Review open questions and stale pages before the next rollup.",
        "- Run `/alpha-wiki:review` if this rollup will be shared externally.",
    ])
    return label, "\n".join(parts).rstrip() + "\n"


def write_rollup(wiki_dir: Path, period: str = "month", today: _date | None = None) -> Path:
    label, report = rollup_report(wiki_dir, period, today)
    out_dir = wiki_dir / "rollups"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{label}.md"
    out.write_text(report)
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


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--period", type=click.Choice(["week", "month"]), default="month", show_default=True)
@click.option("--write", "write_file", is_flag=True, help="Write to <wiki-dir>/rollups/<period>.md.")
def cli(wiki_dir: Path, period: str, write_file: bool) -> None:
    if write_file:
        out = write_rollup(wiki_dir, period)
        click.echo(f"wrote {out}")
        return
    _, report = rollup_report(wiki_dir, period)
    click.echo(report)


if __name__ == "__main__":
    cli()
