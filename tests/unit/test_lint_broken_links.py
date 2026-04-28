from pathlib import Path
from tools.lint import check_broken_wikilinks
from tools._models import LintSeverity

def test_broken_link_detected(sample_wiki: Path):
    findings = check_broken_wikilinks(sample_wiki / "wiki")
    # d2.md has affects: [[m99-nonexistent]]
    targets = [f.message for f in findings]
    assert any("m99-nonexistent" in t for t in targets)
    assert all(f.severity == LintSeverity.ERROR for f in findings)
