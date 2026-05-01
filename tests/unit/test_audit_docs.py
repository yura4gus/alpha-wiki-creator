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
