"""Deterministic contradiction detector for Alpha-Wiki claims."""
from __future__ import annotations

from pathlib import Path

import click

from tools._models import LintFinding, LintSeverity, Page
from tools.wiki_engine import _coerce_targets, scan_wiki


POSITIVE = {"true", "yes", "supported", "accepted", "allowed", "enabled", "pass", "valid"}
NEGATIVE = {"false", "no", "refuted", "rejected", "blocked", "disabled", "fail", "invalid"}


def detect_contradictions(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {page.slug: page for page in pages}
    findings: list[LintFinding] = []
    findings.extend(_explicit_contradictions(pages, by_slug))
    findings.extend(_opposing_claim_stances(wiki_dir, pages))
    return findings


def contradiction_report(wiki_dir: Path) -> str:
    findings = detect_contradictions(wiki_dir)
    errors = [finding for finding in findings if finding.severity == LintSeverity.ERROR]
    warnings = [finding for finding in findings if finding.severity == LintSeverity.WARNING]
    lines = [
        "# Contradiction Detector",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("- PASS: no explicit or deterministic opposing-stance contradictions found.")
    for finding in findings:
        icon = "ERROR" if finding.severity == LintSeverity.ERROR else "WARN"
        lines.append(f"- {icon} `{finding.check}` {finding.file}: {finding.message}")
        if finding.suggested_fix:
            lines.append(f"  Action: {finding.suggested_fix}")
    return "\n".join(lines) + "\n"


def _explicit_contradictions(pages: list[Page], by_slug: dict[str, Page]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for page in pages:
        for key in ("contradicts", "invalidates"):
            for target in _coerce_targets(page.frontmatter.get(key, [])):
                if target not in by_slug:
                    findings.append(_finding(
                        page,
                        "contradiction-target-missing",
                        LintSeverity.ERROR,
                        f"{page.slug}.{key} points at missing [[{target}]]",
                        "Create the target page or remove the stale contradiction link.",
                    ))
                else:
                    findings.append(_finding(
                        page,
                        "explicit-contradiction",
                        LintSeverity.WARNING,
                        f"{page.slug} {key} [[{target}]]",
                        "Resolve, supersede, or assign owner/timebox before relying on either page.",
                    ))
    return findings


def _opposing_claim_stances(wiki_dir: Path, pages: list[Page]) -> list[LintFinding]:
    claims = [_claim_record(wiki_dir, page) for page in pages]
    claims = [claim for claim in claims if claim is not None]
    findings: list[LintFinding] = []
    seen: set[tuple[str, str]] = set()
    for index, left in enumerate(claims):
        for right in claims[index + 1:]:
            if left["subject"] != right["subject"] or left["polarity"] == right["polarity"]:
                continue
            key = tuple(sorted([left["slug"], right["slug"]]))
            if key in seen:
                continue
            seen.add(key)
            page = left["page"]
            findings.append(_finding(
                page,
                "opposing-claim-stance",
                LintSeverity.ERROR,
                f"[[{left['slug']}]] and [[{right['slug']}]] assert opposing stances for `{left['subject']}`",
                "Link the claims with `contradicts`, choose an accepted source, or timebox review.",
            ))
    return findings


def _claim_record(wiki_dir: Path, page: Page) -> dict | None:
    marker = str(page.frontmatter.get("type") or page.frontmatter.get("kind") or "").lower()
    rel = Path(page.path).relative_to(wiki_dir)
    is_claim = marker == "claim" or "claims" in rel.parts or any(
        key in page.frontmatter for key in ("claim", "subject", "verdict", "stance")
    )
    if not is_claim:
        return None
    subject = str(page.frontmatter.get("subject") or page.frontmatter.get("claim") or page.title).strip().lower()
    verdict = str(
        page.frontmatter.get("verdict")
        or page.frontmatter.get("stance")
        or page.frontmatter.get("truth")
        or ""
    ).strip().lower()
    polarity = _polarity(verdict)
    if not subject or polarity is None:
        return None
    return {"slug": page.slug, "subject": subject, "polarity": polarity, "page": page}


def _polarity(verdict: str) -> str | None:
    if verdict in POSITIVE:
        return "positive"
    if verdict in NEGATIVE:
        return "negative"
    return None


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
    report = contradiction_report(wiki_dir)
    click.echo(report)
    if any(finding.severity == LintSeverity.ERROR for finding in detect_contradictions(wiki_dir)):
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
