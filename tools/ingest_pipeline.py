"""Deterministic source-to-wiki ingest pipeline for durable local files."""
from __future__ import annotations

import json
import hashlib
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import click

from tools._models import LintSeverity
from tools.classify import classify
from tools.lint import run_all_checks
from tools.wiki_engine import rebuild_context_brief, rebuild_edges, rebuild_open_questions, scan_wiki


@dataclass(frozen=True)
class IngestResult:
    source: Path
    page: Path
    slot: str
    slug: str
    lint_errors: int
    lint_warnings: int
    created: bool = True


MAX_EXCERPT_LINES = 80


def ingest_files(
    wiki_dir: Path,
    sources: list[Path],
    slot: str | None = None,
    belongs_to: str | None = None,
    resume: bool = False,
) -> list[IngestResult]:
    results: list[IngestResult] = []
    state = _load_state(wiki_dir)
    recovered = None
    if state.get("pending"):
        if state["pending"]["source"] not in {str(source.resolve()) for source in sources}:
            raise ValueError("unfinished ingest: retry with the original pending source")
        recovered = _finish_pending(wiki_dir, state)
        results.append(recovered)
        state = _load_state(wiki_dir)
    completed = set(state.get("completed", []))
    source_hashes = state.get("source_hashes", {})
    for source in sources:
        source_key = str(source.resolve())
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if recovered and source_key == str(recovered.source.resolve()):
            continue
        if resume and source_key in completed and source_hashes.get(source_key) == source_hash:
            continue
        result = _ingest_one(wiki_dir, source, slot=slot, belongs_to=belongs_to)
        if result.created:
            result = _finish_pending(wiki_dir, _load_state(wiki_dir))
            state = _load_state(wiki_dir)
            completed = set(state.get("completed", []))
            source_hashes = state.get("source_hashes", {})
        results.append(result)
    findings = run_all_checks(wiki_dir, schema={}, dir_to_type={}, dependency_rules=[])
    lint_errors = sum(1 for finding in findings if finding.severity == LintSeverity.ERROR)
    lint_warnings = sum(1 for finding in findings if finding.severity == LintSeverity.WARNING)
    results = [replace(result, lint_errors=lint_errors, lint_warnings=lint_warnings) for result in results]
    return results


def _out_of_scope_terms(wiki_dir: Path) -> list[str]:
    """Out-of-scope modules recorded in the init source manifest, if any."""
    manifest = wiki_dir.parent / "raw" / "docs" / "source-manifest.md"
    if not manifest.exists():
        return []
    for line in manifest.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("- Out of scope:"):
            value = stripped.split(":", 1)[1].strip()
            if not value or value.startswith("_(") or "none recorded" in value:
                return []
            return [term.strip() for term in value.replace(";", ",").split(",") if term.strip()]
    return []


def scope_warnings(wiki_dir: Path, sources: list[Path]) -> list[str]:
    """Warning-only: flag sources whose path matches an out-of-scope module.

    Never blocks ingest — records active scope discipline so an agent does not
    silently pull deferred modules (e.g. Launchpad when scope is Web Wallet).
    """
    terms = _out_of_scope_terms(wiki_dir)
    warnings: list[str] = []
    for source in sources:
        low = str(source).lower()
        for term in terms:
            if term.lower() and term.lower() in low:
                warnings.append(f"`{source}` matches out-of-scope module '{term}' — confirm before ingesting")
                break
    return warnings


def ingest_report(
    wiki_dir: Path,
    sources: list[Path],
    slot: str | None = None,
    belongs_to: str | None = None,
    resume: bool = False,
) -> str:
    warnings = scope_warnings(wiki_dir, sources)
    results = ingest_files(wiki_dir, sources, slot=slot, belongs_to=belongs_to, resume=resume)
    lines = ["# Wiki Ingest", ""]
    if resume:
        lines.append("- Resume mode: enabled")
        lines.append("")
    if warnings:
        lines.append("## Scope Warnings")
        lines.append("")
        lines.extend(f"- ⚠️ {warning}" for warning in warnings)
        lines.append("")
    for result in results:
        lines.append(f"- `{result.source}` -> `{result.page.relative_to(wiki_dir)}` slot={result.slot}")
        lines.append(f"  - slug: [[{result.slug}]]")
        lines.append(f"  - lint: {result.lint_errors} error(s), {result.lint_warnings} warning(s)")
        if not result.created:
            lines.append("  - Existing source owner preserved. Use document_worker plan for source drift; no import or journal entry was created.")
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
    if source.resolve().is_relative_to(wiki_dir.resolve()):
        relative = source.resolve().relative_to(wiki_dir.resolve())
        if any(part in {"graph", "render", "outputs"} or part.startswith(".") for part in relative.parts[:-1]):
            raise ValueError("refusing to ingest generated graph/render artifacts")
    body = _read_text_source(source)
    owners = []
    for candidate in scan_wiki(wiki_dir):
        stored = candidate.frontmatter.get("source_files") or []
        stored = [stored] if isinstance(stored, str) else stored
        if not isinstance(stored, list):
            raise ValueError(f"{candidate.path}: source_files must be a path list")
        stored = list(stored)
        if candidate.frontmatter.get("source_file"):
            stored.append(candidate.frontmatter["source_file"])
        for value in stored:
            path = Path(str(value))
            project = _project_root(wiki_dir)
            path = path if path.is_absolute() else project / path
            if path.resolve() == source.resolve():
                owners.append(candidate)
                break
    if len(owners) > 1:
        raise ValueError(f"source has multiple existing wiki owners; select and reconcile them explicitly: {source}")
    if owners:
        page = Path(owners[0].path)
        return IngestResult(source, page, str(page.parent.relative_to(wiki_dir)), owners[0].slug, 0, 0, created=False)
    artifact = classify(source)
    target_slot = slot or artifact.suggested_slot or _default_slot(wiki_dir, artifact.kind)
    slug = _unique_slug(wiki_dir, _slugify(source.stem))
    title = _title_from_source(source, body)
    page = wiki_dir / target_slot / f"{slug}.md"
    relative_page = str(page.relative_to(wiki_dir))
    _pending_page(wiki_dir, relative_page)
    state = _load_state(wiki_dir)
    _write_state(wiki_dir, state.get("completed", []), state.get("failed", []),
                 state.get("source_hashes", {}), pending={
                     "source": str(source.resolve()),
                     "transaction_id": uuid.uuid4().hex,
                     "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "page": relative_page, "slot": target_slot, "slug": slug,
                     "text": _page_text(source, title, slug, target_slot, artifact.kind, belongs_to, body, wiki_dir=wiki_dir),
                 })
    return IngestResult(
        source=source,
        page=page,
        slot=target_slot,
        slug=slug,
        lint_errors=0,
        lint_warnings=0,
    )


