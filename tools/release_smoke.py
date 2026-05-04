"""Fresh-project release smoke for Alpha-Wiki."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click

from scripts.bootstrap import bootstrap
from scripts.install_codex import install_codex_skills
from scripts.interview import InterviewConfig
from tools.doctor import run_doctor
from tools.ingest_pipeline import ingest_files
from tools.render_dot import write_dot
from tools.render_html import render_html
from tools.render_mermaid import write_mermaid
from tools.review import review_report
from tools.status import status_report
from tools.wiki_search import search_wiki


@dataclass(frozen=True)
class SmokeResult:
    project_dir: Path
    codex_home: Path
    checks: list[tuple[str, str, str]]

    @property
    def passed(self) -> bool:
        return all(status == "PASS" for _, status, _ in self.checks)

    def to_markdown(self) -> str:
        lines = [
            "# Alpha-Wiki Release Smoke",
            "",
            f"- Date: {date.today().isoformat()}",
            f"- Smoke verdict: {'PASS' if self.passed else 'FAIL'}",
            f"- Project: `{self.project_dir}`",
            f"- Codex home: `{self.codex_home}`",
            "",
            "## Checks",
            "",
        ]
        for name, status, message in self.checks:
            lines.append(f"- {status} `{name}`: {message}")
        return "\n".join(lines) + "\n"


def run_release_smoke(base_dir: Path | None = None) -> SmokeResult:
    if base_dir is None:
        temp = tempfile.TemporaryDirectory(prefix="alpha-wiki-release-smoke-")
        base = Path(temp.name)
    else:
        temp = None
        base = base_dir
        base.mkdir(parents=True, exist_ok=True)

    try:
        project = base / "project"
        codex_home = base / "codex-home"
        checks: list[tuple[str, str, str]] = []

        cfg = InterviewConfig(
            project_name="alpha-wiki-release-smoke",
            project_description="Fresh install release smoke",
            wiki_dir="wiki",
            preset="software-project",
            overlay="none",
            custom_entity_types=None,
            i18n_languages=["en"],
            hooks="all",
            ci=True,
            schema_evolve_mode="gated",
        )
        bootstrap(target=project, config=cfg)
        install_codex_skills(codex_home / "skills")
        old_codex_home = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(codex_home)
        try:
            doctor = run_doctor(project, platform="both", refresh=True)
        finally:
            if old_codex_home is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old_codex_home
        _record(checks, "Claude/Codex doctor", not doctor.failures, f"{len(doctor.passes)} pass, {len(doctor.warnings)} warn, {len(doctor.failures)} fail")

        wiki = project / "wiki"
        _write_page(
            wiki / "modules" / "smoke-service.md",
            "title: Smoke Service\nslug: smoke-service\nstatus: stable\ndate_updated: 2026-05-05\nsource: [[release-smoke]]",
            "# Smoke Service\n",
        )
        _write_page(
            wiki / "modules" / "smoke-module.md",
            "title: Smoke Module\nslug: smoke-module\nstatus: stable\ndate_updated: 2026-05-05\nbelongs_to: [[smoke-service]]\nsource: [[release-smoke]]",
            "# Smoke Module\n",
        )
        source = project / "raw" / "docs" / "release-smoke-prd.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "# Release Smoke PRD\n\n"
            "The release smoke verifies bootstrap, Codex adapter install, ingest, query, status, review, and render exports.\n"
        )
        ingest = ingest_files(wiki, [source], slot="specs", belongs_to="smoke-service")
        hits = search_wiki(wiki, "release smoke", limit=3)
        status = status_report(wiki)
        review = review_report(wiki)
        _record(
            checks,
            "Ingest/query/status/review",
            bool(ingest) and bool(hits) and "Wiki Status Report" in status and "Wiki Review" in review,
            f"{len(ingest)} ingested page(s), {len(hits)} query hit(s)",
        )

        mermaid = write_mermaid(wiki)
        dot = write_dot(wiki)
        html = render_html(wiki)
        _record(
            checks,
            "Render exports",
            mermaid.exists() and dot.exists() and (html / "index.html").exists(),
            "Mermaid, DOT, and static HTML exports exist",
        )

        return SmokeResult(project_dir=project, codex_home=codex_home, checks=checks)
    finally:
        if temp is not None:
            temp.cleanup()


def _record(checks: list[tuple[str, str, str]], name: str, passed: bool, message: str) -> None:
    checks.append((name, "PASS" if passed else "FAIL", message))


def _write_page(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


@click.command()
@click.option("--base-dir", type=click.Path(path_type=Path, file_okay=False), help="Optional directory for smoke artifacts.")
def cli(base_dir: Path | None) -> None:
    result = run_release_smoke(base_dir=base_dir)
    click.echo(result.to_markdown())
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
