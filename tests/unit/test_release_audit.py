from pathlib import Path

from click.testing import CliRunner

from tools.release_audit import cli, release_audit_report, run_release_audit


ROOT = Path(__file__).parents[2]


def test_release_audit_reports_current_release_gates():
    findings = run_release_audit(ROOT)
    by_gate = {finding.gate: finding for finding in findings}

    assert by_gate["skill-command-surface"].status == "PASS"
    assert by_gate["deterministic-tools"].status == "PASS"
    assert by_gate["packaging"].status == "PASS"
    assert by_gate["fresh-install-smoke"].status == "PASS"
    assert by_gate["version-metadata"].status == "PASS"
    assert by_gate["trust-depth"].status == "WARN"


def test_release_audit_report_is_ready_with_warnings_until_trust_tools_exist():
    report = release_audit_report(ROOT)

    assert "Verdict: READY_WITH_WARNINGS" in report
    assert "quickstart and changelog exist" in report
    assert "fresh-install-smoke" in report
    assert "version-metadata" in report


def test_release_audit_cli_exits_zero_when_only_warnings_remain():
    result = CliRunner().invoke(cli, ["--root", str(ROOT)])

    assert result.exit_code == 0
    assert "Alpha-Wiki Release Audit" in result.output
