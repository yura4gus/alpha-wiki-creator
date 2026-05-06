"""Deterministic source-to-wiki ingest pipeline for durable local files."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import click

from tools._models import LintSeverity
from tools.classify import classify
from tools.lint import run_all_checks
from tools.wiki_engine import rebuild_context_brief, rebuild_edges, rebuild_open_questions


@dataclass(frozen=True)
class IngestResult:
    source: Path
    page: Path
    slot: str
    slug: str
    lint_errors: int
    lint_warnings: int


MAX_EXCERPT_LINES = 80


def ingest_files(
    wiki_dir: Path,
    sources: list[Path],
    slot: str | None = None,
    belongs_to: str | None = None,
    resume: bool = False,
) -> list[IngestResult]:
    results: list[IngestResult] = []
    state = _load_state(wiki_dir) if resume else {"completed": []}
    completed = set(state.get("completed", []))
    for source in sources:
        source_key = str(source.resolve())
        if resume and source_key in completed:
            continue
        results.append(_ingest_one(wiki_dir, source, slot=slot, belongs_to=belongs_to))
        if resume:
            completed.add(source_key)
            _write_state(wiki_dir, sorted(completed), failed=[])
    _update_index(wiki_dir, results)
    rebuild_edges(wiki_dir)
    rebuild_context_brief(wiki_dir)
    rebuild_open_questions(wiki_dir)
    findings = run_all_checks(wiki_dir, schema={}, dir_to_type={}, dependency_rules=[])
    lint_errors = sum(1 for finding in findings if finding.severity == LintSeverity.ERROR)
    lint_warnings = sum(1 for finding in findings if finding.severity == LintSeverity.WARNING)
    results = [replace(result, lint_errors=lint_errors, lint_warnings=lint_warnings) for result in results]
    _append_log(wiki_dir, results)
    return results


def ingest_report(
    wiki_dir: Path,
    sources: list[Path],
    slot: str | None = None,
    belongs_to: str | None = None,
    resume: bool = False,
) -> str:
    results = ingest_files(wiki_dir, sources, slot=slot, belongs_to=belongs_to, resume=resume)
    lines = ["# Wiki Ingest", ""]
    if resume:
        lines.append("- Resume mode: enabled")
        lines.append("")
    for result in results:
        lines.append(f"- `{result.source}` -> `{result.page.relative_to(wiki_dir)}` slot={result.slot}")
        lines.append(f"  - slug: [[{result.slug}]]")
        lines.append(f"  - lint: {result.lint_errors} error(s), {result.lint_warnings} warning(s)")
    lines.extend([
        "",
        "## Next Actions",
        "",
        "- Run `/alpha-wiki:query <question>` to verify retrieval.",
        "- Run `/alpha-wiki:status` to inspect gaps, provenance, and graph health.",
    ])
    return "\n".join(lines) + "\n"


def _ingest_one(wiki_dir: Path, source: Path, slot: str | None, belongs_to: str | None) -> IngestResult:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"source not found: {source}")
    if wiki_dir.resolve() in source.resolve().parents and "graph" in source.parts:
        raise ValueError("refusing to ingest generated graph artifacts")
    body = _read_text_source(source)
    artifact = classify(source)
    target_slot = slot or artifact.suggested_slot or _default_slot(wiki_dir, artifact.kind)
    slug = _unique_slug(wiki_dir, _slugify(source.stem))
    title = _title_from_source(source, body)
    page = wiki_dir / target_slot / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(_page_text(source, title, slug, target_slot, artifact.kind, belongs_to, body))
    return IngestResult(
        source=source,
        page=page,
        slot=target_slot,
        slug=slug,
        lint_errors=0,
        lint_warnings=0,
    )


def _update_index(wiki_dir: Path, results: list[IngestResult]) -> None:
    if not results:
        return
    index = wiki_dir / "index.md"
    if index.exists():
        text = index.read_text().rstrip()
    else:
        text = "---\nproject: alpha-wiki\ngenerated: unknown\n---\n# Index"
    if "## Ingested Pages" not in text:
        text += "\n\n## Ingested Pages\n"
    existing = text
    additions = []
    for result in results:
        link = f"[[{result.slug}]]"
        if link in existing:
            continue
        additions.append(f"- {link} -> `{result.slot}/`")
    if additions:
        text += "\n" + "\n".join(additions)
    index.write_text(text.rstrip() + "\n")


def _page_text(source: Path, title: str, slug: str, slot: str, kind: str, belongs_to: str | None, body: str) -> str:
    today = date.today().isoformat()
    frontmatter = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "date_updated": today,
        "source": f"[[{_slugify(source.stem)}]]",
        "source_file": str(source),
        "kind": kind,
    }
    if belongs_to:
        frontmatter["belongs_to"] = _wikilink(belongs_to)
    if slot.startswith("decisions"):
        frontmatter["date"] = today
    if slot.startswith("contracts"):
        frontmatter.setdefault("transport", "rest")
        frontmatter.setdefault("version", "v0")
        if belongs_to:
            frontmatter["service"] = _wikilink(belongs_to)
    excerpt, truncated = _excerpt(body.splitlines())
    open_questions = _open_questions(body)
    risk_lines = _risk_lines(body)
    lines = [
        "---",
        *[f"{key}: {value}" for key, value in frontmatter.items()],
        "---",
        f"# {title}",
        "",
        "## Provenance",
        "",
        f"- Source file: `{source}`",
        f"- Ingested: {today}",
        f"- Classifier kind: `{kind}`",
        "",
        "## Source Excerpt",
        "",
        excerpt or "_(empty source)_",
        "",
    ]
    if truncated:
        lines.extend([
            "> Source excerpt truncated. Re-run ingest in smaller sections if the omitted portion contains decisions, risks, or contracts.",
            "",
        ])
    lines.extend([
        "## Risks",
        "",
    ])
    lines.extend(risk_lines or ["_(none detected)_"])
    lines.extend([
        "",
        "## Open Questions",
        "",
    ])
    lines.extend(open_questions or ["_(none detected)_"])
    return "\n".join(lines) + "\n"


def _default_slot(wiki_dir: Path, kind: str) -> str:
    if kind in {"adr", "postmortem"}:
        return "decisions"
    if kind in {"prd", "rfc", "runbook", "diagram", "markdown"}:
        return "specs" if (wiki_dir / "specs").exists() else "sources"
    if kind == "transcript":
        return "sources"
    return "sources"


def _title_from_source(source: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return source.stem.replace("-", " ").replace("_", " ").title()


def _read_text_source(source: Path) -> str:
    raw = source.read_bytes()
    if b"\x00" in raw:
        raise ValueError(f"refusing to ingest likely binary/unparseable source: {source}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _excerpt(lines: Iterable[str]) -> tuple[str, bool]:
    materialized = list(lines)
    excerpt = "\n".join(materialized[:MAX_EXCERPT_LINES]).strip()
    return excerpt, len(materialized) > MAX_EXCERPT_LINES


def _open_questions(text: str) -> list[str]:
    questions = []
    for line in text.splitlines():
        stripped = line.strip("-* \t")
        if "?" in stripped:
            questions.append(f"- {stripped}")
        if len(questions) >= 10:
            break
    return questions


def _risk_lines(text: str) -> list[str]:
    risks = []
    for line in text.splitlines():
        stripped = line.strip("-* \t")
        lower = stripped.lower()
        if lower.startswith("risk") or " risk:" in lower or "blocked" in lower:
            risks.append(f"- {stripped}")
        if len(risks) >= 10:
            break
    return risks


def _append_log(wiki_dir: Path, results: list[IngestResult]) -> None:
    if not results:
        return
    log = wiki_dir / "log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        log.write_text("# Log\n")
    today = date.today().isoformat()
    pages = ", ".join(f"[[{result.slug}]]" for result in results)
    log.write_text(log.read_text().rstrip() + f"\n\n## [{today}] ingest | deterministic pipeline | pages={pages}\n")


def _unique_slug(wiki_dir: Path, base: str) -> str:
    existing = {path.stem for path in wiki_dir.rglob("*.md")}
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def _wikilink(value: str) -> str:
    if value.startswith("[["):
        return value
    return f"[[{value}]]"


def _state_path(wiki_dir: Path) -> Path:
    return wiki_dir / "graph" / "ingest_state.json"


def _load_state(wiki_dir: Path) -> dict:
    path = _state_path(wiki_dir)
    if not path.exists():
        return {"completed": []}
    return json.loads(path.read_text())


def _write_state(wiki_dir: Path, completed: list[str], failed: list[str]) -> None:
    path = _state_path(wiki_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "updated": date.today().isoformat(),
        "completed": completed,
        "failed": failed,
    }, indent=2, sort_keys=True) + "\n")


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--slot", help="Target wiki slot, for example decisions, specs, modules, contracts/rest.")
@click.option("--belongs-to", help="Typed cluster owner/service slug.")
@click.option("--resume", is_flag=True, help="Skip sources already recorded in graph/ingest_state.json.")
@click.argument("sources", nargs=-1, type=click.Path(path_type=Path, exists=True))
def cli(wiki_dir: Path, slot: str | None, belongs_to: str | None, resume: bool, sources: tuple[Path, ...]) -> None:
    if not sources:
        raise click.UsageError("at least one source path is required")
    click.echo(ingest_report(wiki_dir, list(sources), slot=slot, belongs_to=belongs_to, resume=resume))


if __name__ == "__main__":
    cli()
