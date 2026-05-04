"""Deterministic wiki search and query report. No embeddings."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click

from tools.wiki_engine import scan_wiki


@dataclass(frozen=True)
class SearchHit:
    slug: str
    title: str
    path: str
    score: int
    status: str
    citations: list[str]


def search_wiki(wiki_dir: Path, query: str, limit: int = 7) -> list[SearchHit]:
    terms = _terms(query)
    if not terms:
        return []
    hits: list[SearchHit] = []
    for page in scan_wiki(wiki_dir):
        path = Path(page.path)
        text = path.read_text()
        score = _score_page(page.slug, page.title, str(page.frontmatter), page.body, terms, query)
        if score <= 0:
            continue
        citations = _citations(wiki_dir, path, terms)
        hits.append(SearchHit(
            slug=page.slug,
            title=page.title,
            path=str(path.relative_to(wiki_dir)),
            score=score,
            status=str(page.frontmatter.get("status", "unknown")),
            citations=citations,
        ))
    return sorted(hits, key=lambda item: (-item.score, item.slug))[:limit]


def query_report(wiki_dir: Path, query: str, limit: int = 7) -> str:
    hits = search_wiki(wiki_dir, query, limit=limit)
    lines = [
        "# Wiki Query",
        "",
        f"- Question: {query}",
        f"- Retrieval: deterministic markdown search, no embeddings",
        "",
    ]
    if not hits:
        lines.extend([
            "## Short Answer",
            "",
            "No relevant wiki pages were found.",
            "",
            "## Suggested Next Action",
            "",
            "- Ingest or link durable source material before relying on this answer.",
        ])
        return "\n".join(lines) + "\n"

    lines.extend([
        "## Short Answer",
        "",
        f"Found {len(hits)} relevant page(s). Read the cited pages before making a decision.",
        "",
        "## Evidence",
        "",
    ])
    for hit in hits:
        lines.append(f"- [[{hit.slug}]] `{hit.path}` status={hit.status} score={hit.score}")
        for citation in hit.citations[:3]:
            lines.append(f"  - {citation}")
    truth_status = _truth_status(hits)
    lines.extend([
        "",
        "## Truth Status",
        "",
        f"- {truth_status}",
        "",
        "## Related Pages",
        "",
    ])
    lines.extend(f"- [[{hit.slug}]]" for hit in hits)
    lines.extend([
        "",
        "## Suggested Next Action",
        "",
        "- Use `/alpha-wiki:review` if this answer affects a decision or release.",
    ])
    return "\n".join(lines) + "\n"


def _score_page(slug: str, title: str, frontmatter: str, body: str, terms: list[str], query: str) -> int:
    slug_l = slug.lower()
    title_l = title.lower()
    frontmatter_l = frontmatter.lower()
    body_l = body.lower()
    query_l = query.lower()
    score = 0
    if query_l and query_l in title_l:
        score += 20
    if query_l and query_l in body_l:
        score += 10
    for term in terms:
        if term in slug_l:
            score += 12
        if term in title_l:
            score += 10
        if term in frontmatter_l:
            score += 4
        score += min(body_l.count(term), 5)
    return score


def _citations(wiki_dir: Path, path: Path, terms: list[str]) -> list[str]:
    citations: list[str] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        lower = line.lower()
        if any(term in lower for term in terms):
            rel = path.relative_to(wiki_dir)
            citations.append(f"`{rel}:{number}` {line.strip()[:160]}")
        if len(citations) >= 5:
            break
    return citations or [f"`{path.relative_to(wiki_dir)}:1` page matched metadata"]


def _terms(query: str) -> list[str]:
    return [term for term in re.findall(r"[a-zA-Z0-9_-]+", query.lower()) if len(term) > 1]


def _truth_status(hits: list[SearchHit]) -> str:
    statuses = {hit.status.lower() for hit in hits}
    if statuses & {"accepted", "stable"}:
        return "accepted: at least one accepted/stable page matched."
    if statuses & {"risk", "blocked"}:
        return "risk: relevant pages indicate risk or blocked status."
    if statuses & {"draft", "building", "unknown"}:
        return "assumption: evidence exists but is draft/building/unknown."
    return "open: evidence needs human review."


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--query", "query_text", required=True)
@click.option("--limit", type=int, default=7, show_default=True)
def cli(wiki_dir: Path, query_text: str, limit: int) -> None:
    click.echo(query_report(wiki_dir, query_text, limit=limit))


if __name__ == "__main__":
    cli()
