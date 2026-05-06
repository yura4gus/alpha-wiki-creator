"""Render Alpha-Wiki markdown pages to a small static HTML bundle."""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import click

from tools._models import Page
from tools.render_dot import write_dot
from tools.render_mermaid import write_mermaid
from tools.wiki_engine import rebuild_context_brief, rebuild_edges, rebuild_open_questions, scan_wiki


def render_html(wiki_dir: Path, out_dir: Path | None = None) -> Path:
    target = out_dir or wiki_dir / "render" / "html"
    if target.resolve() == wiki_dir.resolve():
        raise ValueError("HTML output directory must not be the wiki source directory")
    if out_dir is None and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    graph_dir = target / "graph"
    graph_dir.mkdir(exist_ok=True)
    write_mermaid(wiki_dir, out=graph_dir / "graph.mmd")
    write_dot(wiki_dir, out=graph_dir / "graph.dot")
    rebuild_edges(wiki_dir)
    rebuild_context_brief(wiki_dir)
    rebuild_open_questions(wiki_dir)

    pages = sorted(scan_wiki(wiki_dir), key=lambda page: page.slug)
    hrefs = {page.slug: _page_href(wiki_dir, page) for page in pages}
    for page in pages:
        _write_page(wiki_dir, target, page, hrefs)
    _write_index(wiki_dir, target, pages)
    _write_style(target)
    return target


def _write_index(wiki_dir: Path, out_dir: Path, pages: list[Page]) -> None:
    rows = "\n".join(
        f'<li><a href="{_page_href(wiki_dir, page)}">{html.escape(page.title)}</a> '
        f'<code>{html.escape(page.slug)}</code> '
        f'<span>{html.escape(str(page.frontmatter.get("status", "unknown")))}</span></li>'
        for page in pages
    )
    body = f"""
<h1>Alpha-Wiki Export</h1>
<p class="muted">Static read-only export. Markdown remains the source of truth.</p>
<nav>
  <a href="graph/graph.mmd">Mermaid graph</a>
  <a href="graph/graph.dot">DOT graph</a>
</nav>
<h2>Pages</h2>
<ul class="page-list">
{rows}
</ul>
"""
    (out_dir / "index.html").write_text(_layout("Alpha-Wiki Export", body))


def _write_page(wiki_dir: Path, out_dir: Path, page: Page, hrefs: dict[str, str]) -> None:
    rel = Path(page.path).relative_to(wiki_dir).with_suffix(".html")
    target = out_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{_link_wikilinks(html.escape(str(value)), target, out_dir, hrefs)}</td></tr>"
        for key, value in sorted(page.frontmatter.items())
    )
    body = f"""
<p><a href="{_relative_back(target, out_dir)}index.html">Back to index</a></p>
<h1>{html.escape(page.title)}</h1>
<table class="frontmatter">
{frontmatter}
</table>
<main>
{_markdown(page.body, target, out_dir, hrefs)}
</main>
"""
    target.write_text(_layout(page.title, body, depth=len(rel.parts) - 1))


def _layout(title: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
  <div class="shell">
{body}
  </div>
</body>
</html>
"""


def _write_style(out_dir: Path) -> None:
    (out_dir / "style.css").write_text("""body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #111827;
  background: #f8fafc;
}
.shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}
a { color: #1d4ed8; }
code {
  background: #e5e7eb;
  border-radius: 4px;
  padding: 1px 4px;
}
pre {
  overflow: auto;
  background: #111827;
  color: #f9fafb;
  border-radius: 8px;
  padding: 14px;
}
table.frontmatter {
  border-collapse: collapse;
  width: 100%;
  margin: 18px 0 26px;
  background: #ffffff;
}
.frontmatter th,
.frontmatter td {
  border: 1px solid #d1d5db;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}
.frontmatter th {
  width: 180px;
  background: #f3f4f6;
}
nav {
  display: flex;
  gap: 14px;
  margin: 18px 0;
}
.muted { color: #6b7280; }
.page-list li { margin: 8px 0; }
.missing-link { color: #b91c1c; }
""")


def _markdown(text: str, target: Path, out_dir: Path, hrefs: dict[str, str]) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_code = False
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<pre><code>" if not in_code else "</code></pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("#"):
            if in_list:
                out.append("</ul>")
                in_list = False
            level = min(len(line) - len(line.lstrip("#")), 6)
            label = line[level:].strip()
            out.append(f"<h{level}>{_inline(label, target, out_dir, hrefs)}</h{level}>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[2:].strip(), target, out_dir, hrefs)}</li>")
        elif not line:
            if in_list:
                out.append("</ul>")
                in_list = False
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{_inline(line, target, out_dir, hrefs)}</p>")
    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def _inline(text: str, target: Path, out_dir: Path, hrefs: dict[str, str]) -> str:
    return _link_wikilinks(html.escape(text), target, out_dir, hrefs)


def _link_wikilinks(text: str, target: Path, out_dir: Path, hrefs: dict[str, str]) -> str:
    return re.sub(r"\[\[([^]|]+)(?:\|([^]]+))?\]\]", lambda match: _wikilink_repl(match, target, out_dir, hrefs), text)


def _wikilink_repl(match: re.Match, target: Path, out_dir: Path, hrefs: dict[str, str]) -> str:
    slug = match.group(1)
    label = match.group(2) or slug
    href = hrefs.get(slug)
    if href:
        prefix = _relative_back(target, out_dir)
        return f'<a href="{prefix}{html.escape(href)}">[[{html.escape(label)}]]</a>'
    return f'<span class="missing-link">[[{html.escape(label)}]]</span>'


def _page_href(wiki_dir: Path, page: Page) -> str:
    return str(Path(page.path).relative_to(wiki_dir).with_suffix(".html"))


def _relative_back(target: Path, out_dir: Path) -> str:
    depth = len(target.relative_to(out_dir).parts) - 1
    return "../" * depth


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--out", type=click.Path(path_type=Path), help="Output directory. Defaults to <wiki-dir>/render/html.")
def cli(wiki_dir: Path, out: Path | None) -> None:
    target = render_html(wiki_dir, out_dir=out)
    click.echo(f"wrote {target}")


if __name__ == "__main__":
    cli()
