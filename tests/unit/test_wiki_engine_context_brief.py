"""Tests for wiki_engine context_brief builder."""
from pathlib import Path
from tools.wiki_engine import rebuild_context_brief


def test_context_brief_under_8000_chars(sample_wiki: Path):
    out = rebuild_context_brief(sample_wiki / "wiki")
    assert len(out.read_text()) <= 8000


def test_context_brief_includes_recent_log(sample_wiki: Path):
    out = rebuild_context_brief(sample_wiki / "wiki")
    text = out.read_text()
    assert "bootstrap | sample wiki for tests" in text or "Recent log" in text
