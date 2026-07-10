"""Deterministic delivery-audit scaffold for Alpha-Wiki.

This backend does NOT judge a project. It guarantees the *structure* and the
*invariants* of a delivery-readiness audit so every Claude/Codex session produces
the same shape of report:

- all 17 required sections are present and in order;
- the exact status-label legend is emitted;
- the security section is always present for software projects;
- provider- and business-case-coverage tables are always scaffolded;
- any cell without evidence defaults to `not confirmed` (never invented);
- git inventory is read-only (no writes, commits, pushes, or edits).

The operator skill (`/alpha-wiki:audit-project`) fills the tables from real
evidence; this module keeps it honest.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import click

NOT_CONFIRMED = "not confirmed"

# Exact status labels — tests assert these verbatim.
STATUS_LABELS: tuple[tuple[str, str], ...] = (
    ("🟢", "Done / almost closed — 80–100%"),
    ("🟡", "In progress / partially ready — 30–79%"),
    ("⚪", "Not started / almost not started — 0–29%"),
    ("🔴", "Blocked / risk or stopper"),
    ("🔵", "Needs review / done but needs verification"),
)

# The 17 required report sections, in order. Tests assert every heading is present.
AUDIT_SECTIONS: tuple[str, ...] = (
    "1. Executive Summary",
    "2. Source Inventory",
    "3. Status Table",
    "4. Progress By Period/Session",
    "5. What Happened Earlier",
    "6. Where We Are Now",
    "7. Backend/Frontend/SDK/Provider Business Coverage",
    "8. Provider Coverage",
    "9. Deploy Readiness",
    "10. Security Review",
    "11. Performance/Readiness",
    "12. Tech Debt",
    "13. Roadmap Forward",
    "14. Readiness Checklist",
    "15. Risks",
    "16. Mismatches And Questions",
    "17. Next 3 Actions",
)

DEFAULT_PHASES: tuple[str, ...] = (
    "Foundation / architecture",
    "Core functionality",
    "Backend/API/DB",
    "Frontend/UI/UX",
    "SDK",
    "Provider integrations",
    "Auth/security",
    "QA/testing",
    "Performance",
    "Deploy/release",
    "Documentation/handoff",
    "Tech debt",
)

READINESS_CHECKLIST: tuple[str, ...] = (
    "Architecture/canons confirmed",
    "Core backend flows implemented",
    "Core frontend flows implemented",
    "SDK/backend contract verified",
    "Provider coverage confirmed",
    "API/contracts stable",
    "Auth/security reviewed",
    "Integration/E2E tests pass",
    "Performance smoke/load tested",
    "Deploy configured",
    "Env/secrets verified",
    "Documentation/wiki up to date",
    "No critical blockers",
    "Next step is clear",
    "Ready for next developer/agent handoff",
)

# Source categories inventoried before conclusions are drawn.
SOURCE_KINDS: tuple[str, ...] = (
    "git repositories", "branches", "remotes", "latest commits", "uncommitted changes",
    "PR/MR metadata", "docs", "roadmap", "TODOs", "changelog", "wiki pages", "logs",
    "test outputs", "deployment configs", "CI configs", "env examples", "API specs",
    "SDK docs", "provider docs", "pasted chat/session summaries",
)


@dataclass(frozen=True)
class GitInventory:
    path: str
    available: bool
    branch: str = NOT_CONFIRMED
    remote: str = NOT_CONFIRMED
    upstream: str = NOT_CONFIRMED
    divergence: str = NOT_CONFIRMED
    recent_commits: tuple[str, ...] = ()
    uncommitted: int = 0
    untracked: int = 0
    local_branches: int = 0


@dataclass(frozen=True)
class AuditInputs:
    project_name: str
    repos: list[str] = field(default_factory=list)
    period: str = "entire project"
    focus: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)
    software_project: bool = True


def _git(path: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def git_inventory(repo_path: Path) -> GitInventory:
    """Read-only git inventory. Never writes. Returns available=False for non-repos."""
    path = Path(repo_path)
    inside = _git(path, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        return GitInventory(path=str(repo_path), available=False)

    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD") or NOT_CONFIRMED
    remote = _git(path, "remote", "get-url", "origin") or NOT_CONFIRMED
    upstream = _git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") or NOT_CONFIRMED
    divergence = NOT_CONFIRMED
    if upstream != NOT_CONFIRMED:
        counts = _git(path, "rev-list", "--left-right", "--count", "@{u}...HEAD")
        if counts:
            behind, _, ahead = counts.partition("\t")
            divergence = f"{ahead.strip()} ahead / {behind.strip()} behind {upstream}"
    log = _git(path, "log", "--oneline", "-5") or ""
    commits = tuple(line for line in log.splitlines() if line)
    porcelain = _git(path, "status", "--porcelain") or ""
    status_lines = [line for line in porcelain.splitlines() if line]
    untracked = sum(1 for line in status_lines if line.startswith("??"))
    uncommitted = len(status_lines) - untracked
    branches = _git(path, "branch", "--format=%(refname:short)") or ""
    local_branches = len([b for b in branches.splitlines() if b.strip()])

    return GitInventory(
        path=str(repo_path),
        available=True,
        branch=branch,
        remote=remote,
        upstream=upstream,
        divergence=divergence,
        recent_commits=commits,
        uncommitted=uncommitted,
        untracked=untracked,
        local_branches=local_branches,
    )


def source_inventory_rows(inputs: AuditInputs) -> list[tuple[str, str, str, str]]:
    """(source, checked?, confidence, notes). Everything unproven starts unchecked."""
    checked_git = bool(inputs.repos)
    rows: list[tuple[str, str, str, str]] = []
    for kind in SOURCE_KINDS:
        if kind in {"git repositories", "branches", "remotes", "latest commits", "uncommitted changes"}:
            checked = "yes" if checked_git else "no"
            confidence = "high" if checked_git else "low"
            notes = f"{len(inputs.repos)} repo(s) provided" if checked_git else "no repo path provided"
        elif kind == "pasted chat/session summaries":
            has = bool(inputs.context_notes)
            checked = "yes" if has else "no"
            confidence = "low" if has else "n/a"
            notes = "context provided — treat as unverified claims" if has else "none provided"
        else:
            checked = "no"
            confidence = "low"
            notes = NOT_CONFIRMED
        rows.append((kind, checked, confidence, notes))
    return rows


def audit_report(inputs: AuditInputs) -> str:
    lines: list[str] = [
        f"# Delivery Audit — {inputs.project_name}",
        "",
        f"- Period: {inputs.period}",
        f"- Repositories: {', '.join(inputs.repos) if inputs.repos else '_(none provided — low confidence)_'}",
        f"- Focus areas: {', '.join(inputs.focus) if inputs.focus else 'all'}",
        "",
        "## Status Labels",
        "",
    ]
    for emoji, label in STATUS_LABELS:
        lines.append(f"- {emoji} {label}")
    lines.append("")

    # 1. Executive Summary
    lines += _section("1. Executive Summary", [
        f"- Where we are now: {NOT_CONFIRMED} — fill from evidence below.",
        f"- Overall readiness: {NOT_CONFIRMED}%",
        f"- Main progress for the period: {NOT_CONFIRMED}",
        f"- Main blockers: {NOT_CONFIRMED}",
        f"- Blockers confirmed or unverified: {NOT_CONFIRMED}",
        f"- Best next step: {NOT_CONFIRMED}",
    ])

    # 2. Source Inventory
    src_rows = source_inventory_rows(inputs)
    lines += _table_section("2. Source Inventory",
        ["Source", "Checked?", "Confidence", "Notes"],
        [[s, c, cf, n] for s, c, cf, n in src_rows])

    # 3. Status Table
    lines += _table_section("3. Status Table",
        ["Epic / Phase", "Status", "Readiness", "What is done", "What remains", "Evidence"],
        [[phase, "⚪", f"{NOT_CONFIRMED}%", NOT_CONFIRMED, NOT_CONFIRMED, NOT_CONFIRMED] for phase in DEFAULT_PHASES])

    # 4. Progress by period/session
    lines += _table_section("4. Progress By Period/Session",
        ["Session / Day", "Plan", "Fact", "Outcome", "Still open"],
        [[NOT_CONFIRMED] * 5])

    # 5. What happened earlier
    lines += _section("5. What Happened Earlier", [
        f"- Timeline of phases: {NOT_CONFIRMED}",
        f"- Important decisions: {NOT_CONFIRMED} (cross-check `wiki/decisions/`)",
        f"- Closed milestones: {NOT_CONFIRMED}",
        f"- Important commits/MRs/PRs: {NOT_CONFIRMED}",
    ])

    # 6. Where we are now — per-repo git inventory
    lines += ["## 6. Where We Are Now", ""]
    if inputs.repos:
        for repo in inputs.repos:
            lines += _git_block(git_inventory(Path(repo)))
    else:
        lines += ["- No repository path provided — git state unknown (low confidence).", ""]
    lines += [
        f"- Stable areas: {NOT_CONFIRMED}",
        f"- Active development areas: {NOT_CONFIRMED}",
        f"- Not-ready areas: {NOT_CONFIRMED}",
        f"- Areas needing review: {NOT_CONFIRMED}",
        "",
    ]

    # 7. Business coverage
    lines += _table_section("7. Backend/Frontend/SDK/Provider Business Coverage",
        ["Business case", "Backend", "Frontend", "SDK", "Provider", "Tests", "Status", "Evidence"],
        [[NOT_CONFIRMED, "⚪", "⚪", "⚪", NOT_CONFIRMED, NOT_CONFIRMED, "⚪", NOT_CONFIRMED]])

    # 8. Provider coverage
    lines += _table_section("8. Provider Coverage",
        ["Provider", "Role", "Code wired?", "Env configured?", "Mock tested?", "Live tested?", "Business cases enabled", "Blocker?", "Evidence"],
        [[NOT_CONFIRMED, NOT_CONFIRMED, "no", "no", "no", "no", NOT_CONFIRMED, "no", NOT_CONFIRMED]])

    # 9. Deploy readiness
    lines += _table_section("9. Deploy Readiness",
        ["Deploy area", "Status", "Evidence", "Blocker?", "Next check"],
        [[area, "⚪", NOT_CONFIRMED, "no", NOT_CONFIRMED] for area in
         ("deployment configs", "Docker/Compose", "CI/CD", "env examples", "health endpoints",
          "DB/Redis/queue", "migrations", "monitoring/logs", "rollback plan", "staging/prod separation")])
    lines += [
        "",
        "_Do not mark deploy blocked without a proven root cause. If deploy is configured and only "
        "verification remains, state: \"Deploy appears configured; remaining work is verification/testing, "
        "not deployment setup.\"_",
        "",
    ]

    # 10. Security Review — ALWAYS present for software projects
    lines += _security_section(inputs)

    # 11. Performance/readiness
    lines += _table_section("11. Performance/Readiness",
        ["Flow/API", "Evidence", "Test coverage", "Risk", "Next action"],
        [[NOT_CONFIRMED] * 5])

    # 12. Tech debt
    lines += _table_section("12. Tech Debt",
        ["Debt item", "Area", "Severity", "Evidence", "Impact", "Fix path", "Priority"],
        [[NOT_CONFIRMED, area, NOT_CONFIRMED, NOT_CONFIRMED, NOT_CONFIRMED, NOT_CONFIRMED, NOT_CONFIRMED]
         for area in ("architecture", "contract/API drift", "test", "security", "deploy/infra",
                      "provider/integration", "frontend UX", "backend/domain", "documentation", "branch/release")])

    # 13. Roadmap forward
    lines += ["## 13. Roadmap Forward", "",
              "- Immediate next steps: " + NOT_CONFIRMED,
              "- Short-term: " + NOT_CONFIRMED,
              "- Mid-term: " + NOT_CONFIRMED,
              "- Release gate: " + NOT_CONFIRMED,
              ""]
    lines += _table(["Priority", "Stage", "Task", "Why it matters", "Dependencies", "Definition of Done"],
                    [[NOT_CONFIRMED] * 6])
    lines += [""]

    # 14. Readiness checklist
    lines += ["## 14. Readiness Checklist", ""]
    lines += [f"- [ ] {item}" for item in READINESS_CHECKLIST]
    lines += [""]

    # 15. Risks
    lines += _table_section("15. Risks",
        ["Risk", "Level", "Why it matters", "What to do"],
        [[NOT_CONFIRMED] * 4])

    # 16. Mismatches and questions
    lines += _section("16. Mismatches And Questions", [
        f"- Docs vs code mismatches: {NOT_CONFIRMED}",
        f"- Chat/log claims vs git evidence mismatches: {NOT_CONFIRMED}",
        f"- Missing evidence: {NOT_CONFIRMED}",
        f"- Manual checks required: {NOT_CONFIRMED}",
        f"- Questions for the team: {NOT_CONFIRMED}",
    ])

    # 17. Next 3 actions
    lines += _section("17. Next 3 Actions", [
        f"1. {NOT_CONFIRMED}",
        f"2. {NOT_CONFIRMED}",
        f"3. {NOT_CONFIRMED}",
    ])

    return "\n".join(lines).rstrip() + "\n"


def _security_section(inputs: AuditInputs) -> list[str]:
    areas = (
        "auth model", "session model", "identity model", "permission model",
        "secrets handling", "env handling", "frontend no-secrets rule", "API trust boundaries",
        "money/custody flow gates", "KYC/PII handling", "webhook/signature verification",
        "admin permissions", "provider credentials", "CORS/CSRF", "rate limiting",
        "input validation", "dependency vulnerabilities", "logging of sensitive data",
        "production DEBUG/dev flags", "release security gates",
    )
    rows = [[area, "⚪", NOT_CONFIRMED, NOT_CONFIRMED, NOT_CONFIRMED] for area in areas]
    block = _table_section("10. Security Review",
        ["Area", "Status", "Evidence", "Risk", "Required check before release"], rows)
    block += [
        "_Release is NOT ready if auth/session or secrets/env rules are unclear, money/custody flows "
        "are ungated, provider credentials are unaccounted for, critical security tests are missing, "
        "release gates are undefined, or real blockers are unresolved._",
        "",
    ]
    return block


def _git_block(inv: GitInventory) -> list[str]:
    if not inv.available:
        return [f"### `{inv.path}`", "", "- Not a git repository or git unavailable (low confidence).", ""]
    lines = [
        f"### `{inv.path}`",
        "",
        f"- Branch: `{inv.branch}`",
        f"- Remote: `{inv.remote}`",
        f"- Upstream: `{inv.upstream}`",
        f"- Divergence: {inv.divergence}",
        f"- Local branches: {inv.local_branches}" + ("  ⚠️ branch sprawl" if inv.local_branches > 10 else ""),
        f"- Uncommitted changes: {inv.uncommitted}",
        f"- Untracked files: {inv.untracked}",
        "- Recent commits:",
    ]
    lines += [f"  - `{c}`" for c in inv.recent_commits] or ["  - (none)"]
    lines.append("")
    return lines


def _section(title: str, body: list[str]) -> list[str]:
    return [f"## {title}", "", *body, ""]


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return out


def _table_section(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    return [f"## {title}", "", *_table(headers, rows), ""]


@click.command()
@click.option("--project", required=True, help="Project name.")
@click.option("--repo", "repos", multiple=True, help="Repository path (repeatable, read-only).")
@click.option("--period", default="entire project", show_default=True)
@click.option("--focus", multiple=True, help="Focus area (repeatable).")
@click.option("--note", "notes", multiple=True, help="Context note / pasted-summary marker (repeatable).")
@click.option("--out", type=click.Path(path_type=Path), help="Write report to a file instead of stdout.")
def cli(project: str, repos: tuple[str, ...], period: str, focus: tuple[str, ...],
        notes: tuple[str, ...], out: Path | None) -> None:
    inputs = AuditInputs(
        project_name=project, repos=list(repos), period=period,
        focus=list(focus), context_notes=list(notes),
    )
    report = audit_report(inputs)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        click.echo(f"wrote {out}")
        return
    click.echo(report)


if __name__ == "__main__":
    cli()
