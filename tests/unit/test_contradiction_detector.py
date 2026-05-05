from pathlib import Path

from tools.contradiction_detector import contradiction_report, detect_contradictions


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_contradiction_detector_flags_opposing_claim_stances(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "claims" / "auth-supported.md",
        "title: Auth Supported\nslug: auth-supported\ntype: claim\nsubject: auth rollout\nverdict: supported",
        "# Auth Supported\n",
    )
    _write_page(
        wiki / "claims" / "auth-refuted.md",
        "title: Auth Refuted\nslug: auth-refuted\ntype: claim\nsubject: auth rollout\nverdict: refuted",
        "# Auth Refuted\n",
    )

    findings = detect_contradictions(wiki)

    assert any(finding.check == "opposing-claim-stance" for finding in findings)
    assert "opposing-claim-stance" in contradiction_report(wiki)


def test_contradiction_detector_passes_consistent_claims(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "claims" / "search-supported.md",
        "title: Search Supported\nslug: search-supported\ntype: claim\nsubject: search rollout\nverdict: supported",
        "# Search Supported\n",
    )
    _write_page(
        wiki / "claims" / "billing-supported.md",
        "title: Billing Supported\nslug: billing-supported\ntype: claim\nsubject: billing rollout\nverdict: accepted",
        "# Billing Supported\n",
    )

    assert detect_contradictions(wiki) == []
    assert "PASS" in contradiction_report(wiki)
