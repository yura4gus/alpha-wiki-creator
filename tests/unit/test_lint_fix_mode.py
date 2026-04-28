from pathlib import Path
from tools.lint import apply_fixes, run_all_checks

def test_fix_mode_writes_reverse_link(sample_wiki: Path):
    findings = run_all_checks(sample_wiki / "wiki", schema={}, dir_to_type={}, dependency_rules=[])
    fixed = apply_fixes(findings, sample_wiki / "wiki")
    # m1 should now contain d1 in some Decisions reference
    m1 = (sample_wiki / "wiki" / "modules" / "m1.md").read_text()
    assert "d1" in m1
    assert fixed > 0
