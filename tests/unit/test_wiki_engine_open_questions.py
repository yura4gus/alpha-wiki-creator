"""Tests for wiki_engine open_questions builder."""
from pathlib import Path
from tools.wiki_engine import rebuild_open_questions


def test_open_questions_extracted(sample_wiki: Path):
    # Add an explicit open question to one page
    p = sample_wiki / "wiki" / "modules" / "m1.md"
    p.write_text(p.read_text() + "\n## Open questions\n- Should we shard?\n- Auth strategy?\n")
    out = rebuild_open_questions(sample_wiki / "wiki")
    text = out.read_text()
    assert "Should we shard?" in text
    assert "Auth strategy?" in text
