from datetime import date
from pathlib import Path

from tools.claims_check import check_claims, claims_report


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_claims_check_passes_supported_fresh_claim(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "claims" / "auth-claim.md",
        "title: Auth Claim\nslug: auth-claim\ntype: claim\nsubject: auth security\nverdict: supported\ndate_updated: 2026-05-01\nsource: [[auth-audit]]",
        "# Auth Claim\n",
    )

    assert check_claims(wiki, today=date(2026, 5, 5)) == []
    assert "PASS" in claims_report(wiki)


def test_claims_check_flags_missing_provenance_stale_and_missing_target(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "claims" / "legacy-claim.md",
        "title: Legacy Claim\nslug: legacy-claim\ntype: claim\nsubject: legacy auth\nverdict: accepted\ndate_updated: 2025-01-01\ncontradicts: [[missing-claim]]",
        "# Legacy Claim\n",
    )

    checks = {finding.check for finding in check_claims(wiki, today=date(2026, 5, 5))}

    assert "claim-missing-provenance" in checks
    assert "claim-stale" in checks
    assert "claim-contradiction-target-missing" in checks
