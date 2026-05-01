"""Wiki health report — recent activity, staleness, gaps, schema-evolution log."""
from __future__ import annotations
from datetime import date as _date
from pathlib import Path
from tools.wiki_engine import (
    cluster_gaps,
    read_edges,
    rebuild_context_brief,
    rebuild_edges,
    rebuild_open_questions,
    scan_wiki,
)

STALE_THRESHOLD_DAYS = 30

def status_report(wiki_dir: Path) -> str:
    rebuild_edges(wiki_dir)
    rebuild_context_brief(wiki_dir)
    rebuild_open_questions(wiki_dir)

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

    cluster_gap_count = sum(len(cluster_gaps(wiki_dir, page)) for page in pages)
    gap_items = _gap_check(
        pages,
        edges,
        open_q_count,
        len(log_lines),
        len(stale),
        len(no_date),
        cluster_gap_count,
    )

    # Build report
    parts = [
        f"# Wiki Status Report",
        f"\n_Generated: {today.isoformat()}_\n",
        f"## Status Summary",
        f"- Pages: {len(pages)}",
        f"- Edges: {len(edges)}",
        f"- Open questions: {open_q_count}",
        f"- Recent log entries: {len(log_lines)}",
        f"- Gap check: {'clear' if not gap_items else str(len(gap_items)) + ' gap(s)'}",
        f"\n## Gap Check",
    ]
    if gap_items:
        parts.extend(f"- {item}" for item in gap_items)
    else:
        parts.append("- No cross-cutting gaps detected.")
    parts.append(
        f"\n## Recent activity (last {len(recent)})",
    )
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
    parts.append(f"\n_Run `/alpha-wiki:lint --suggest` for structural gaps._")
    return "\n".join(parts) + "\n"


def _gap_check(
    pages,
    edges,
    open_q_count: int,
    log_count: int,
    stale_count: int,
    no_date_count: int,
    cluster_gap_count: int,
) -> list[str]:
    """Return cross-cutting health gaps, not per-file lint findings."""
    gaps: list[str] = []
    page_count = len(pages)
    dirs = {Path(p.path).parent.name for p in pages}

    if page_count == 0:
        gaps.append("Content gap: no wiki pages exist yet; ingest first durable source.")
        return gaps
    if page_count > 1 and not edges:
        gaps.append("Graph gap: multiple pages exist but no typed edges were generated.")
    if log_count == 0:
        gaps.append("Process gap: no log entries; recent wiki changes are not auditable.")
    if open_q_count:
        gaps.append(f"Decision gap: {open_q_count} open question(s) need owner or next action.")
    if cluster_gap_count:
        gaps.append(f"Cluster gap: {cluster_gap_count} page cluster link issue(s) need typed ownership links.")
    if stale_count:
        gaps.append(f"Freshness gap: {stale_count} page(s) are older than {STALE_THRESHOLD_DAYS} days.")
    if no_date_count:
        gaps.append(f"Metadata gap: {no_date_count} page(s) have no date_updated.")
    if not dirs.intersection({"decisions", "specs", "contracts", "features", "claims", "papers"}):
        gaps.append("Coverage gap: no decision/spec/contract/feature/claim evidence pages detected.")
    return gaps
