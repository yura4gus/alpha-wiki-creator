"""Delivery-audit scaffold: structure, status labels, invariants, read-only git.

Deterministic — the report contains no wall-clock date by default, and git
inventory is asserted structurally (never on commit hashes).
"""
import subprocess
from pathlib import Path

import pytest

from tools.project_audit import (
    AUDIT_SECTIONS,
    NOT_CONFIRMED,
    READINESS_CHECKLIST,
    STATUS_LABELS,
    AuditInputs,
    audit_report,
    git_inventory,
)


def _report(**kw) -> str:
    return audit_report(AuditInputs(project_name="Demo", **kw))


def test_all_seventeen_sections_present_in_order():
    report = _report()
    positions = [report.find(f"## {title}") for title in AUDIT_SECTIONS]
    assert all(pos != -1 for pos in positions), "a required section heading is missing"
    assert positions == sorted(positions), "sections are out of order"


def test_status_label_legend_is_verbatim():
    report = _report()
    for emoji, label in STATUS_LABELS:
        assert f"{emoji} {label}" in report


def test_security_section_always_present_for_software_project():
    report = _report()
    assert "## 10. Security Review" in report
    assert "money/custody flow gates" in report
    assert "release security gates" in report
    # Release-not-ready guardrail language is present.
    assert "Release is NOT ready" in report


def test_provider_and_business_coverage_tables_present():
    report = _report()
    assert "## 8. Provider Coverage" in report
    assert "| Provider | Role | Code wired? |" in report
    assert "## 7. Backend/Frontend/SDK/Provider Business Coverage" in report
    assert "| Business case | Backend | Frontend | SDK | Provider |" in report


def test_missing_evidence_is_marked_not_confirmed():
    report = _report()
    # Executive summary and every scaffolded matrix default to not-confirmed.
    assert f"Overall readiness: {NOT_CONFIRMED}%" in report
    assert report.count(NOT_CONFIRMED) > 20


def test_readiness_checklist_and_next_actions_present():
    report = _report()
    for item in READINESS_CHECKLIST:
        assert f"- [ ] {item}" in report
    assert "## 17. Next 3 Actions" in report


def test_no_repo_yields_low_confidence_source_inventory():
    report = _report()
    assert "no repo path provided" in report
    assert "_(none provided — low confidence)_" in report


def test_multi_repo_produces_a_git_block_per_repo(tmp_path: Path):
    # Two non-repo paths still each get a labeled block.
    a = tmp_path / "repo-a"
    b = tmp_path / "repo-b"
    a.mkdir()
    b.mkdir()
    report = _report(repos=[str(a), str(b)])
    assert f"### `{a}`" in report
    assert f"### `{b}`" in report


def test_git_inventory_non_repo_is_unavailable(tmp_path: Path):
    inv = git_inventory(tmp_path)
    assert inv.available is False
    assert inv.branch == NOT_CONFIRMED


def test_git_inventory_reads_real_repo_read_only(tmp_path: Path):
    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True,
                       capture_output=True, text=True)

    run("init")
    run("-c", "user.email=t@t.io", "-c", "user.name=t", "commit",
        "--allow-empty", "-m", "initial commit")
    (tmp_path / "f.txt").write_text("x\n")  # untracked working-tree change

    inv = git_inventory(tmp_path)

    assert inv.available is True
    assert isinstance(inv.branch, str) and inv.branch != NOT_CONFIRMED
    assert len(inv.recent_commits) >= 1
    assert inv.untracked >= 1
    # Read-only: inventory must not have created or modified tracked files.
    status = subprocess.run(["git", "-C", str(tmp_path), "log", "--oneline"],
                            capture_output=True, text=True)
    assert status.stdout.count("\n") == 1  # still exactly one commit


def test_cli_writes_report(tmp_path: Path):
    from click.testing import CliRunner

    from tools.project_audit import cli

    out = tmp_path / "audit.md"
    result = CliRunner().invoke(cli, ["--project", "Demo", "--out", str(out)])
    assert result.exit_code == 0
    text = out.read_text()
    assert "# Delivery Audit — Demo" in text
    assert "## 1. Executive Summary" in text


@pytest.mark.parametrize("period", ["today", "last 24h", "week", "entire project"])
def test_period_is_recorded(period):
    report = _report(period=period)
    assert f"- Period: {period}" in report
