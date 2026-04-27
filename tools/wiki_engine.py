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


import json

# Frontmatter keys that produce typed edges (relation = key name)
EDGE_KEYS = {
    "depends_on", "dependents", "affects", "implements", "consumes",
    "service", "consumers", "supersedes", "superseded_by", "supports",
    "extends", "tested_by", "contradicts", "inspired_by", "addresses_gap",
    "derived_from", "invalidates", "target_module", "defined_in",
    "belongs_to", "distilled_from", "tracks_metric", "persona",
}


def rebuild_edges(wiki_dir: Path) -> list[Edge]:
    edges: list[Edge] = []
    for page in scan_wiki(wiki_dir):
        for key, value in page.frontmatter.items():
            if key not in EDGE_KEYS:
                continue
            for target in _coerce_targets(value):
                edges.append(Edge(source=page.slug, target=target, relation=key))
    out_path = wiki_dir / "graph" / "edges.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(e.to_jsonl() for e in edges) + ("\n" if edges else ""))
    return edges


def read_edges(path: Path) -> list[Edge]:
    if not path.exists():
        return []
    return [Edge(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def _coerce_targets(value) -> list[str]:
    if isinstance(value, str):
        return [s for s in WIKILINK_RE.findall(value)] or ([value] if not value.startswith("[") else [])
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            out.extend(_coerce_targets(v))
        return out
    return []


def add_edge(wiki_dir: Path, source: str, target: str, relation: str, bidirectional: bool = False) -> None:
    """Adds a forward link to source's frontmatter; if bidirectional, also writes reverse on target."""
    src_page = _find_page(wiki_dir, source)
    if src_page is None:
        raise FileNotFoundError(f"page not found: {source}")
    _add_to_frontmatter_list(src_page, relation, f"[[{target}]]")
    if bidirectional:
        reverse_relation = _reverse_of(relation)
        if reverse_relation is None:
            return
        tgt_page = _find_page(wiki_dir, target)
        if tgt_page is None:
            _create_stub(wiki_dir, target)
            tgt_page = _find_page(wiki_dir, target)
        _add_to_frontmatter_list(tgt_page, reverse_relation, f"[[{source}]]")


REVERSE_OF = {
    "depends_on": "dependents",
    "dependents": "depends_on",
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
    "service": "_provides",  # special: writes section, not frontmatter
    "consumes": "consumers",
    "consumers": "consumes",
    "implements": "_specs",  # special: writes section
}


def _reverse_of(relation: str) -> str | None:
    return REVERSE_OF.get(relation)


def _find_page(wiki_dir: Path, slug: str) -> Path | None:
    for p in wiki_dir.rglob("*.md"):
        if "graph" in p.parts:
            continue
        page = parse_page(p)
        if page.slug == slug:
            return p
    return None


def _add_to_frontmatter_list(page_path: Path, key: str, value: str) -> None:
    text = page_path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        # No frontmatter — add minimal
        new = f"---\n{key}:\n  - {value}\n---\n" + text
        page_path.write_text(new)
        return
    fm = yaml.safe_load(m.group(1)) or {}
    existing = fm.get(key, [])
    if isinstance(existing, str):
        existing = [existing]
    if value not in existing:
        existing.append(value)
    fm[key] = existing
    new_fm = yaml.safe_dump(fm, sort_keys=False).rstrip()
    page_path.write_text(f"---\n{new_fm}\n---\n" + text[m.end():])


def _create_stub(wiki_dir: Path, slug: str) -> None:
    stub_dir = wiki_dir / "_stubs"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_path = stub_dir / f"{slug}.md"
    stub_path.write_text(f"---\ntitle: {slug}\nslug: {slug}\nstatus: stub\n---\n# {slug}\nTODO: fill via /wiki-ingest\n")
