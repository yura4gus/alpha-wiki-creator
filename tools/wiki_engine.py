"""Wiki engine parsing helpers."""
from __future__ import annotations

import re
from pathlib import Path
import yaml

from tools._models import Page, Edge

WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_page(path: Path) -> Page:
    """Parse a markdown page with frontmatter.

    Extracts YAML frontmatter, body content, and forward wikilinks.
    Wikilinks are extracted from both body and frontmatter (recursively).
    """
    text = path.read_text()
    fm: dict = {}
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        fm = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    slug = fm.get("slug") or path.stem
    title = fm.get("title") or slug
    forward = sorted(set(extract_wikilinks(body) + _wikilinks_from_frontmatter(fm)))
    return Page(
        slug=slug,
        title=title,
        path=str(path),
        frontmatter=fm,
        body=body,
        forward_links=forward,
    )


def extract_wikilinks(text: str) -> list[str]:
    """Extract wikilink targets from text.

    Finds all [[target]] and [[target|alias]] patterns,
    returning the target (not the alias).
    """
    return WIKILINK_RE.findall(text)


def _wikilinks_from_frontmatter(fm: dict) -> list[str]:
    """Recursively extract wikilinks from frontmatter dict."""
    out: list[str] = []

    def visit(v):
        if isinstance(v, str):
            out.extend(WIKILINK_RE.findall(v))
        elif isinstance(v, list):
            for x in v:
                visit(x)
        elif isinstance(v, dict):
            for x in v.values():
                visit(x)

    visit(fm)
    return out


def scan_wiki(wiki_dir: Path) -> list[Page]:
    """Scan a wiki directory and parse all markdown pages.

    Excludes:
    - Files in graph/ subdirectories
    - index.md and log.md files
    """
    return [
        parse_page(p)
        for p in wiki_dir.rglob("*.md")
        if "graph" not in p.parts and p.name not in ("index.md", "log.md")
    ]
