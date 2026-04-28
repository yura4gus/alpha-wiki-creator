from pathlib import Path
from tools.lint import check_duplicate_slugs

def test_duplicate_slug_detected(sample_wiki: Path):
    (sample_wiki / "wiki" / "modules" / "m1-dup.md").write_text(
        "---\ntitle: Dup\nslug: m1\nstatus: stable\n---\n# Dup\n")
    findings = check_duplicate_slugs(sample_wiki / "wiki")
    assert any("m1" in f.message for f in findings)
