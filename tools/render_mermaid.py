"""Render Alpha-Wiki graph to Mermaid with typed clusters and role colors."""
from __future__ import annotations

import re
from pathlib import Path

import click

from tools._models import Edge, Page
from tools.wiki_engine import page_role, read_edges, rebuild_edges, scan_wiki

CLUSTER_RELATIONS = {"belongs_to", "owned_by", "service", "defined_in"}

ROLE_CLASS = {
    "service": "service",
    "module": "module",
    "module-root": "module",
    "feature": "feature",
    "document": "document",
    "contract": "contract",
}

CLASS_DEFS = {
    "service": "fill:#E94B43,stroke:#7f1d1d,color:#ffffff",
    "module": "fill:#16A34A,stroke:#14532d,color:#ffffff",
    "feature": "fill:#2563EB,stroke:#1e3a8a,color:#ffffff",
    "document": "fill:#111111,stroke:#525252,color:#ffffff",
    "contract": "fill:#F97316,stroke:#9a3412,color:#ffffff",
    "other": "fill:#E5E7EB,stroke:#6B7280,color:#111111",
}


def render_mermaid(wiki_dir: Path) -> str:
    pages = scan_wiki(wiki_dir)
    page_by_slug = {page.slug: page for page in pages}
    edges = _current_edges(wiki_dir)
    clusters = _service_clusters(wiki_dir, pages, edges)

    assigned = {slug for members in clusters.values() for slug in members}
    lines = [
        "%% Alpha-Wiki graph export",
        "%% Clusters come from typed links; colors show node roles.",
        "flowchart LR",
    ]

    for service_slug, members in sorted(clusters.items()):
        service_page = page_by_slug.get(service_slug)
        title = service_page.title if service_page else service_slug
        lines.append(f'  subgraph {_node_id("cluster_" + service_slug)}["{_escape_label(title)} cluster"]')
        for slug in sorted(members):
            page = page_by_slug.get(slug)
            if page:
                lines.append(_node_line(wiki_dir, page, indent="    "))
        lines.append("  end")

    for page in sorted(pages, key=lambda item: item.slug):
        if page.slug not in assigned:
            lines.append(_node_line(wiki_dir, page, indent="  "))

    for edge in sorted(edges, key=lambda item: (item.source, item.target, item.relation)):
        lines.append(f'  {_node_id(edge.source)} --|"{_escape_label(edge.relation)}"| {_node_id(edge.target)}')

    for class_name, definition in CLASS_DEFS.items():
        lines.append(f"  classDef {class_name} {definition};")

    for page in sorted(pages, key=lambda item: item.slug):
        role_class = _role_class(wiki_dir, page)
        lines.append(f"  class {_node_id(page.slug)} {role_class};")

    return "\n".join(lines) + "\n"


def write_mermaid(wiki_dir: Path, out: Path | None = None) -> Path:
    target = out or wiki_dir / "graph" / "graph.mmd"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_mermaid(wiki_dir))
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
    return f'{indent}{_node_id(page.slug)}["{_escape_label(page.title)}"]'


def _node_id(slug: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_]", "_", slug)
    if not value or value[0].isdigit():
        value = f"n_{value}"
    return value


def _escape_label(value: str) -> str:
    return value.replace('"', r"\"")


def _role_class(wiki_dir: Path, page: Page) -> str:
    return ROLE_CLASS.get(page_role(wiki_dir, page), "other")


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--out", type=click.Path(path_type=Path), help="Output path. Defaults to <wiki-dir>/graph/graph.mmd.")
def cli(wiki_dir: Path, out: Path | None) -> None:
    target = write_mermaid(wiki_dir, out=out)
    click.echo(f"wrote {target}")


if __name__ == "__main__":
    cli()
