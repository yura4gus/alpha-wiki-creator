"""Deterministic release-readiness audit for Alpha-Wiki."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

EXPECTED_COMMANDS = {
    "init", "doctor", "ingest", "query", "lint", "evolve",
    "status", "spawn-agent", "render", "review", "rollup",
}

EXPECTED_TOOLS = {
    "doctor.py",
    "ingest_pipeline.py",
    "wiki_search.py",
    "lint.py",
    "status.py",
    "review.py",
    "rollup.py",
    "wiki_engine.py",
    "render_mermaid.py",
    "render_dot.py",
    "render_html.py",
}

RELEASE_DOCS = {
    "README.md",
    "docs/final-release-hardening-plan.md",
    "docs/alpha-wiki-lifecycle-automation-audit-2026-05-01.md",
    "docs/platform-compatibility-matrix.md",
}

PACKAGING_DOCS = {
    "CHANGELOG.md",
    "docs/quickstart.md",
}


@dataclass(frozen=True)
class AuditFinding:
    gate: str
    status: str
    message: str
    action: str | None = None


def run_release_audit(root: Path) -> list[AuditFinding]:
    return [
        _surface_check(root),
        _tools_check(root),
        _docs_check(root),
        _packaging_check(root),
        _trust_check(root),
        _platform_check(root),
    ]


def release_audit_report(root: Path) -> str:
    findings = run_release_audit(root)
    verdict = "BLOCKED" if any(item.status == FAIL for item in findings) else "READY_WITH_WARNINGS"
    if all(item.status == PASS for item in findings):
        verdict = "READY"
    lines = [
        "# Alpha-Wiki Release Audit",
        "",
        f"- Verdict: {verdict}",
        f"- Pass: {sum(1 for item in findings if item.status == PASS)}",
        f"- Warn: {sum(1 for item in findings if item.status == WARN)}",
        f"- Fail: {sum(1 for item in findings if item.status == FAIL)}",
        "",
        "## Gates",
        "",
    ]
    for item in findings:
        lines.append(f"- {item.status} `{item.gate}`: {item.message}")
        if item.action:
            lines.append(f"  Action: {item.action}")
    return "\n".join(lines) + "\n"


def _surface_check(root: Path) -> AuditFinding:
    missing_skills = sorted(name for name in EXPECTED_COMMANDS if not (root / "skills" / name / "SKILL.md").exists())
    missing_commands = sorted(name for name in EXPECTED_COMMANDS if not (root / "commands" / f"{name}.md").exists())
    if missing_skills or missing_commands:
        return AuditFinding(
            "skill-command-surface",
            FAIL,
            f"missing skills={missing_skills} commands={missing_commands}",
            "Restore one skill and one command per Alpha-Wiki operation.",
        )
    return AuditFinding("skill-command-surface", PASS, f"{len(EXPECTED_COMMANDS)} skills and commands present")


def _tools_check(root: Path) -> AuditFinding:
    missing = sorted(name for name in EXPECTED_TOOLS if not (root / "tools" / name).exists())
    if missing:
        return AuditFinding("deterministic-tools", FAIL, f"missing tools: {', '.join(missing)}")
    return AuditFinding("deterministic-tools", PASS, f"{len(EXPECTED_TOOLS)} release-critical tools present")


def _docs_check(root: Path) -> AuditFinding:
    missing = sorted(path for path in RELEASE_DOCS if not (root / path).exists())
    if missing:
        return AuditFinding("release-docs", FAIL, f"missing docs: {', '.join(missing)}")
    return AuditFinding("release-docs", PASS, "core release docs and compatibility matrix exist")


def _packaging_check(root: Path) -> AuditFinding:
    missing = sorted(path for path in PACKAGING_DOCS if not (root / path).exists())
    if missing:
        return AuditFinding(
            "packaging",
            FAIL,
            f"missing packaging docs: {', '.join(missing)}",
            "Add quickstart and changelog before tagging a public release.",
        )
    return AuditFinding("packaging", PASS, "quickstart and changelog exist")


def _trust_check(root: Path) -> AuditFinding:
    missing = [
        path for path in [
            "tools/claims_check.py",
            "tools/contracts_check.py",
            "tools/contradiction_detector.py",
        ]
        if not (root / path).exists()
    ]
    if missing:
        return AuditFinding(
            "trust-depth",
            WARN,
            f"semantic trust tools are still missing: {', '.join(missing)}",
            "Keep release scoped as beta or implement claim/contract checks before v1.0.",
        )
    return AuditFinding("trust-depth", PASS, "claim/contract/contradiction tools exist")


def _platform_check(root: Path) -> AuditFinding:
    if not (root / "docs" / "codex-adapter.md").exists():
        return AuditFinding("platform", FAIL, "Codex adapter docs missing")
    if not (root / "scripts" / "install_codex.py").exists():
        return AuditFinding("platform", FAIL, "Codex installer missing")
    return AuditFinding("platform", PASS, "Claude primary path and Codex adapter path documented")


@click.command()
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=Path("."), show_default=True)
def cli(root: Path) -> None:
    report = release_audit_report(root)
    click.echo(report)
    if "Verdict: BLOCKED" in report:
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
