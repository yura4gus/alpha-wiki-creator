from pathlib import Path

from click.testing import CliRunner

from tools.release_audit import cli, release_audit_report, run_release_audit


ROOT = Path(__file__).parents[2]


def test_release_audit_reports_current_blockers():
    findings = run_release_audit(ROOT)
    by_gate = {finding.gate: finding for finding in findings}

    assert by_gate["skill-command-surface"].status == "PASS"
    assert by_gate["deterministic-tools"].status == "PASS"
    assert by_gate["packaging"].status == "FAIL"
    assert by_gate["trust-depth"].status == "WARN"


def test_release_audit_report_is_blocked_until_packaging_docs_exist():
    report = release_audit_report(ROOT)

    assert "Verdict: BLOCKED" in report
    assert "CHANGELOG.md" in report
    assert "docs/quickstart.md" in report


def test_release_audit_cli_exits_nonzero_when_blocked():
    result = CliRunner().invoke(cli, ["--root", str(ROOT)])

    assert result.exit_code == 1
    assert "Alpha-Wiki Release Audit" in result.output
