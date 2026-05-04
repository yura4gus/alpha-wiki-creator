from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_karpathy_compliance_audit_covers_core_contract():
    text = (ROOT / "docs" / "karpathy-llm-wiki-compliance-audit-2026-05-01.md").read_text()

    for phrase in [
        "Simple markdown memory",
        "`ingest` operation",
        "`query` operation",
        "`lint` operation",
        "`index.md` service file",
        "`log.md` service file",
        "Fast agent orientation",
        "No embeddings / no vector store",
        "Status: pass",
    ]:
        assert phrase in text


def test_best_practices_gap_analysis_routes_work_to_phase_1a():
    text = (ROOT / "docs" / "best-practices-gap-analysis-2026-04-30.md").read_text()

    assert "Phase 1a" in text
    assert "`doctor`" in text
    assert "Graph QA snapshots" in text


def test_final_release_plan_covers_key_hardening_topics():
    text = (ROOT / "docs" / "final-release-hardening-plan.md").read_text()

    for phrase in [
        "Cluster semantics and ownership links",
        "Deterministic ingest pipeline",
        "Deterministic query helper",
        "Doctor command",
        "Codex adapter hardening",
        "Platform compatibility matrix",
        "Cluster Semantics Contract",
        "Graph QA",
        "Release readiness audit",
        "Release Gates",
    ]:
        assert phrase in text


def test_lifecycle_automation_audit_covers_closed_loop():
    text = (ROOT / "docs" / "alpha-wiki-lifecycle-automation-audit-2026-05-01.md").read_text()

    for phrase in [
        "install",
        "init/bootstrap",
        "ingest/update pages",
        "rebuild graph artifacts",
        "lint structural rules",
        "status gap report",
        "review trust report",
        "rollup activity summary",
        "Rule-To-Automation Matrix",
        "partially closed",
        "Universalization Scorecard",
    ]:
        assert phrase in text


def test_platform_matrix_covers_supported_and_deferred_runtimes():
    text = (ROOT / "docs" / "platform-compatibility-matrix.md").read_text()

    for phrase in [
        "Claude Code is the primary supported runtime",
        "Codex is supported through prefixed skill adapters",
        "Gemini is not supported",
        "Session hooks",
        "Doctor check",
        "Codex has no native session-start/session-end hook equivalent",
    ]:
        assert phrase in text


def test_final_release_readiness_audit_names_release_blockers():
    text = (ROOT / "docs" / "final-release-readiness-audit-2026-05-04.md").read_text()

    for phrase in [
        "BLOCKED for final v1.0",
        "`CHANGELOG.md` missing",
        "`docs/quickstart.md` missing",
        "Fresh install smoke not recorded",
        "Release readiness audit tool",
        "Plugin metadata/version/tag",
    ]:
        assert phrase in text