def _pending_page(wiki_dir: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or any(part in {"..", "graph", "render", "outputs"} or part.startswith(".") for part in path.parts):
        raise ValueError("ingest page must remain inside a source-page directory")
    target = wiki_dir / path
    if target.is_symlink() or not target.resolve().is_relative_to(wiki_dir.resolve()):
        raise ValueError("ingest page must remain inside the wiki")
    return target


def _finish_pending(wiki_dir: Path, state: dict) -> IngestResult:
    """Finalize one captured page before checkpointing, including crash retries."""
    from tools.document_maintenance import _atomic_text

    pending = state["pending"]
    source = Path(pending["source"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != pending["source_sha256"]:
        raise ValueError("stale pending ingest source; preserve ingest_state.json and reconcile the source")
    page = _pending_page(wiki_dir, pending["page"])
    if page.exists() and page.read_text() != pending["text"]:
        raise ValueError("concurrent edit to pending ingest page; preserve it and reconcile before retry")
    page.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(page, pending["text"])
    result = IngestResult(source, page, pending["slot"], pending["slug"], 0, 0)
    _update_index(wiki_dir, [result])
    _append_log(wiki_dir, [result], transaction_id=pending["transaction_id"])
    rebuild_edges(wiki_dir)
    rebuild_context_brief(wiki_dir)
    rebuild_open_questions(wiki_dir)
    completed = set(state.get("completed", [])) | {pending["source"]}
    hashes = dict(state.get("source_hashes", {}))
    hashes[pending["source"]] = pending["source_sha256"]
    _write_state(wiki_dir, sorted(completed), [], hashes)
    return result


def _update_index(wiki_dir: Path, results: list[IngestResult]) -> None:
    from tools.document_maintenance import _atomic_text

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
    _atomic_text(index, text.rstrip() + "\n")


def _project_root(wiki_dir: Path) -> Path:
    return next((parent for parent in wiki_dir.resolve().parents
                 if (parent / ".alpha-wiki/config.yaml").is_file()), wiki_dir.resolve().parent)


def _source_binding(wiki_dir: Path, source: Path) -> str:
    path = source.resolve()
    try:
        return path.relative_to(_project_root(wiki_dir)).as_posix()
    except ValueError:
        return str(path)


def _page_text(source: Path, title: str, slug: str, slot: str, kind: str, belongs_to: str | None, body: str, *, wiki_dir: Path) -> str:
    today = date.today().isoformat()
    source_binding = _source_binding(wiki_dir, source)
    frontmatter = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "date_updated": today,
        "source": f"[[{_slugify(source.stem)}]]",
        "source_file": json.dumps(source_binding, ensure_ascii=False),
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
        f"- Source file: `{source_binding}`",
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


def _append_log(wiki_dir: Path, results: list[IngestResult], *, transaction_id: str | None = None) -> None:
    from tools.document_maintenance import _atomic_text

    if not results:
        return
    log = wiki_dir / "log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        log.write_text("# Log\n")
    text = log.read_text()
    marker = f" | import={transaction_id}" if transaction_id else ""
    if marker and any(line.endswith(marker) for line in text.splitlines()):
        return
    today = date.today().isoformat()
    pages = ", ".join(f"[[{result.slug}]]" for result in results)
    _atomic_text(log, text.rstrip() + f"\n\n## [{today}] ingest | deterministic pipeline | pages={pages}{marker}\n")


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


def _write_state(wiki_dir: Path, completed: list[str], failed: list[str], source_hashes: dict | None = None,
                 pending: dict | None = None) -> None:
    from tools.document_maintenance import _atomic_text

    path = _state_path(wiki_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    ignore = path.parent / ".gitignore"
    ignore_text = ignore.read_text() if ignore.exists() else ""
    if "/ingest_state.json" not in ignore_text.splitlines():
        _atomic_text(ignore, ignore_text.rstrip() + "\n/ingest_state.json\n")
    _atomic_text(path, json.dumps({
        "updated": date.today().isoformat(),
        "completed": completed,
        "failed": failed,
        "source_hashes": source_hashes or {},
        "pending": pending,
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
