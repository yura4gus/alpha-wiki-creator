"""Wiki health report — recent activity, staleness, gaps, schema-evolution log."""
from __future__ import annotations
import re
from datetime import date as _date, timedelta
from pathlib import Path
from tools.wiki_engine import scan_wiki, read_edges, rebuild_open_questions

STALE_THRESHOLD_DAYS = 30

def status_report(wiki_dir: Path) -> str:
    pages = scan_wiki(wiki_dir)
    log_text = (wiki_dir / "log.md").read_text() if (wiki_dir / "log.md").exists() else ""
    edges_path = wiki_dir / "graph" / "edges.jsonl"
    edges = read_edges(edges_path) if edges_path.exists() else []

    # Recent activity (last 10 log entries)
    log_lines = [ln for ln in log_text.splitlines() if ln.startswith("## [")]
    recent = log_lines[-10:]

    # Schema-evolution events
    schema_events = [ln for ln in log_lines if "schema-change" in ln]

    # Stale pages
    today = _date.today()
    stale: list[tuple[str, str]] = []
    no_date: list[str] = []
    for p in pages:
        du = p.frontmatter.get("date_updated")
        if du:
            try:
                d = _date.fromisoformat(str(du))
                if (today - d).days > STALE_THRESHOLD_DAYS:
                    stale.append((p.slug, str(du)))
            except ValueError:
                no_date.append(p.slug)
        else:
            no_date.append(p.slug)

    # Open questions
    open_q_path = wiki_dir / "graph" / "open_questions.md"
    open_q_count = 0
    if open_q_path.exists():
        open_q_count = sum(1 for ln in open_q_path.read_text().splitlines() if ln.startswith("- "))

    # Build report
    parts = [
        f"# Wiki Status Report",
        f"\n_Generated: {today.isoformat()}_\n",
        f"## Stats",
        f"- Pages: {len(pages)}",
        f"- Edges: {len(edges)}",
        f"- Open questions: {open_q_count}",
        f"- Recent log entries: {len(log_lines)}",
        f"\n## Recent activity (last {len(recent)})",
    ]
    if recent:
        parts.extend(f"- {ln[3:]}" for ln in recent)
    else:
        parts.append("_(none)_")
    if schema_events:
        parts.append(f"\n## Schema evolution ({len(schema_events)})")
        parts.extend(f"- {ln[3:]}" for ln in schema_events)
    if stale:
        parts.append(f"\n## Stale pages (> {STALE_THRESHOLD_DAYS} days)")
        parts.extend(f"- [[{slug}]] — last updated {du}" for slug, du in stale)
    if no_date:
        parts.append(f"\n## Pages without date_updated ({len(no_date)})")
        parts.extend(f"- [[{slug}]]" for slug in no_date[:20])
        if len(no_date) > 20:
            parts.append(f"_… and {len(no_date) - 20} more_")
    parts.append(f"\n_Run `/wiki:lint --suggest` for structural gaps._")
    return "\n".join(parts) + "\n"
