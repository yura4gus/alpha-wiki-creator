"""Existing-project audit for Alpha-Wiki init.

Beyond discovering candidate source files, this module curates them: it excludes
vendored/generated noise, classifies each file into an operational category,
detects duplicate/source-of-truth conflicts, and proposes a small, durable
Batch 1 instead of dumping every candidate. Real-world usage (the Zamio /
ZamWallet workspace) surfaced 253 candidates dominated by `repos/*/vendor/**`
noise; the curation below keeps first-class sources focused.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click

from tools.classify import classify


DOC_SUFFIXES = {".md", ".mdx", ".txt", ".json", ".yaml", ".yml", ".toml", ".graphql", ".gql", ".proto", ".sql", ".tf"}

# Directory names that are never first-class project memory: VCS internals,
# language/tool caches, dependency trees, build output, and Alpha-Wiki's own
# generated layers. Matched against any path part.
EXCLUDED_PARTS = {
    # VCS / editor / Alpha-Wiki internals
    ".git", ".hg", ".svn", ".idea", ".vscode",
    ".alpha-wiki", ".obsidian", ".wiki", "wiki", "raw",
    # Python / tooling caches
    ".venv", "venv", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", ".tox",
    "htmlcov", "coverage", ".coverage", ".cache", ".pytest",
    # Dependency trees
    "node_modules", "vendor", "bower_components", ".yarn", ".pnp",
    "third_party", "third-party", "Pods", ".gradle", ".terraform",
    # Build / generated output
    "dist", "build", "out", ".output", ".next", ".nuxt", ".svelte-kit",
    "target", "bin", "obj", ".turbo", ".parcel-cache", "generated", "__generated__",
    # Transient
    "tmp", "temp", "logs", "log",
}

# Filenames that indicate third-party/licensing artifacts rather than project canon.
THIRD_PARTY_NAMES = {
    "license", "license.md", "license.txt", "licence", "licence.md",
    "notice", "notice.md", "copying", "authors", "contributors", "patents",
}

# Lockfiles / machine-generated manifests.
GENERATED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "cargo.lock", "go.sum", "composer.lock", "gemfile.lock", "flake.lock",
}

# Categories used to separate durable sources from noise.
CAT_CANONICAL = "canonical"
CAT_ADR = "adr"
CAT_ARCHITECTURE = "architecture"
CAT_API = "api-contract"
CAT_SECURITY = "security"
CAT_RELEASE = "release"
CAT_PRODUCT = "product"
CAT_IMPL = "impl-notes"
CAT_THIRD_PARTY = "third-party"
CAT_GENERATED = "generated"
CAT_DUPLICATE = "duplicate"
CAT_UNKNOWN = "unknown"

# Categories that belong in a focused, durable Batch 1.
BATCH1_CATEGORIES = {
    CAT_CANONICAL, CAT_ARCHITECTURE, CAT_ADR, CAT_API, CAT_SECURITY, CAT_RELEASE, CAT_PRODUCT,
}
# Categories that must never be proposed as first-class Batch 1 sources.
NOISE_CATEGORIES = {CAT_THIRD_PARTY, CAT_GENERATED, CAT_DUPLICATE}


@dataclass(frozen=True)
class SourceCandidate:
    path: Path
    kind: str
    raw_target: str
    wiki_slot: str
    batch: str
    reason: str
    category: str = CAT_UNKNOWN
    canonical: bool = True
    duplicate_of: str | None = None


@dataclass(frozen=True)
class InitScope:
    """Operational scope recorded during init so agents avoid deferred work."""
    active: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    canonical_notes: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)


def discover_sources(root: Path) -> list[SourceCandidate]:
    root = root.resolve()
    raw: list[SourceCandidate] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _excluded(path, root):
            continue
        if path.suffix.lower() not in DOC_SUFFIXES and path.name not in {"README", "CHANGELOG"}:
            continue
        rel = path.relative_to(root)
        artifact = classify(path)
        wiki_slot, batch, reason = _route(rel, artifact.kind, artifact.suggested_slot)
        category = _categorize(rel, artifact.kind, wiki_slot)
        raw.append(SourceCandidate(
            path=rel,
            kind=artifact.kind,
            raw_target=_raw_target(rel),
            wiki_slot=wiki_slot,
            batch=batch,
            reason=reason,
            category=category,
        ))
    return _mark_duplicates(raw)


def batch1_plan(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """Small, durable Batch 1: prefer canon/arch/ADR/API/security/release, drop noise."""
    plan = [
        item for item in candidates
        if item.category in BATCH1_CATEGORIES
        and item.category not in NOISE_CATEGORIES
        and item.canonical
    ]
    return sorted(plan, key=lambda item: (_batch1_priority(item.category), str(item.path)))


def excluded_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """Candidates that are noise or need human review before ingest."""
    return [item for item in candidates if item.category in NOISE_CATEGORIES or not item.canonical]


def init_audit_report(
    root: Path,
    wiki_dir: str = "wiki",
    scope: InitScope | None = None,
) -> str:
    candidates = discover_sources(root)
    batches = _group(candidates, key=lambda item: item.batch)
    slots = _group(candidates, key=lambda item: item.wiki_slot)
    categories = _group(candidates, key=lambda item: item.category)
    batch1 = batch1_plan(candidates)
    excluded = excluded_candidates(candidates)

    lines = [
        "# Alpha-Wiki Init Audit",
        "",
        f"- Project root: `{root.resolve()}`",
        f"- Recommended wiki dir: `{wiki_dir}`",
        f"- Candidate source files: {len(candidates)}",
        f"- Recommended Batch 1 sources: {len(batch1)}",
        f"- Excluded / needs-review: {len(excluded)}",
        "",
    ]
    lines.extend(_scope_block(scope))
    lines.extend([
        "## Project Signals",
        "",
        *[f"- {signal}" for signal in _project_signals(root)],
        "",
        "## Source Classification",
        "",
    ])
    for category, items in sorted(categories.items(), key=lambda kv: (_batch1_priority(kv[0]), kv[0])):
        lines.append(f"- `{category}`: {len(items)} source(s)")
    lines.extend([
        "",
        "## Recommended Batch 1 (durable project memory)",
        "",
    ])
    if batch1:
        for item in batch1:
            lines.append(f"- `{item.path}` -> `{wiki_dir}/{item.wiki_slot}/` ({item.category}; {item.reason})")
    else:
        lines.append("_(no high-signal sources detected; review the excluded list below)_")
    lines.extend([
        "",
        "## Excluded / Needs Human Review",
        "",
    ])
    if excluded:
        for item in excluded:
            note = item.duplicate_of and f"duplicate of `{item.duplicate_of}`" or item.category
            lines.append(f"- `{item.path}` ({note})")
    else:
        lines.append("_(nothing excluded)_")
    lines.extend([
        "",
        "## Excluded Folders (never ingested)",
        "",
        "- " + ", ".join(f"`{part}`" for part in sorted(EXCLUDED_PARTS)),
        "",
        "## Proposed Wiki Structure",
        "",
    ])
    for slot, items in sorted(slots.items()):
        lines.append(f"- `{wiki_dir}/{slot}/`: {len(items)} source(s)")
    lines.extend([
        "",
        "## Proposed Raw Placement",
        "",
    ])
    for item in candidates:
        lines.append(f"- `{item.path}` -> `{item.raw_target}` ({item.kind}; {item.reason})")
    lines.extend([
        "",
        "## Processing Plan",
        "",
    ])
    for batch, items in sorted(batches.items(), key=_batch_sort_key):
        lines.append(f"### {batch}")
        for item in items:
            lines.append(f"- Ingest `{item.raw_target}` -> `{wiki_dir}/{item.wiki_slot}/`")
        lines.append("")
    lines.extend([
        "## Init Decision Points",
        "",
        "- Confirm the active product scope and the out-of-scope / deferred modules (recorded in the source manifest).",
        "- Confirm which location is canonical when duplicate docs exist.",
        "- Confirm whether to copy source snapshots into `raw/` or keep a manifest that references current repo paths.",
        "- Confirm whether to process all batches now or start with Batch 1 only.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def write_source_manifest(
    root: Path,
    out: Path | None = None,
    scope: InitScope | None = None,
) -> Path:
    root = root.resolve()
    target = out or root / "raw" / "docs" / "source-manifest.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    candidates = discover_sources(root)
    batch1 = batch1_plan(candidates)
    excluded = excluded_candidates(candidates)
    duplicates = [item for item in candidates if not item.canonical]
    deferred_batches = _group(
        [item for item in candidates if item not in batch1 and item.category not in NOISE_CATEGORIES and item.canonical],
        key=lambda item: item.batch,
    )

    lines = [
        "# Source Manifest",
        "",
        "Generated by `tools/init_audit.py`. First-class raw evidence + curation record",
        "for Alpha-Wiki ingest. After init, agents should read this instead of",
        "reconstructing corpus logic from chat history.",
        "",
    ]
    lines.extend(_scope_block(scope))
    lines.extend([
        "## Canonical Sources (Batch 1)",
        "",
    ])
    if batch1:
        for item in batch1:
            lines.append(f"- `{item.path}` -> `{item.raw_target}` | category=`{item.category}` | wiki_slot=`{item.wiki_slot}`")
    else:
        lines.append("_(none detected — review excluded sources)_")
    lines.extend(["", "## Deferred Sources (later batches)", ""])
    if deferred_batches:
        for batch, items in sorted(deferred_batches.items(), key=_batch_sort_key):
            lines.append(f"### {batch}")
            for item in items:
                lines.append(f"- `{item.path}` | category=`{item.category}` | wiki_slot=`{item.wiki_slot}`")
            lines.append("")
    else:
        lines.append("_(none)_")
        lines.append("")
    lines.extend(["## Duplicates / Source Mirrors", ""])
    if duplicates:
        for item in duplicates:
            lines.append(f"- `{item.path}` — duplicate of `{item.duplicate_of}` (ignored as source of truth)")
    else:
        lines.append("_(no duplicate docs detected)_")
    lines.extend(["", "## Excluded / Noise", ""])
    noise = [item for item in excluded if item.category in NOISE_CATEGORIES and item.canonical]
    if noise:
        for item in noise:
            lines.append(f"- `{item.path}` (category=`{item.category}`)")
    else:
        lines.append("_(none)_")
    lines.extend([
        "",
        "## Excluded Folders",
        "",
        "- " + ", ".join(f"`{part}`" for part in sorted(EXCLUDED_PARTS)),
        "",
        "## Excluded File Categories",
        "",
        f"- third-party/licensing files (e.g. {', '.join(sorted(THIRD_PARTY_NAMES)[:4])}, …)",
        "- generated lockfiles and machine manifests",
        "- duplicate source mirrors (kept only the canonical copy)",
        "",
        "## All Candidates",
        "",
    ])
    for item in candidates:
        flag = "" if item.canonical else " | duplicate"
        lines.append(
            f"- `{item.path}` -> `{item.raw_target}` | kind=`{item.kind}` | "
            f"category=`{item.category}` | wiki_slot=`{item.wiki_slot}` | batch=`{item.batch}`{flag}"
        )
    target.write_text("\n".join(lines) + "\n")
    return target


def _scope_block(scope: InitScope | None) -> list[str]:
    scope = scope or InitScope()
    lines = ["## Scope", ""]
    lines.append("- Active scope: " + (", ".join(scope.active) if scope.active else "_(not set — record before ingest)_"))
    lines.append("- Out of scope: " + (", ".join(scope.out_of_scope) if scope.out_of_scope else "_(none recorded)_"))
    lines.append("- Deferred: " + (", ".join(scope.deferred) if scope.deferred else "_(none recorded)_"))
    if scope.canonical_notes:
        lines.append("")
        lines.append("### Source-of-Truth Notes")
        lines.append("")
        lines.extend(f"- {note}" for note in scope.canonical_notes)
    if scope.decisions:
        lines.append("")
        lines.append("### Human Decisions During Init")
        lines.append("")
        lines.extend(f"- {decision}" for decision in scope.decisions)
    lines.append("")
    return lines


def _excluded(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_PARTS for part in rel_parts):
        return True
    return "render" in rel_parts and any(part in {".wiki", "wiki"} for part in rel_parts)


def _raw_target(rel: Path) -> str:
    safe_parts = [part.replace(" ", "-") for part in rel.parts]
    return str(Path("raw") / "docs" / Path(*safe_parts))


def _categorize(rel: Path, kind: str, wiki_slot: str) -> str:
    name = rel.name.lower()
    lower = str(rel).lower()
    parts = rel.parts

    if name in GENERATED_NAMES or name.endswith(".lock"):
        return CAT_GENERATED
    if name in THIRD_PARTY_NAMES or name.startswith("license") or name.startswith("licence"):
        return CAT_THIRD_PARTY
    if kind == "adr" or name.startswith("adr-"):
        return CAT_ADR
    if wiki_slot.startswith("contracts") or kind in {"openapi", "asyncapi", "graphql-schema", "protobuf", "sql-ddl", "postman-collection"}:
        return CAT_API
    if _has_token(lower, {"security", "auth", "authz", "rbac", "permission", "secret", "threat", "kyc", "pii", "custody", "signature"}):
        return CAT_SECURITY
    if _has_token(lower, {"architecture", "hexagonal", "clean-arch", "ddd", "c4", "design-doc"}) or name.startswith("design"):
        return CAT_ARCHITECTURE
    if _has_token(lower, {"release", "changelog", "deploy", "rollback"}):
        return CAT_RELEASE
    if _has_token(lower, {"product", "scope", "roadmap", "prd", "vision"}) or kind == "prd":
        return CAT_PRODUCT
    if kind in {"runbook", "transcript", "postmortem"} or _has_token(lower, {"notes", "wip", "scratch", "draft", "impl"}):
        return CAT_IMPL
    if len(parts) == 1 and rel.name in {"README.md", "CLAUDE.md"}:
        return CAT_CANONICAL
    if parts[0] == "docs" and len(parts) == 2:
        return CAT_CANONICAL
    if kind in {"markdown", "unknown"}:
        return CAT_UNKNOWN
    return CAT_UNKNOWN


def _mark_duplicates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """When the same basename appears in multiple places, keep one canonical copy.

    Canonical preference: a file physically inside a repo's own `docs/` (e.g.
    `repos/wallet-trade-v2/docs/x.md`) beats a workspace-level mirror; otherwise
    the shallowest path wins. Deterministic — ties break on path string.
    """
    by_name: dict[str, list[SourceCandidate]] = {}
    for item in candidates:
        by_name.setdefault(item.path.name.lower(), []).append(item)

    resolved: list[SourceCandidate] = []
    for _name, group in by_name.items():
        if len(group) == 1:
            resolved.append(group[0])
            continue
        winner = min(group, key=_canonical_rank)
        for item in group:
            if item is winner:
                resolved.append(item)
            else:
                resolved.append(SourceCandidate(
                    path=item.path,
                    kind=item.kind,
                    raw_target=item.raw_target,
                    wiki_slot=item.wiki_slot,
                    batch=item.batch,
                    reason=item.reason,
                    category=CAT_DUPLICATE,
                    canonical=False,
                    duplicate_of=str(winner.path),
                ))
    # Preserve original sorted order by path.
    return sorted(resolved, key=lambda item: str(item.path))


def _canonical_rank(item: SourceCandidate) -> tuple[int, int, str]:
    parts = item.path.parts
    inside_repo_docs = 0 if ("docs" in parts and "repos" in parts) else 1
    return (inside_repo_docs, len(parts), str(item.path))


def _has_token(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def _route(rel: Path, kind: str, suggested_slot: str | None) -> tuple[str, str, str]:
    parts = rel.parts
    name = rel.name.lower()
    if parts[0] == ".claude-plugin":
        return "contracts/rpc", "Batch 1 - contracts and decisions", "plugin metadata contract"
    if len(parts) >= 2 and parts[0] == "docs" and name.startswith("adr-"):
        return "decisions", "Batch 1 - contracts and decisions", "ADR source"
    if parts[0] == "commands":
        return "specs", "Batch 2 - command and skill manuals", "command manual"
    if parts[0] == "skills":
        return "specs", "Batch 2 - command and skill manuals", "skill manual"
    if parts[0] == "references":
        return "specs", "Batch 3 - references and examples", "reference material"
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "superpowers":
        return "specs", "Batch 4 - archive distillation", "archive/design history"
    if parts[0] == "docs":
        return "specs", "Batch 1 - architecture and release docs", "project documentation"
    if len(parts) == 1 and rel.name in {"README.md", "CHANGELOG.md", "CLAUDE.md", "pyproject.toml"}:
        return "specs", "Batch 1 - architecture and release docs", "root project contract"
    if suggested_slot:
        return suggested_slot, "Batch 1 - contracts and decisions", "classifier suggested a concrete slot"
    return "specs", "Batch 5 - remaining documents", f"{kind} source"


def _project_signals(root: Path) -> list[str]:
    signals: list[str] = []
    for marker in ["pyproject.toml", "README.md", "CHANGELOG.md", "skills", "commands", "docs", ".claude-plugin"]:
        if (root / marker).exists():
            signals.append(f"`{marker}` present")
    return signals or ["No common project signals detected"]


def _group(items: list[SourceCandidate], key) -> dict[str, list[SourceCandidate]]:
    grouped: dict[str, list[SourceCandidate]] = {}
    for item in items:
        grouped.setdefault(key(item), []).append(item)
    return grouped


def _batch_sort_key(item: tuple[str, list[SourceCandidate]]) -> tuple[int, str]:
    label = item[0]
    for idx in range(1, 9):
        if label.startswith(f"Batch {idx}"):
            return idx, label
    return 99, label


def _batch1_priority(category: str) -> int:
    order = [
        CAT_CANONICAL, CAT_PRODUCT, CAT_ARCHITECTURE, CAT_ADR, CAT_API,
        CAT_SECURITY, CAT_RELEASE, CAT_IMPL, CAT_UNKNOWN,
        CAT_THIRD_PARTY, CAT_GENERATED, CAT_DUPLICATE,
    ]
    return order.index(category) if category in order else 99


@click.command()
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=Path("."), show_default=True)
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--active-scope", multiple=True, help="Active product scope module (repeatable).")
@click.option("--out-of-scope", multiple=True, help="Out-of-scope module (repeatable).")
@click.option("--deferred", multiple=True, help="Deferred module (repeatable).")
@click.option("--write-manifest", is_flag=True, help="Write raw/docs/source-manifest.md in addition to printing the audit.")
@click.option("--manifest-out", type=click.Path(path_type=Path), help="Override manifest output path.")
def cli(
    root: Path,
    wiki_dir: str,
    active_scope: tuple[str, ...],
    out_of_scope: tuple[str, ...],
    deferred: tuple[str, ...],
    write_manifest: bool,
    manifest_out: Path | None,
) -> None:
    scope = InitScope(active=list(active_scope), out_of_scope=list(out_of_scope), deferred=list(deferred))
    click.echo(init_audit_report(root, wiki_dir=wiki_dir, scope=scope))
    if write_manifest:
        target = write_source_manifest(root, out=manifest_out, scope=scope)
        click.echo(f"\nwrote {target}")


if __name__ == "__main__":
    cli()
