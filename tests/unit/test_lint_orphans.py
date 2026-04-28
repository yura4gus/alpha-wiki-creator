from pathlib import Path
from tools.lint import check_orphans

def test_orphan_detected(sample_wiki: Path):
    findings = check_orphans(sample_wiki / "wiki")
    msgs = [f.message for f in findings]
    assert any("m3" in m for m in msgs)
