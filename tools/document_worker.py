"""Deterministic governance for a small, maintained document canon."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

import click
import yaml


UPDATE_OPERATIONS = {
    "document-update",
    "document-register",
    "document-rename",
    "ingest",
    "evolve",
    "update",
}
ADD_OPERATIONS = {"document-register", "ingest", "bootstrap"}
DELETE_OPERATIONS = {"document-retire", "document-rename"}


@dataclass(frozen=True)
class DocumentPolicy:
    enabled: bool
    global_log: PurePosixPath
    canonical_files: frozenset[PurePosixPath]
    canonical_roots: tuple[PurePosixPath, ...]
    excluded_files: frozenset[PurePosixPath]
    excluded_roots: tuple[PurePosixPath, ...]

    def is_canonical(self, path: PurePosixPath) -> bool:
        if not path.parts or path.parts[0] in {"raw", ".git", ".alpha-wiki"}:
            return False
        if any(_is_within(path, self.global_log.parent / name) for name in ("graph", "render", "outputs")):
            return False
        if path.suffix.lower() != ".md":
            return False
        if path == self.global_log or path in self.excluded_files:
            return False
        if any(_is_within(path, root) for root in self.excluded_roots):
            return False
        return path in self.canonical_files or any(
            _is_within(path, root) for root in self.canonical_roots
        )


@dataclass(frozen=True)
class DocumentChange:
    status: str
    path: PurePosixPath
    old_path: PurePosixPath | None = None


def load_policy(config_path: Path, *, content: str | None = None) -> DocumentPolicy:
    data = yaml.safe_load(config_path.read_text() if content is None else content) or {}
    if not isinstance(data, dict):
        raise ValueError("configuration must be a YAML mapping")
    raw = data.get("document_governance") or {}
    if not isinstance(raw, dict):
        raise ValueError("document_governance must be a YAML mapping")
    for key in ("canonical_files", "canonical_roots", "excluded_files", "excluded_roots"):
        if not isinstance(raw.get(key, []), list):
            raise ValueError(f"document_governance.{key} must be a list of repository paths")
    return DocumentPolicy(
        enabled=bool(raw.get("enabled", False)),
        global_log=_posix(raw.get("global_log", "wiki/log.md")),
        canonical_files=frozenset(_posix(value) for value in raw.get("canonical_files", [])),
        canonical_roots=tuple(_posix(value) for value in raw.get("canonical_roots", [])),
        excluded_files=frozenset(_posix(value) for value in raw.get("excluded_files", [])),
        excluded_roots=tuple(_posix(value) for value in raw.get("excluded_roots", [])),
    )


def collect_changes(
    root: Path,
    *,
    staged: bool = False,
    base: str | None = None,
) -> list[DocumentChange]:
    args = ["diff"]
    if staged:
        args.append("--cached")
    elif base:
        args.append(base)
    elif not _has_head(root):
        args.append("--cached")
    else:
        args.append("HEAD")
    args.extend(["--name-status", "-z", "--find-renames", "--"])
    output = _git(root, args)
    changes = _parse_name_status(output)

    if not staged and base is None:
        untracked = _git(root, ["ls-files", "-z", "--others", "--exclude-standard"])
        known = {change.path for change in changes}
        for line in filter(None, untracked.split("\0")):
            path = _posix(line)
            if path not in known:
                changes.append(DocumentChange("A", path))
    return changes


def check_document_governance(
    root: Path,
    config_path: Path,
    *,
    staged: bool = False,
    base: str | None = None,
) -> list[str]:
    root = root.resolve()
    config_path = config_path.resolve() if config_path.is_absolute() else (root / config_path).resolve()
    policy = load_policy(config_path, content=_git(root, ["show", f":{_relative(root, config_path)}"]) if staged else None)
    if not policy.enabled:
        return []

    from tools.document_maintenance import hierarchy_findings
    hierarchy = hierarchy_findings(root, config_path, staged=staged)

    changes = collect_changes(root, staged=staged, base=base)
    canonical = [change for change in changes if _governed_change(policy, change)]
    entries = _added_log_entries(root, policy.global_log, staged=staged, base=base)
    if not canonical and not any(_operation(entry).startswith("document-") for entry in entries):
        return hierarchy
    bootstrap = any(_operation(entry) == "bootstrap" for entry in entries)
    changed_ids: set[str] = set()
    findings: list[str] = list(hierarchy)

    for change in canonical:
        required = _required_identifiers(root, change, policy, staged=staged, base=base)
        changed_ids.update(required)
        matches = [entry for entry in entries if required & _entry_identifiers(entry)]
        operation_set = {_operation(entry) for entry in matches}

        if change.status == "A" and bootstrap:
            continue
        if not matches:
            findings.append(
                f"{change.path}: canonical document changed without a matching {policy.global_log} entry"
            )
            continue
        if change.status == "A" and not (operation_set & ADD_OPERATIONS):
            findings.append(
                f"{change.path}: new canonical document requires `ingest` or `document-register`"
            )
        elif change.status == "D" and not (operation_set & DELETE_OPERATIONS):
            findings.append(
                f"{change.path}: removed canonical document requires `document-retire` or `document-rename`"
            )
        elif change.status == "R" and "document-rename" not in operation_set:
            findings.append(f"{change.path}: renamed canonical document requires `document-rename`")
        elif change.status == "M" and not (operation_set & UPDATE_OPERATIONS):
            findings.append(f"{change.path}: unsupported document log operation: {sorted(operation_set)}")

    for entry in entries:
        if not _operation(entry).startswith("document-"):
            continue
        for identifier in _entry_identifiers(entry):
            if identifier not in changed_ids:
                findings.append(
                    f"{policy.global_log}: {identifier} is logged by `{_operation(entry)}` but the document did not change"
                )
    return findings


def record_change(
    root: Path,
    config_path: Path,
    documents: tuple[Path, ...],
    summary: str,
    *,
    operation: str | None = None,
    allow_new: bool = False,
) -> str:
    root = root.resolve()
    config_path = config_path.resolve() if config_path.is_absolute() else (root / config_path).resolve()
    policy = load_policy(config_path)
    if not policy.enabled:
        raise ValueError("document governance is disabled in .alpha-wiki/config.yaml")
    changes = collect_changes(root)
    by_path = {change.path: change for change in changes}
    selected: list[DocumentChange] = []
    for document in documents:
        relative = _relative(root, document)
        change = by_path.get(relative)
        if change is None:
            raise ValueError(f"{relative} has no uncommitted document change")
        if not _governed_change(policy, change):
            raise ValueError(f"{relative} is not in the configured canonical document set")
        selected.append(change)

    inferred = operation or _infer_operation(selected)
    if any(change.status == "A" for change in selected) and not allow_new:
        raise ValueError("registering a new canonical document requires --allow-new")
    if inferred not in {"document-update", "document-register", "document-retire", "document-rename"}:
        raise ValueError(f"unsupported operation: {inferred}")
    allowed = {"A": ADD_OPERATIONS, "M": UPDATE_OPERATIONS,
               "D": DELETE_OPERATIONS, "R": {"document-rename"}}
    if any(inferred not in allowed.get(change.status, set()) for change in selected):
        raise ValueError("use separate records for registration, updates, retirement, and renames")

    clean_summary = " ".join(summary.split())
    if not clean_summary:
        raise ValueError("summary must not be empty")
    paths: list[str] = []
    for change in selected:
        if change.old_path is not None:
            paths.append(f"`{change.old_path}`")
        paths.append(f"`{change.path}`")
    fingerprint = hashlib.sha256()
    fingerprint.update((_git(root, ["rev-parse", "HEAD"]).strip() if _has_head(root) else "unborn").encode())
    for change in selected:
        fingerprint.update(f"{change.status}:{change.old_path}:{change.path}".encode())
        path = root / change.path
        fingerprint.update(path.read_bytes() if path.exists() else b"deleted")
    change_id = fingerprint.hexdigest()[:20]
    entry = (
        f"## [{date.today().isoformat()}] {inferred} | {clean_summary[:300]} | "
        f"documents={', '.join(dict.fromkeys(paths))} | change={change_id}"
    )
    from tools.document_maintenance import _safe
    log_path = _safe(root.resolve(), str(policy.global_log))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    current = log_path.read_text() if log_path.exists() else "# Log\n"
    existing = next((line for line in current.splitlines() if f"change={change_id}" in line), None)
    if existing:
        return existing
    if entry not in current:
        log_path.write_text(current.rstrip() + "\n\n" + entry + "\n")
    return entry


def _infer_operation(changes: list[DocumentChange]) -> str:
    statuses = {change.status for change in changes}
    if statuses == {"A"}:
        return "document-register"
    if statuses == {"D"}:
        return "document-retire"
    if "R" in statuses:
        return "document-rename"
    return "document-update"


def _governed_change(policy: DocumentPolicy, change: DocumentChange) -> bool:
    return policy.is_canonical(change.path) or (
        change.old_path is not None and policy.is_canonical(change.old_path)
    )


def _required_identifiers(
    root: Path, change: DocumentChange, policy: DocumentPolicy, *, staged: bool, base: str | None,
) -> set[str]:
    identifiers = {f"`{change.path}`"}
    if change.old_path is not None:
        identifiers.add(f"`{change.old_path}`")
    for path in (change.path, change.old_path):
        if path is None or not _is_within(path, policy.global_log.parent):
            continue
        if staged and path == change.path and change.status != "D":
            content = _git(root, ["show", f":{path}"])
        elif path == change.old_path or change.status == "D":
            revision = base or "HEAD"
            content = _git(root, ["show", f"{revision}:{path}"])
        else:
            content = (root / path).read_text() if (root / path).exists() else ""
        slug = _slug_from_text(content, path.stem)
        identifiers.add(f"[[{slug}]]")
    return identifiers


def _page_slug(path: Path) -> str:
    try:
        text = path.read_text()
    except (OSError, UnicodeError):
        return path.stem
    return _slug_from_text(text, path.stem)


def _slug_from_text(text: str, default: str) -> str:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return default
    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return default
    return str(frontmatter.get("slug") or default) if isinstance(frontmatter, dict) else default


def _added_log_entries(
    root: Path,
    log_path: PurePosixPath,
    *,
    staged: bool,
    base: str | None,
) -> list[str]:
    absolute = root / log_path
    if not staged and not absolute.exists():
        return []
    args = ["diff"]
    if staged:
        args.append("--cached")
    elif base:
        args.append(base)
    elif not _has_head(root):
        args.append("--cached")
    else:
        args.append("HEAD")
    args.extend(["--unified=0", "--", str(log_path)])
    diff = _git(root, args)
    entries = [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++") and line[1:].startswith("## [")
    ]
    if not entries and _is_untracked(root, log_path) and not staged and base is None:
        entries = [line for line in absolute.read_text().splitlines() if line.startswith("## [")]
    return entries


def _entry_identifiers(entry: str) -> set[str]:
    if "documents=" in entry:
        entry = entry.split("documents=", 1)[1].split(" | ", 1)[0]
    paths = {f"`{value}`" for value in re.findall(r"`([^`]+\.md)`", entry)}
    links = {f"[[{value}]]" for value in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", entry)}
    return paths | links


def _operation(entry: str) -> str:
    match = re.match(r"^## \[[^\]]+\]\s+([^|]+)", entry)
    return match.group(1).strip().lower() if match else ""


def _parse_name_status(output: str) -> list[DocumentChange]:
    changes: list[DocumentChange] = []
    fields = iter(filter(None, output.split("\0")))
    for code in fields:
        status = code[0]
        first = next(fields)
        if status in {"R", "C"}:
            target = next(fields)
            changes.append(DocumentChange("R" if status == "R" else "A", _posix(target),
                                          _posix(first) if status == "R" else None))
        elif status in {"A", "M", "D", "T"}:
            changes.append(DocumentChange("M" if status == "T" else status, _posix(first)))
    return changes


def _is_untracked(root: Path, path: PurePosixPath) -> bool:
    output = _git(root, ["ls-files", "--others", "--exclude-standard", "--", str(path)])
    return bool(output.strip())


def _has_head(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _posix(value: str | Path) -> PurePosixPath:
    normalized = str(value).replace(os.sep, "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"expected a non-empty repository-relative path: {value}")
    return path


def _relative(root: Path, value: Path) -> PurePosixPath:
    path = value if value.is_absolute() else root / value
    return _posix(path.resolve().relative_to(root.resolve()))


def _is_within(path: PurePosixPath, root: PurePosixPath) -> bool:
    return path == root or root in path.parents


@click.group()
def cli() -> None:
    """Maintain a finite, auditable set of canonical project documents."""


@cli.command("check")
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=".")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=".alpha-wiki/config.yaml")
@click.option("--staged", is_flag=True, help="Check only staged changes.")
@click.option("--base", help="Check changes relative to a Git revision.")
def check_cli(root: Path, config_path: Path, staged: bool, base: str | None) -> None:
    """Verify document changes and the global log are synchronized."""
    try:
        if staged and base:
            raise ValueError("choose --staged or --base, not both")
        config = config_path if config_path.is_absolute() else root / config_path
        findings = check_document_governance(root.resolve(), config.resolve(), staged=staged, base=base)
    except (RuntimeError, ValueError, OSError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc
    if findings:
        for finding in findings:
            click.echo(f"ERROR {finding}")
        raise click.exceptions.Exit(1)
    click.echo("PASS document governance")


@cli.command("record")
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=".")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=".alpha-wiki/config.yaml")
@click.option("--document", "documents", type=click.Path(path_type=Path), multiple=True, required=True)
@click.option("--summary", required=True)
@click.option(
    "--operation",
    type=click.Choice(["document-update", "document-register", "document-retire", "document-rename"]),
)
@click.option("--allow-new", is_flag=True, help="Acknowledge deliberate expansion of the canonical set.")
def record_cli(
    root: Path,
    config_path: Path,
    documents: tuple[Path, ...],
    summary: str,
    operation: str | None,
    allow_new: bool,
) -> None:
    """Append one global change record for already-edited canonical documents."""
    try:
        config_path = config_path if config_path.is_absolute() else root / config_path
        entry = record_change(
            root.resolve(),
            config_path.resolve(),
            documents,
            summary,
            operation=operation,
            allow_new=allow_new,
        )
    except (RuntimeError, ValueError, OSError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(entry)


@cli.command("plan")
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=".")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=".alpha-wiki/config.yaml")
@click.option("--document", "documents", type=click.Path(path_type=Path), multiple=True)
@click.option("--compact", is_flag=True, help="Explicitly scope source-preserving prose compaction.")
@click.option("--limit", type=click.IntRange(min=1), default=10, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), help="Optional generated plan under .alpha-wiki/maintenance/.")
def plan_cli(root: Path, config_path: Path, documents: tuple[Path, ...], compact: bool,
             limit: int, output: Path | None) -> None:
    """Plan changed-source updates to existing documents; never call a model."""
    import json
    from tools.document_maintenance import STATE_DIR, _safe, _write_json, plan_maintenance

    try:
        root = root.resolve()
        plan = plan_maintenance(root, _safe(root, config_path), documents, compact=compact, limit=limit)
        if output:
            target = _safe(root, output)
            if target.parent != root / STATE_DIR or target.name in {"state.json", "pending.json", "worker.lock", ".gitignore"}:
                raise ValueError("write plans directly under .alpha-wiki/maintenance/, not over source/checkpoint files")
            target.parent.mkdir(parents=True, exist_ok=True)
            (target.parent / ".gitignore").write_text("*\n!.gitignore\n")
            _write_json(target, plan)
        click.echo(json.dumps(plan, indent=2, ensure_ascii=False))
    except (RuntimeError, ValueError, OSError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command("apply")
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=".")
@click.option("--plan", "plan_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--edits", "edits_path", type=click.Path(path_type=Path, exists=True), required=True)
def apply_cli(root: Path, plan_path: Path, edits_path: Path) -> None:
    """Apply reviewed JSON edits, journal once, refresh graph, and checkpoint."""
    import json
    from tools.document_maintenance import apply_maintenance

    try:
        result = apply_maintenance(root.resolve(), json.loads(plan_path.read_text()), json.loads(edits_path.read_text()))
    except (RuntimeError, ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    cli()
