"""Deterministic security-memory scaffolding and review for Alpha-Wiki.

This is project-memory hygiene, NOT a security scanner. It checks whether the
wiki has *captured* the security decisions an agent must not forget, and it
scaffolds minimal placeholder pages so those slots are visible but never
hallucinated. It makes no claim about the actual security of the code.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click

# Marker written into placeholder bodies; presence means "not yet captured".
PLACEHOLDER_MARKER = "_(no evidence captured yet — fill from real sources during ingest)_"
PLACEHOLDER_STATUSES = {"placeholder", "stub", "empty", "todo"}


@dataclass(frozen=True)
class SecurityPage:
    filename: str
    slug: str
    title: str
    questions: tuple[str, ...]


SECURITY_PAGES: tuple[SecurityPage, ...] = (
    SecurityPage(
        "security-overview.md", "security-overview", "Security Overview",
        ("What is the overall security posture?", "Which areas are frozen for safety?",
         "What must pass before a security-relevant release?"),
    ),
    SecurityPage(
        "auth-session.md", "auth-session", "Auth & Session Model",
        ("What is the authentication model?", "What is the session model / lifetime?",
         "Where are tokens issued, stored, and validated?"),
    ),
    SecurityPage(
        "identity-permissions.md", "identity-permissions", "Identity & Permissions",
        ("What is the identity model?", "What is the permission / RBAC model?",
         "What are the admin-access assumptions?"),
    ),
    SecurityPage(
        "secrets-env.md", "secrets-env", "Secrets & Environment",
        ("How are secrets handled?", "How is env configuration handled?",
         "Is the frontend-no-secrets rule enforced?"),
    ),
    SecurityPage(
        "api-boundaries.md", "api-boundaries", "API Trust Boundaries",
        ("What are the API trust boundaries?", "What are the webhook/signature assumptions?",
         "What external provider assumptions exist?"),
    ),
    SecurityPage(
        "release-security-gates.md", "release-security-gates", "Release Security Gates",
        ("Are money/custody flows frozen or gated?", "Which security checks must pass before release?",
         "What are the KYC/PII handling gates?"),
    ),
    SecurityPage(
        "known-security-blockers.md", "known-security-blockers", "Known Security Blockers",
        ("What security blockers remain open?", "What custody / private-key assumptions are unverified?",
         "What required security tests are missing?"),
    ),
)


def scaffold_security_pages(wiki_dir: Path) -> list[Path]:
    """Create minimal placeholder security pages if they do not already exist.

    Existing pages are never overwritten. Returns the paths that were created.
    """
    security_dir = wiki_dir / "security"
    security_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for page in SECURITY_PAGES:
        target = security_dir / page.filename
        if target.exists():
            continue
        target.write_text(_placeholder_body(page))
        created.append(target)
    return created


def _placeholder_body(page: SecurityPage) -> str:
    questions = "\n".join(f"- {q}" for q in page.questions)
    return (
        f"---\n"
        f"title: {page.title}\n"
        f"slug: {page.slug}\n"
        f"status: placeholder\n"
        f"---\n\n"
        f"# {page.title}\n\n"
        f"{PLACEHOLDER_MARKER}\n\n"
        f"## Questions to answer\n\n"
        f"{questions}\n"
    )


def _is_captured(path: Path) -> bool:
    """A page counts as captured when it exists with real content, not a placeholder."""
    if not path.exists():
        return False
    text = path.read_text()
    if PLACEHOLDER_MARKER in text:
        return False
    for status in PLACEHOLDER_STATUSES:
        if f"status: {status}" in text:
            return False
    # Require some body beyond frontmatter + heading.
    body = text.split("---", 2)[-1]
    meaningful = [line for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return len(meaningful) > 0


@dataclass(frozen=True)
class SecurityMemory:
    security_dir_exists: bool
    captured: list[str]
    missing: list[str]
    blockers_page_present: bool

    @property
    def has_security_memory(self) -> bool:
        return self.security_dir_exists and bool(self.captured)


def security_memory(wiki_dir: Path) -> SecurityMemory:
    security_dir = wiki_dir / "security"
    captured: list[str] = []
    missing: list[str] = []
    for page in SECURITY_PAGES:
        if _is_captured(security_dir / page.filename):
            captured.append(page.slug)
        else:
            missing.append(page.slug)
    return SecurityMemory(
        security_dir_exists=security_dir.exists(),
        captured=captured,
        missing=missing,
        blockers_page_present=(security_dir / "known-security-blockers.md").exists(),
    )


def security_review_section(wiki_dir: Path) -> str:
    """Markdown block summarizing captured vs. missing security memory."""
    mem = security_memory(wiki_dir)
    lines = ["## Security Memory", ""]
    if not mem.security_dir_exists:
        lines.append("- No `security/` pages found. Run `scaffold_security_pages` or `/alpha-wiki:review --scaffold-security`.")
        lines.append("- Release should not be called ready until auth/session/secrets/custody decisions are captured.")
        return "\n".join(lines) + "\n"
    lines.append(f"- Captured: {', '.join(mem.captured) if mem.captured else '_(none)_'}")
    lines.append(f"- Missing / placeholder: {', '.join(mem.missing) if mem.missing else '_(none)_'}")
    if mem.missing:
        lines.append("")
        lines.append("Security decisions still to capture before a security-relevant release:")
        for slug in mem.missing:
            page = next(p for p in SECURITY_PAGES if p.slug == slug)
            lines.append(f"- **{page.title}**: {page.questions[0]}")
    return "\n".join(lines) + "\n"


def security_release_blockers(wiki_dir: Path) -> list[str]:
    """Reasons a security-relevant release should NOT be called ready. Empty = clear."""
    mem = security_memory(wiki_dir)
    blockers: list[str] = []
    if not mem.security_dir_exists:
        blockers.append("no security/ memory pages exist")
        return blockers
    critical = {"auth-session", "secrets-env", "release-security-gates"}
    uncaptured_critical = sorted(critical & set(mem.missing))
    if uncaptured_critical:
        blockers.append(f"critical security pages not captured: {', '.join(uncaptured_critical)}")
    return blockers


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--scaffold", is_flag=True, help="Create missing placeholder security pages.")
def cli(wiki_dir: Path, scaffold: bool) -> None:
    if scaffold:
        created = scaffold_security_pages(wiki_dir)
        click.echo(f"created {len(created)} security placeholder(s)")
    click.echo(security_review_section(wiki_dir))


if __name__ == "__main__":
    cli()
