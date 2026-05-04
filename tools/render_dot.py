"""Render Alpha-Wiki graph to Graphviz DOT with typed clusters and role colors."""
from __future__ import annotations

import re
from pathlib import Path

import click

from tools._models import Edge, Page
from tools.render_mermaid import CLUSTER_RELATIONS
from tools.wiki_engine import page_role, read_edges, rebuild_edges, scan_wiki

ROLE_COLORS = {
    "service": "#E94B43",
    "module": "#16A34A",
    "module-root": "#16A34A",
    "feature": "#2563EB",
    "document": "#111111",
    "contract": "#F97316",
    "other": "#E5E7EB",
}

FONT_COLORS = {
    "service": "#FFFFFF",
    "module": "#FFFFFF",
    "module-root": "#FFFFFF",
    "feature": "#FFFFFF",
    "document": "#FFFFFF",
    "contract": "#FFFFFF",
    "other": "#111111",
}


def render_dot(wiki_dir: Path) -> str:
    pages = scan_wiki(wiki_dir)
    page_by_slug = {page.slug: page for page in pages}
    edges = _current_edges(wiki_dir)
    clusters = _service_clusters(wiki_dir, pages, edges)
    assigned = {slug for members in clusters.values() for slug in members}

    lines = [
        "digraph AlphaWiki {",
        '  graph [rankdir="LR", compound="true"];',
        '  node [shape="box", style="filled,rounded", fontname="Arial"];',
        '  edge [fontname="Arial"];',
    ]

    for service_slug, members in sorted(clusters.items()):
        service_page = page_by_slug.get(service_slug)
        title = service_page.title if service_page else service_slug
        lines.append(f'  subgraph cluster_{_dot_id(service_slug)} {{')
        lines.append(f'    label="{_escape(title)} cluster";')
        lines.append('    color="#CBD5E1";')
        for slug in sorted(members):
            page = page_by_slug.get(slug)
            if page:
                lines.append(_node_line(wiki_dir, page, indent="    "))
        lines.append("  }")

    for page in sorted(pages, key=lambda item: item.slug):
        if page.slug not in assigned:
            lines.append(_node_line(wiki_dir, page, indent="  "))

    for edge in sorted(edges, key=lambda item: (item.source, item.target, item.relation)):
        lines.append(f'  "{_escape(edge.source)}" -> "{_escape(edge.target)}" [label="{_escape(edge.relation)}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def write_dot(wiki_dir: Path, out: Path | None = None) -> Path:
    target = out or wiki_dir / "graph" / "graph.dot"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dot(wiki_dir))
    return target


def _current_edges(wiki_dir: Path) -> list[Edge]:
    rebuild_edges(wiki_dir)
    return read_edges(wiki_dir / "graph" / "edges.jsonl")


def _service_clusters(wiki_dir: Path, pages: list[Page], edges: list[Edge]) -> dict[str, set[str]]:
    service_slugs = {page.slug for page in pages if page_role(wiki_dir, page) == "service"}
    clusters = {slug: {slug} for slug in service_slugs}
    for edge in edges:
        if edge.relation not in CLUSTER_RELATIONS or edge.target not in service_slugs:
            continue
        clusters.setdefault(edge.target, {edge.target}).add(edge.source)
    return {service: members for service, members in clusters.items() if len(members) > 1}


def _node_line(wiki_dir: Path, page: Page, indent: str) -> str:
    role = page_role(wiki_dir, page)
    fill = ROLE_COLORS.get(role, ROLE_COLORS["other"])
    font = FONT_COLORS.get(role, FONT_COLORS["other"])
    return f'{indent}"{_escape(page.slug)}" [label="{_escape(page.title)}", fillcolor="{fill}", fontcolor="{font}"];'


def _dot_id(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_]", "_", value)
    if not value or value[0].isdigit():
        value = f"n_{value}"
    return value


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', r"\"")


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--out", type=click.Path(path_type=Path), help="Output path. Defaults to <wiki-dir>/graph/graph.dot.")
def cli(wiki_dir: Path, out: Path | None) -> None:
    target = write_dot(wiki_dir, out=out)
    click.echo(f"wrote {target}")


if __name__ == "__main__":
    cli()
