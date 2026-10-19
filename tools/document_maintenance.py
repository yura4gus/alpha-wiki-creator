"""Bounded, source-pinned maintenance of existing canonical documents.

The agent supplies reviewed replacement text. This module only plans deltas,
validates structure, applies edits, and checkpoints successful synchronization.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import yaml

from tools.document_worker import (
    ADD_OPERATIONS, DocumentChange, DocumentPolicy, _added_log_entries,
    _entry_identifiers, _git, _has_head, _operation, _posix, _required_identifiers, load_policy,
)


STATE_DIR = Path(".alpha-wiki/maintenance")
PROTECTED_SECTIONS = {
    "requirements", "constraints", "invariants", "contracts", "acceptance",
    "acceptance criteria", "decisions", "risks", "open questions", "provenance",
    "требования", "ограничения", "инварианты", "контракты", "решения",
    "критерии приемки", "критерии приёмки", "риски", "открытые вопросы", "источники",
}


class LegacySourceBindingError(ValueError):
    """A moved/external absolute binding is a gap, not a hierarchy failure."""


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe(root: Path, value: str | Path) -> Path:
    root = root.resolve()
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.relative_to(root)
        except ValueError:
            # Resolve root aliases such as macOS /var, retaining the final name
            # so a symlink file itself is still rejected below.
            path = path.parent.resolve().relative_to(root) / path.name
    relative = _posix(path)
    target = root / relative
    target.resolve().relative_to(root)
    if any(candidate.is_symlink() for candidate in (target, *target.parents) if candidate != root.parent):
        raise ValueError(f"symlink paths are not supported for maintenance: {relative}")
    return target


def _document(root: Path, policy: DocumentPolicy, value: str | Path) -> Path:
    path = _safe(root, value)
    relative = path.relative_to(root)
    if any(character in relative.as_posix() for character in ("\n", "\r", "`")):
        raise ValueError("canonical paths must be representable in a one-line Markdown journal")
    wiki = Path(policy.global_log.parent)
    protected = {"raw", ".git", ".alpha-wiki"}
    if (not policy.is_canonical(_posix(relative)) or relative.parts[0] in protected
            or any(relative.is_relative_to(wiki / name) for name in ("graph", "render", "outputs"))):
        raise ValueError(f"not a writable canonical document: {relative}")
    return path


def _frontmatter(text: str) -> dict:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        raise ValueError("unterminated YAML frontmatter")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def inventory(root: Path, config_path: Path, *, staged: bool = False) -> list[dict]:
    root = root.resolve()
    config_path = _safe(root, config_path)
    content = _git(root, ["show", f":{config_path.relative_to(root)}"]) if staged else None
    policy = load_policy(config_path, content=content)
    candidates = {root / path for path in policy.canonical_files}
    for directory in policy.canonical_roots:
        candidates.update(_safe(root, str(directory)).rglob("*.md"))
    if staged:
        candidates = {root / value for value in _git(root, ["ls-files", "-z"]).split("\0") if value}
    rows = []
    for path in sorted(candidates):
        relative = path.relative_to(root).as_posix()
        if (not staged and not path.exists()) or not policy.is_canonical(_posix(relative)):
            continue
        path = _document(root, policy, relative)
        metadata = _frontmatter(_git(root, ["show", f":{relative}"]) if staged else path.read_text())
        if metadata.get("slug") is not None and not isinstance(metadata["slug"], str):
            raise ValueError(f"{relative}: slug must be a string")
        source_gaps = []
        try:
            sources = _sources(root, policy, metadata)
        except LegacySourceBindingError as exc:
            sources = []
            source_gaps.append(f"{relative}: {exc}")
        rows.append({"document": relative, "slug": metadata.get("slug"),
                     "parent": metadata.get("belongs_to"),
                     "sources": sources, "source_gaps": source_gaps})
    return rows


def _sources(root: Path, policy: DocumentPolicy, metadata: dict) -> list[str]:
    values = metadata.get("source_files", [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("source_files must be a list of repository paths")
    if metadata.get("source_file"):
        values = [*values, metadata["source_file"]]
    if not all(isinstance(value, str) for value in values):
        raise ValueError("source_file/source_files must identify repository paths")
    paths = []
    for value in values:
        try:
            path = _safe(root, value)
        except ValueError as exc:
            if Path(value).is_absolute():
                raise LegacySourceBindingError(
                    f"external or relocated source binding needs explicit reconciliation: {value}"
                ) from exc
            raise
        relative = path.relative_to(root)
        wiki = Path(policy.global_log.parent)
        if (relative.parts[0] in {".git", ".alpha-wiki"}
                or any(relative.is_relative_to(wiki / part) for part in ("graph", "render", "outputs"))):
            raise ValueError(f"generated/runtime material is not a maintenance source: {relative}")
        paths.append(relative.as_posix())
    return sorted(set(paths))


def hierarchy_findings(root: Path, config_path: Path, *, staged: bool = False) -> list[str]:
    from tools.wiki_engine import _coerce_targets
    rows = inventory(root, config_path, staged=staged)
    by_slug: dict[str, str] = {}
    findings = []
    for row in rows:
        slug = row["slug"]
        if slug:
            if slug in by_slug:
                findings.append(f"{row['document']}: duplicate canonical slug {slug}")
            by_slug[slug] = row["document"]
    parents = {}
    for row in rows:
        value = row["parent"]
        if value is None:
            continue  # Root documents do not need an invented parent.
        values = _coerce_targets(value)
        if len(values) != 1:
            findings.append(f"{row['document']}: belongs_to must identify one ownership parent")
            continue
        target = values[0]
        parent = by_slug.get(target, target if target in {item['document'] for item in rows} else None)
        if not parent:
            findings.append(f"{row['document']}: missing ownership parent {target}")
        else:
            parents[row["document"]] = parent
    reported = set()
    for start in parents:
        seen = []
        node = start
        while node in parents:
            if node in seen:
                cycle = frozenset(seen[seen.index(node):])
                if cycle not in reported:
                    findings.append(f"{start}: ownership hierarchy contains a cycle")
                    reported.add(cycle)
                break
            seen.append(node)
            node = parents[node]
    return sorted(findings)


def _state(root: Path) -> dict:
    path = _safe(root, STATE_DIR / "state.json")
    data = json.loads(path.read_text()) if path.exists() else {"version": 1, "completed": {}}
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("completed"), dict):
        raise ValueError("unsupported maintenance checkpoint; preserve it before recovery")
    return data


def _registered(root: Path, policy: DocumentPolicy, name: str) -> bool:
    if name in _git(root, ["ls-files", "-z", "--", name]).split("\0"):
        return True
    identifiers = _required_identifiers(root, DocumentChange("A", _posix(name)), policy,
                                        staged=False, base=None)
    return any(_operation(entry) in ADD_OPERATIONS and
               (bool(identifiers & _entry_identifiers(entry)) or
                (_operation(entry) == "bootstrap" and not _has_head(root)))
               for entry in _added_log_entries(root, policy.global_log, staged=False, base=None))


def plan_maintenance(root: Path, config_path: Path, documents: tuple[Path, ...] = (), *,
                     compact: bool = False, limit: int = 10) -> dict:
    root = root.resolve()
    config_path = _safe(root, config_path)
    policy = load_policy(config_path)
    if not policy.enabled:
        raise ValueError("document governance is disabled")
    if compact and not documents:
        raise ValueError("compaction requires explicit --document scope")
    if limit < 1:
        raise ValueError("limit must be positive")
    if _safe(root, STATE_DIR / "pending.json").exists():
        raise ValueError("unfinished maintenance transaction: resume apply with its original plan and edits")
    rows = inventory(root, config_path)
    selected = {_document(root, policy, value).relative_to(root).as_posix() for value in documents}
    if selected - {row["document"] for row in rows}:
        raise ValueError("selected document does not exist")
    state = _state(root)
    config_hash = _sha(config_path)
    jobs, gaps = [], []
    for row in rows:
        name = row["document"]
        if selected and name not in selected:
            continue
        if row["source_gaps"]:
            gaps.extend(row["source_gaps"])
            continue
        if not row["sources"] and not compact:
            if selected:
                gaps.append(f"{name}: no source_file/source_files mapping; use explicit compaction or bind real sources")
            continue
        if not _registered(root, policy, name):
            gaps.append(f"{name}: register the existing document explicitly before maintenance")
            continue
        missing = [source for source in row["sources"] if not _safe(root, source).is_file()]
        if missing:
            gaps.append(f"{name}: missing source(s): {', '.join(missing)}")
            continue
        source_hashes = {source: _sha(_safe(root, source)) for source in row["sources"]}
        before = _sha(_safe(root, name))
        input_id = _digest({"document": name, "sources": source_hashes, "config": config_hash})
        receipt = state["completed"].get(name, {})
        if not compact and receipt == {"input_id": input_id, "output_sha256": before}:
            continue
        jobs.append({"document": name, "before_sha256": before, "sources": source_hashes,
                     "input_id": input_id, "mode": "compact" if compact else "refresh"})
    return {"version": 1, "root": str(root),
            "base_sha": _git(root, ["rev-parse", "HEAD"]).strip() if _has_head(root) else None,
            "config": config_path.relative_to(root).as_posix(), "config_sha256": config_hash,
            "jobs": jobs[:limit], "deferred": max(0, len(jobs) - limit),
            "source_bound_documents": sum(bool(row["sources"] or row["source_gaps"]) for row in rows),
            "unmapped_documents": sum(not row["sources"] and not row["source_gaps"] for row in rows),
            "gaps": sorted(gaps), "hierarchy_findings": hierarchy_findings(root, config_path)}


def _atomic_text(path: Path, text: str) -> None:
    if path.exists() and path.read_bytes() == text.encode():
        return
    descriptor, temporary = tempfile.mkstemp(prefix=".alpha-wiki-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_json(path: Path, data: dict) -> None:
    _atomic_text(path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


@contextmanager
def _lock(root: Path):
    directory = _safe(root, STATE_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    _atomic_text(directory / ".gitignore", "*\n!.gitignore\n")
    lock = directory / "worker.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("maintenance worker is locked; retry after it exits; remove a stale lock only after verifying its process stopped") from exc
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def _validate_replacement(old: str, new: str, mode: str) -> None:
    old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
    if not new.strip():
        raise ValueError("replacement must not be empty")
    before, after = _frontmatter(old), _frontmatter(new)
    for metadata in (before, after):
        metadata.pop("date_updated", None)
    if before != after:
        raise ValueError("maintenance must preserve identity, status, ownership, and source metadata; change contracts explicitly outside this operation")
    if mode != "compact":
        return
    if len(new.encode()) > len(old.encode()):
        raise ValueError("compaction must not grow the document")
    references = r"\[\[[^\]]+\]\]|\[[^\]]*\]\([^\)]+\)|https?://[^\s<>]+"
    if set(re.findall(references, old)) - set(re.findall(references, new)):
        raise ValueError("compaction must preserve existing source and cross-document references")
    # Protect normative sections verbatim; prose elsewhere can be consolidated.
    headings = list(re.finditer(r"(?m)^(#{1,6}) (.+)$", old))
    for index, heading in enumerate(headings):
        title = heading.group(2).strip().lower()
        end = next((following.start() for following in headings[index + 1:]
                    if len(following.group(1)) <= len(heading.group(1))), len(old))
        if title in PROTECTED_SECTIONS and old[heading.start():end].strip() not in new:
            raise ValueError(f"compaction must preserve the {title} section; use an explicit reviewed refresh for normative edits")


def _validate_preview(root: Path, config_path: Path, policy: DocumentPolicy, updates: list[dict]) -> None:
    from tools._models import LintSeverity
    from tools.lint import _load_config, run_all_checks

    wiki = _safe(root, str(policy.global_log.parent))
    if not wiki.is_dir():
        raise ValueError("wiki directory is missing")
    if any(path.is_symlink() for path in wiki.rglob("*")):
        raise ValueError("wiki preview does not follow symlinks; resolve them explicitly before maintenance")
    schema, types, rules = _load_config(config_path)
    def errors(directory):
        return {(str(Path(item.file).relative_to(directory)), item.check,
                 item.message.replace(str(directory), "<wiki>"))
                for item in run_all_checks(directory, schema, types, rules)
                if item.severity == LintSeverity.ERROR}
    baseline = errors(wiki)
    with tempfile.TemporaryDirectory(prefix="alpha-wiki-preview-") as temporary:
        preview = Path(temporary) / "wiki"
        shutil.copytree(wiki, preview, ignore=shutil.ignore_patterns("graph", "render", "outputs", ".obsidian"))
        for update in updates:
            target = root / update["document"]
            if target.is_relative_to(wiki):
                (preview / target.relative_to(wiki)).write_text(update["text"])
        introduced = errors(preview) - baseline
        if introduced:
            raise ValueError(f"replacement introduces structural errors: {sorted(introduced)}")


def apply_maintenance(root: Path, plan: dict, edits: dict) -> dict:
    root = root.resolve()
    if not isinstance(plan, dict) or plan.get("version") != 1 or plan.get("root") != str(root):
        raise ValueError("plan belongs to a different root or unsupported version")
    if not isinstance(edits, dict):
        raise ValueError("edits must be a JSON object")
    config_path = _safe(root, plan["config"])
    policy = load_policy(config_path)
    if not policy.enabled:
        raise ValueError("document governance is disabled")
    request_id = _digest({"plan": plan, "edits": edits})
    with _lock(root):
        pending = _safe(root, STATE_DIR / "pending.json")
        if pending.exists():
            transaction = json.loads(pending.read_text())
            if transaction["request_id"] != request_id:
                raise ValueError("unfinished transaction: resume with the original plan and edits")
        else:
            transaction = _prepare(root, config_path, policy, plan, edits, request_id)
            if not transaction["updates"] and transaction["state"] == _state(root):
                return {"status": "unchanged", "changed": [], "completed": []}
            _write_json(pending, transaction)
        result = _finish(root, config_path, policy, transaction)
        pending.unlink()
        return result


def _prepare(root: Path, config: Path, policy: DocumentPolicy, plan: dict, edits: dict, request_id: str) -> dict:
    if _sha(config) != plan["config_sha256"]:
        raise ValueError("stale plan: configuration changed; re-plan")
    jobs = {job["document"]: job for job in plan["jobs"]}
    state = _state(root)
    state_before = json.loads(json.dumps(state))
    updates, completed, inputs, documents_before = [], [], {}, {}
    supplied = edits.get("updates")
    if not isinstance(supplied, list):
        raise ValueError("edits must contain an updates list")
    names = [item["document"] for item in supplied]
    if len(set(names)) != len(names) or set(names) - jobs.keys():
        raise ValueError("edits contain duplicate or unplanned documents")
    for item in supplied:
        name, new = item["document"], item["text"]
        path = _document(root, policy, name)
        job = jobs[name]
        for source, expected in job["sources"].items():
            if _sha(_safe(root, source)) != expected:
                raise ValueError(f"stale source: {source}; re-plan")
            inputs[source] = expected
        old = path.read_text()
        new_hash = _sha(path) if old == new else hashlib.sha256(new.encode()).hexdigest()
        receipt = {"input_id": job["input_id"], "output_sha256": new_hash}
        if state["completed"].get(name) == receipt and _sha(path) == new_hash:
            continue
        if _sha(path) != job["before_sha256"]:
            raise ValueError(f"stale document: {name}; re-plan")
        _validate_replacement(old, new, job["mode"])
        documents_before[name] = job["before_sha256"]
        state["completed"][name] = receipt
        completed.append(name)
        if old != new:
            updates.append({"document": name, "before_sha256": job["before_sha256"], "text": new})
    if updates:
        if any(item["document"] in inputs for item in updates):
            raise ValueError("a changed document is also a source in this batch; apply its owner first, then re-plan dependent projections")
        _validate_preview(root, config, policy, updates)
    log = _safe(root, str(policy.global_log))
    before_log = log.read_text() if log.exists() else ""
    after_log = before_log
    if updates:
        summary = " ".join(str(edits.get("summary", "")).split())
        if not summary:
            raise ValueError("edits require a concise non-empty summary")
        paths = ", ".join(f"`{item['document']}`" for item in updates)
        sources = ", ".join(f"`{name}`" for name in sorted(inputs)) or "existing document"
        entry = (f"## [{date.today().isoformat()}] document-update | {summary[:300]} | documents={paths}"
                 f" | sources={sources} | change={request_id[:20]}")
        after_log = before_log.rstrip() + "\n\n" + entry + "\n"
    return {"request_id": request_id, "config_sha256": plan["config_sha256"], "inputs": inputs,
            "updates": updates, "completed": completed, "log_before": before_log, "log_after": after_log,
            "documents_before": documents_before,
            "state_before": state_before, "state": state}


def _finish(root: Path, config: Path, policy: DocumentPolicy, transaction: dict) -> dict:
    if _sha(config) != transaction["config_sha256"]:
        raise ValueError("configuration changed during maintenance; pending transaction preserved")
    for source, expected in transaction["inputs"].items():
        if _sha(_safe(root, source)) != expected:
            raise ValueError(f"source changed during maintenance: {source}; pending transaction preserved")
    for name, before in transaction["documents_before"].items():
        path = _document(root, policy, name)
        if _sha(path) not in {before, transaction["state"]["completed"][name]["output_sha256"]}:
            raise ValueError(f"concurrent document edit: {name}; pending transaction preserved")
    log = _safe(root, str(policy.global_log))
    if (log.read_text() if log.exists() else "") not in {transaction["log_before"], transaction["log_after"]}:
        raise ValueError("concurrent journal edit; pending transaction preserved")
    if _state(root) not in (transaction["state_before"], transaction["state"]):
        raise ValueError("checkpoint changed; pending transaction preserved")
    for item in transaction["updates"]:
        _atomic_text(_document(root, policy, item["document"]), item["text"])
    if transaction["updates"]:
        _atomic_text(log, transaction["log_after"])
        from tools.wiki_engine import rebuild_context_brief, rebuild_edges, rebuild_open_questions
        wiki = _safe(root, str(policy.global_log.parent))
        rebuild_edges(wiki)
        rebuild_context_brief(wiki)
        rebuild_open_questions(wiki)
    if _sha(config) != transaction["config_sha256"]:
        raise ValueError("configuration changed before checkpoint; pending transaction preserved")
    for source, expected in transaction["inputs"].items():
        if _sha(_safe(root, source)) != expected:
            raise ValueError(f"source changed before checkpoint: {source}; pending transaction preserved")
    for name in transaction["completed"]:
        if _sha(_document(root, policy, name)) != transaction["state"]["completed"][name]["output_sha256"]:
            raise ValueError(f"document changed before checkpoint: {name}; pending transaction preserved")
    if (log.read_text() if log.exists() else "") != transaction["log_after"]:
        raise ValueError("journal changed before checkpoint; pending transaction preserved")
    _write_json(_safe(root, STATE_DIR / "state.json"), transaction["state"])
    return {"status": "applied", "changed": [item["document"] for item in transaction["updates"]],
            "completed": transaction["completed"]}
