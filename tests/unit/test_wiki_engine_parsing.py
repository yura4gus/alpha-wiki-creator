"""Tests for wiki_engine parsing helpers."""
from pathlib import Path
import pytest
from tools.wiki_engine import parse_page, extract_wikilinks, scan_wiki


def test_parse_page_splits_frontmatter_and_body(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("---\ntitle: X\nslug: x\n---\n# X\nbody [[y]]\n")
    page = parse_page(p)
    assert page.frontmatter["title"] == "X"
    assert page.slug == "x"
    assert "body [[y]]" in page.body


def test_extract_wikilinks_finds_all():
    body = "see [[a]] and [[b/c]] not [[d]] yet [[e|alias]]"
    assert sorted(extract_wikilinks(body)) == ["a", "b/c", "d", "e"]


def test_scan_wiki_returns_pages(sample_wiki: Path):
    pages = scan_wiki(sample_wiki / "wiki")
    slugs = sorted(p.slug for p in pages)
    assert "m1" in slugs
    assert "d2" in slugs
    assert "c1" in slugs
