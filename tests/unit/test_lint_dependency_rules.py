from pathlib import Path
from tools.lint import check_dependency_rules
from tools._models import LintSeverity

def test_dependency_rule_violation_detected(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "core").mkdir(parents=True)
    (wiki / "infrastructure").mkdir()
    (wiki / "core" / "user.md").write_text(
        "---\ntitle: User\nslug: user\nstatus: stable\nuses: ['[[postgres-adapter]]']\n---\n")
    (wiki / "infrastructure" / "postgres-adapter.md").write_text(
        "---\ntitle: PG\nslug: postgres-adapter\nstatus: stable\n---\n")
    rules = [{"from": "core/", "forbidden_to": ["infrastructure/", "adapters/"]}]
    findings = check_dependency_rules(wiki, rules)
    assert any(f.severity == LintSeverity.WARNING for f in findings)
    assert any("core/" in f.message and "infrastructure/" in f.message for f in findings)
