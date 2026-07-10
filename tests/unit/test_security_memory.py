"""Security memory: scaffolding, capture detection, review integration, lint safety.

Deterministic; no wall-clock coupling. Security here means project-memory hygiene
(did the wiki capture the decision?), not a code scanner.
"""
from pathlib import Path

from scripts.bootstrap import bootstrap
from scripts.interview import InterviewConfig
from tools._models import LintSeverity
from tools.lint import run_all_checks
from tools.review import review_report
from tools.security import (
    PLACEHOLDER_MARKER,
    SECURITY_PAGES,
    scaffold_security_pages,
    security_memory,
    security_release_blockers,
)


def _config() -> InterviewConfig:
    return InterviewConfig(
        project_name="demo",
        project_description="Security memory smoke",
        wiki_dir="wiki",
        preset="software-project",
        overlay="none",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="all",
        ci=True,
        schema_evolve_mode="gated",
    )


def test_scaffold_creates_minimal_placeholders(tmp_path: Path):
    wiki = tmp_path / "wiki"
    created = scaffold_security_pages(wiki)

    assert len(created) == len(SECURITY_PAGES)
    overview = (wiki / "security" / "security-overview.md").read_text()
    assert "status: placeholder" in overview
    assert PLACEHOLDER_MARKER in overview


def test_scaffold_is_idempotent_and_non_destructive(tmp_path: Path):
    wiki = tmp_path / "wiki"
    scaffold_security_pages(wiki)
    real = wiki / "security" / "auth-session.md"
    real.write_text("---\ntitle: Auth\nslug: auth-session\nstatus: stable\n---\n\nJWT, 30m sessions.\n")

    created_again = scaffold_security_pages(wiki)

    assert real.read_text().endswith("JWT, 30m sessions.\n")
    assert all("auth-session.md" not in str(p) for p in created_again)


def test_security_memory_is_empty_before_scaffold(tmp_path: Path):
    mem = security_memory(tmp_path / "wiki")
    assert mem.security_dir_exists is False
    assert mem.captured == []
    assert mem.has_security_memory is False


def test_placeholders_are_not_counted_as_captured(tmp_path: Path):
    wiki = tmp_path / "wiki"
    scaffold_security_pages(wiki)
    mem = security_memory(wiki)
    assert mem.captured == []
    assert set(mem.missing) == {p.slug for p in SECURITY_PAGES}


def test_real_content_is_counted_as_captured(tmp_path: Path):
    wiki = tmp_path / "wiki"
    scaffold_security_pages(wiki)
    (wiki / "security" / "auth-session.md").write_text(
        "---\ntitle: Auth\nslug: auth-session\nstatus: stable\n---\n\nOAuth2 + 30m JWT sessions.\n"
    )
    mem = security_memory(wiki)
    assert "auth-session" in mem.captured
    assert "auth-session" not in mem.missing


def test_release_blockers_flag_missing_security(tmp_path: Path):
    wiki = tmp_path / "wiki"
    assert security_release_blockers(wiki) == ["no security/ memory pages exist"]

    scaffold_security_pages(wiki)  # placeholders only
    blockers = security_release_blockers(wiki)
    assert any("critical security pages not captured" in b for b in blockers)


def test_review_reports_scope_and_security_sections(tmp_path: Path):
    bootstrap(target=tmp_path, config=_config())
    wiki = tmp_path / "wiki"
    scaffold_security_pages(wiki)

    report = review_report(wiki)

    assert "## Scope" in report
    assert "## Security Memory" in report
    assert "## Release Readiness" in report
    # No source manifest and only placeholder security => not ready.
    assert "Release readiness: NOT READY" in report


def test_scaffolded_security_pages_do_not_break_lint(tmp_path: Path):
    bootstrap(target=tmp_path, config=_config())
    wiki = tmp_path / "wiki"
    scaffold_security_pages(wiki)

    findings = run_all_checks(wiki, schema={}, dir_to_type={}, dependency_rules=[])
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    assert not errors, f"security placeholders introduced lint errors: {errors}"
