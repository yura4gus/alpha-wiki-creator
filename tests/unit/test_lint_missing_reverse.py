from pathlib import Path
from tools.lint import check_missing_reverse_links
from tools._models import LintSeverity

def test_missing_reverse_detected(sample_wiki: Path):
    """d1.md has affects:[[m1]]; m1's `## Decisions` should list d1 — but doesn't."""
    findings = check_missing_reverse_links(sample_wiki / "wiki")
    msgs = [f.message for f in findings]
    assert any("d1" in m and "m1" in m for m in msgs)
    assert all(f.severity == LintSeverity.WARNING for f in findings)
    assert all(f.fix_available for f in findings)
