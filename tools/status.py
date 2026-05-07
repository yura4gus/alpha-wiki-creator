"""Wiki health report — recent activity, staleness, gaps, schema-evolution log."""
from __future__ import annotations
from datetime import date as _date
from pathlib import Path

import click

from tools.wiki_engine import (
    cluster_gaps,
    page_role,
    read_edges,
    rebuild_context_brief,
    rebuild_edges,
    rebuild_open_questions,
    scan_wiki,
)

STALE_THRESHOLD_DAYS = 30
PROVENANCE_KEYS = {"source", "sources", "derived_from", "distilled_from", "evidence", "evidence_strength"}
CLUSTER_EDGE_RELATIONS = {"belongs_to", "owned_by", "service", "defined_in"}

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
    cluster_health = _cluster_health(wiki_dir, pages, edges, cluster_gap_count)
    provenance = _provenance_health(pages)
    open_question_followup = _open_question_followup(open_q_path)
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
    parts.extend([
        "\n## Cluster Health",
        f"- Service clusters: {cluster_health['service_clusters']}",
        f"- Cluster link gaps: {cluster_health['cluster_gap_count']}",
        f"- Isolated service nodes: {cluster_health['isolated_services']}",
        f"- Mixed-role clusters: {cluster_health['mixed_role_clusters']}",
        "\n## Provenance",
        f"- Pages with provenance: {provenance['with_provenance']}/{provenance['total_pages']}",
        f"- Provenance score: {provenance['score']}%",
    ])
    if provenance["missing"]:
        parts.extend(f"- Missing provenance: [[{slug}]]" for slug in provenance["missing"][:10])
        if len(provenance["missing"]) > 10:
            parts.append(f"_... and {len(provenance['missing']) - 10} more_")
    parts.extend([
        "\n## Freshness",
        f"- Stale pages: {len(stale)}",
        f"- Pages without date_updated: {len(no_date)}",
        "\n## Open Question Follow-Up",
        f"- Open questions: {open_q_count}",
        f"- Missing owner/timebox: {open_question_followup['missing_owner_or_timebox']}",
    ])
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
    parts.append("\n## Suggested Next Actions")
    parts.extend(_suggested_next_actions(gap_items, cluster_health, provenance, open_question_followup))
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


def _cluster_health(wiki_dir: Path, pages, edges, cluster_gap_count: int) -> dict[str, int]:
    service_slugs = {page.slug for page in pages if page_role(wiki_dir, page) == "service"}
    role_by_slug = {page.slug: page_role(wiki_dir, page) for page in pages}
    cluster_roles: dict[str, set[str]] = {slug: {"service"} for slug in service_slugs}
    for edge in edges:
        if edge.relation not in CLUSTER_EDGE_RELATIONS or edge.target not in service_slugs:
            continue
        cluster_roles.setdefault(edge.target, {"service"}).add(role_by_slug.get(edge.source, "other"))
    attached_services = {slug for slug, roles in cluster_roles.items() if len(roles) > 1}
    return {
        "service_clusters": len(attached_services),
        "cluster_gap_count": cluster_gap_count,
        "isolated_services": len(service_slugs - attached_services),
        "mixed_role_clusters": sum(1 for roles in cluster_roles.values() if len(roles) >= 3),
    }


def _provenance_health(pages) -> dict[str, object]:
    total = len(pages)
    with_provenance = []
    missing = []
    for page in pages:
        has_frontmatter_provenance = any(key in page.frontmatter and page.frontmatter.get(key) for key in PROVENANCE_KEYS)
        has_body_provenance = "source:" in page.body.lower() or "provenance:" in page.body.lower()
        if has_frontmatter_provenance or has_body_provenance:
            with_provenance.append(page.slug)
        else:
            missing.append(page.slug)
    score = 100 if total == 0 else round(len(with_provenance) * 100 / total)
    return {
        "total_pages": total,
        "with_provenance": len(with_provenance),
        "score": score,
        "missing": missing,
    }


def _open_question_followup(open_q_path: Path) -> dict[str, int]:
    if not open_q_path.exists():
        return {"missing_owner_or_timebox": 0}
    missing = 0
    for line in open_q_path.read_text().splitlines():
        if not line.startswith("- "):
            continue
        lower = line.lower()
        if "owner:" not in lower or ("due:" not in lower and "timebox:" not in lower):
            missing += 1
    return {"missing_owner_or_timebox": missing}


def _suggested_next_actions(
    gap_items: list[str],
    cluster_health: dict[str, int],
    provenance: dict[str, object],
    open_question_followup: dict[str, int],
) -> list[str]:
    actions: list[str] = []
    if any(item.startswith("Content gap") for item in gap_items):
        actions.append("- Run `/alpha-wiki:ingest <path>` on the first durable source.")
    if cluster_health["cluster_gap_count"] or cluster_health["isolated_services"]:
        actions.append("- Add typed cluster links (`belongs_to`, `service`, `affects`, `implements`) before trusting graph layout.")
    if provenance["missing"]:
        actions.append("- Add `source`, `sources`, `derived_from`, or body provenance to unsupported pages.")
    if open_question_followup["missing_owner_or_timebox"]:
        actions.append("- Assign owner and due/timebox metadata to open questions.")
    if any(item.startswith("Freshness gap") or item.startswith("Metadata gap") for item in gap_items):
        actions.append("- Refresh stale pages and add `date_updated` during the next ingest/review pass.")
    if not actions:
        actions.append("- No immediate maintenance action required.")
    return actions


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--out", type=click.Path(path_type=Path), help="Optional report output path.")
def cli(wiki_dir: Path, out: Path | None) -> None:
    report = status_report(wiki_dir)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        click.echo(f"wrote {out}")
        return
    click.echo(report)


if __name__ == "__main__":
    cli()
