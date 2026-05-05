"""Claim freshness and provenance checks for Alpha-Wiki."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from tools._models import LintFinding, LintSeverity, Page
from tools.wiki_engine import _coerce_targets, page_role, scan_wiki


CLAIM_STALE_DAYS = 90
PROVENANCE_KEYS = {"source", "sources", "derived_from", "distilled_from", "evidence", "evidence_strength"}


def check_claims(wiki_dir: Path, today: date | None = None) -> list[LintFinding]:
    today = today or date.today()
    pages = scan_wiki(wiki_dir)
    by_slug = {page.slug: page for page in pages}
    findings: list[LintFinding] = []
    for claim in _claim_pages(wiki_dir, pages):
        findings.extend(_check_provenance(claim))
        findings.extend(_check_freshness(claim, today))
        findings.extend(_check_explicit_contradictions(claim, by_slug))
    return findings


def claims_report(wiki_dir: Path) -> str:
    findings = check_claims(wiki_dir)
    errors = [finding for finding in findings if finding.severity == LintSeverity.ERROR]
    warnings = [finding for finding in findings if finding.severity == LintSeverity.WARNING]
    lines = [
        "# Claims Check",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("- PASS: claims have provenance, freshness metadata, and no unresolved explicit contradictions.")
    for finding in findings:
        icon = "ERROR" if finding.severity == LintSeverity.ERROR else "WARN"
        lines.append(f"- {icon} `{finding.check}` {finding.file}: {finding.message}")
        if finding.suggested_fix:
            lines.append(f"  Action: {finding.suggested_fix}")
    return "\n".join(lines) + "\n"


def _claim_pages(wiki_dir: Path, pages: list[Page]) -> list[Page]:
    claims: list[Page] = []
    for page in pages:
        rel = Path(page.path).relative_to(wiki_dir)
        if page_role(wiki_dir, page) == "document" and "claims" in rel.parts:
            claims.append(page)
            continue
        marker = str(page.frontmatter.get("type") or page.frontmatter.get("kind") or "").lower()
        if marker == "claim" or any(key in page.frontmatter for key in ("claim", "subject", "verdict", "stance")):
            claims.append(page)
    return claims


def _check_provenance(claim: Page) -> list[LintFinding]:
    has_frontmatter_provenance = any(claim.frontmatter.get(key) for key in PROVENANCE_KEYS)
    has_body_provenance = "source:" in claim.body.lower() or "provenance:" in claim.body.lower()
    if has_frontmatter_provenance or has_body_provenance:
        return []
    return [_finding(
        claim,
        "claim-missing-provenance",
        LintSeverity.WARNING,
        f"{claim.slug} has no source/evidence provenance",
        "Add `source`, `sources`, `derived_from`, or `evidence_strength` before using this claim in decisions.",
    )]


def _check_freshness(claim: Page, today: date) -> list[LintFinding]:
    raw_date = claim.frontmatter.get("date_updated") or claim.frontmatter.get("date")
    if not raw_date:
        return [_finding(
            claim,
            "claim-missing-date",
            LintSeverity.WARNING,
            f"{claim.slug} has no `date_updated` or `date`",
            "Add `date_updated` so review can timebox claim freshness.",
        )]
    try:
        updated = date.fromisoformat(str(raw_date))
    except ValueError:
        return [_finding(
            claim,
            "claim-invalid-date",
            LintSeverity.WARNING,
            f"{claim.slug} has invalid claim date `{raw_date}`",
            "Use ISO date format, e.g. `2026-05-05`.",
        )]
    if (today - updated).days <= CLAIM_STALE_DAYS:
        return []
    return [_finding(
        claim,
        "claim-stale",
        LintSeverity.WARNING,
        f"{claim.slug} is older than {CLAIM_STALE_DAYS} days",
        "Refresh the claim, downgrade it, or add a review exemption.",
    )]


def _check_explicit_contradictions(claim: Page, by_slug: dict[str, Page]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for target in _coerce_targets(claim.frontmatter.get("contradicts", [])):
        if target not in by_slug:
            findings.append(_finding(
                claim,
                "claim-contradiction-target-missing",
                LintSeverity.ERROR,
                f"{claim.slug} contradicts missing page [[{target}]]",
                "Create the target claim or remove the stale contradiction link.",
            ))
        else:
            findings.append(_finding(
                claim,
                "claim-explicit-contradiction",
                LintSeverity.WARNING,
                f"{claim.slug} explicitly contradicts [[{target}]]",
                "Resolve the contradiction or route it to review with owner/timebox.",
            ))
    return findings


def _finding(page: Page, check: str, severity: LintSeverity, message: str, action: str) -> LintFinding:
    return LintFinding(
        check=check,
        severity=severity,
        file=page.path,
        line=0,
        message=message,
        fix_available=False,
        suggested_fix=action,
    )


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
def cli(wiki_dir: Path) -> None:
    report = claims_report(wiki_dir)
    click.echo(report)
    if any(finding.severity == LintSeverity.ERROR for finding in check_claims(wiki_dir)):
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
