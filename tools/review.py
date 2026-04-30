"""Wiki-level review report."""
from __future__ import annotations

from pathlib import Path

import click

from tools._models import LintFinding, LintSeverity
from tools.lint import _load_config, run_all_checks
from tools.status import status_report


def review_report(wiki_dir: Path, config_path: Path | None = None) -> str:
    """Build a deterministic wiki review report.

    This is intentionally structural, not an LLM semantic review. It gives CI and
    `/alpha-wiki:review` a real backend while deeper contradiction/staleness
    checks can be added in Phase 1a skill hardening.
    """
    schema, dir_to_type, dep_rules = _load_config(config_path)
    findings = run_all_checks(wiki_dir, schema, dir_to_type, dep_rules)
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    warnings = [f for f in findings if f.severity == LintSeverity.WARNING]

    parts = [
        "# Wiki Review",
        "",
        "## Summary",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        f"- Total findings: {len(findings)}",
        "",
        "## Health Snapshot",
        "",
        status_report(wiki_dir).strip(),
        "",
        "## Structural Findings",
        "",
    ]
    if findings:
        parts.extend(_render_findings("Errors", errors))
        parts.extend(_render_findings("Warnings", warnings))
    else:
        parts.append("No structural findings.")

    parts.extend([
        "",
        "## Suggested Next Actions",
        "",
    ])
    if errors:
        parts.append("- Fix blocking errors before publishing or merging wiki changes.")
    if warnings:
        parts.append("- Review warnings and run `/alpha-wiki:lint --fix` for safe reverse-link repairs.")
    if not findings:
        parts.append("- No immediate structural action required.")
    parts.append("- Run `/alpha-wiki:status` for the regular health dashboard.")
    return "\n".join(parts).rstrip() + "\n"


def _render_findings(title: str, findings: list[LintFinding]) -> list[str]:
    lines = [f"### {title}", ""]
    if not findings:
        lines.append("_(none)_")
        lines.append("")
        return lines
    for finding in findings:
        lines.append(f"- `{finding.check}` {finding.file}: {finding.message}")
        if finding.suggested_fix:
            lines.append(f"  Suggested fix: {finding.suggested_fix}")
    lines.append("")
    return lines


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--config", type=click.Path(path_type=Path, exists=True), help="Path to .alpha-wiki/config.yaml")
@click.option("--out", type=click.Path(path_type=Path), help="Optional report output path.")
def cli(wiki_dir: Path, config: Path | None, out: Path | None) -> None:
    report = review_report(wiki_dir, config)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        click.echo(f"wrote {out}")
        return
    click.echo(report)


if __name__ == "__main__":
    cli()
