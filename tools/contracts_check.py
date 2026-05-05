"""Contract trust checks for Alpha-Wiki."""
from __future__ import annotations

import re
from pathlib import Path

import click

from tools._models import LintFinding, LintSeverity, Page
from tools.wiki_engine import _coerce_targets, page_role, scan_wiki


def check_contracts(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {page.slug: page for page in pages}
    findings: list[LintFinding] = []
    for contract in _contract_pages(wiki_dir, pages):
        findings.extend(_check_contract_owner(contract))
        findings.extend(_check_consumers(contract, by_slug))
        findings.extend(_check_migration_notes(contract))
    return findings


def contracts_report(wiki_dir: Path) -> str:
    findings = check_contracts(wiki_dir)
    errors = [finding for finding in findings if finding.severity == LintSeverity.ERROR]
    warnings = [finding for finding in findings if finding.severity == LintSeverity.WARNING]
    lines = [
        "# Contracts Check",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("- PASS: contract ownership, consumers, and migration notes are consistent.")
    for finding in findings:
        icon = "ERROR" if finding.severity == LintSeverity.ERROR else "WARN"
        lines.append(f"- {icon} `{finding.check}` {finding.file}: {finding.message}")
        if finding.suggested_fix:
            lines.append(f"  Action: {finding.suggested_fix}")
    return "\n".join(lines) + "\n"


def _contract_pages(wiki_dir: Path, pages: list[Page]) -> list[Page]:
    return [
        page for page in pages
        if page_role(wiki_dir, page) == "contract"
        or str(Path(page.path).relative_to(wiki_dir)).startswith("contracts/")
    ]


def _check_contract_owner(contract: Page) -> list[LintFinding]:
    if _targets(contract, "service"):
        return []
    return [_finding(
        contract,
        "contract-missing-service",
        LintSeverity.ERROR,
        f"{contract.slug} has no `service` owner",
        "Add `service: [[service-slug]]` to the contract frontmatter.",
    )]


def _check_consumers(contract: Page, by_slug: dict[str, Page]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    consumers = _targets(contract, "consumers")
    if not consumers:
        findings.append(_finding(
            contract,
            "contract-missing-consumers",
            LintSeverity.WARNING,
            f"{contract.slug} has no `consumers` list",
            "Add consumer modules/services or mark the contract as intentionally unused in release notes.",
        ))
        return findings
    for consumer_slug in consumers:
        consumer = by_slug.get(consumer_slug)
        if consumer is None:
            findings.append(_finding(
                contract,
                "contract-consumer-missing-page",
                LintSeverity.ERROR,
                f"{contract.slug} lists missing consumer [[{consumer_slug}]]",
                "Create the consumer page or remove it from `consumers`.",
            ))
            continue
        if contract.slug not in _targets(consumer, "consumes"):
            findings.append(_finding(
                consumer,
                "contract-consumer-missing-reverse",
                LintSeverity.WARNING,
                f"{consumer.slug} is listed as a consumer of {contract.slug} but lacks `consumes: [[{contract.slug}]]`",
                f"Add `consumes: [[{contract.slug}]]` to {consumer.slug}.",
            ))
    return findings


def _check_migration_notes(contract: Page) -> list[LintFinding]:
    if not _requires_migration_notes(contract):
        return []
    body = contract.body.lower()
    if "migration notes" in body or "migration plan" in body:
        return []
    return [_finding(
        contract,
        "contract-missing-migration-notes",
        LintSeverity.WARNING,
        f"{contract.slug} looks version-bumped but has no Migration notes section",
        "Add `## Migration notes` with consumer impact and rollout guidance.",
    )]


def _requires_migration_notes(contract: Page) -> bool:
    fm = contract.frontmatter
    if str(fm.get("migration_required", "")).lower() in {"true", "yes", "1"}:
        return True
    if fm.get("previous_version") or fm.get("supersedes"):
        return True
    version = str(fm.get("version", "")).strip().lower()
    match = re.match(r"v?(\d+)", version)
    return bool(match and int(match.group(1)) > 1)


def _targets(page: Page, key: str) -> list[str]:
    return _coerce_targets(page.frontmatter.get(key, []))


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
    report = contracts_report(wiki_dir)
    click.echo(report)
    if any(finding.severity == LintSeverity.ERROR for finding in check_contracts(wiki_dir)):
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
