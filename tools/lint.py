"""Wiki structural lint. Pure Python, no LLM."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from tools._models import LintFinding, LintSeverity
from tools.wiki_engine import (
    REVERSE_OF,
    _coerce_targets,
    cluster_gaps,
    scan_wiki,
)


def check_broken_wikilinks(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    slugs = {p.slug for p in pages}
    findings: list[LintFinding] = []
    for p in pages:
        for link in p.forward_links:
            target_slug = link.split("/")[-1].split("|")[0]
            if target_slug not in slugs:
                findings.append(LintFinding(
                    check="broken-wikilink",
                    severity=LintSeverity.ERROR,
                    file=p.path,
                    line=0,
                    message=f"broken wikilink: [[{link}]] (no page with slug {target_slug})",
                    fix_available=False,
                ))
    return findings


def _slug_of(s) -> str:
    if isinstance(s, str):
        if s.startswith("[[") and s.endswith("]]"):
            return s[2:-2].split("|")[0]
        return s
    return ""


def check_missing_reverse_links(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {p.slug: p for p in pages}
    findings: list[LintFinding] = []
    for src in pages:
        relative = Path(src.path).relative_to(wiki_dir)
        if relative.parts and relative.parts[0] == "agentops":
            continue  # AgentOps dependencies are intentionally directed and validated separately.
        for key, value in src.frontmatter.items():
            reverse = REVERSE_OF.get(key)
            if reverse is None or reverse.startswith("_"):
                continue  # section-based reverses checked separately
            for target_slug in _coerce_targets(value):
                tgt = by_slug.get(target_slug)
                if tgt is None:
                    continue
                tgt_field = tgt.frontmatter.get(reverse, [])
                if isinstance(tgt_field, str):
                    tgt_field = [tgt_field]
                tgt_slugs = [_slug_of(s) for s in tgt_field]
                if src.slug not in tgt_slugs:
                    findings.append(LintFinding(
                        check="missing-reverse-link",
                        severity=LintSeverity.WARNING,
                        file=tgt.path,
                        line=0,
                        message=f"{tgt.slug}.{reverse} missing reverse for {src.slug}.{key}",
                        fix_available=True,
                        suggested_fix=f"add [[{src.slug}]] to {tgt.path} frontmatter `{reverse}`",
                    ))
    return findings


def check_orphans(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    incoming: dict[str, int] = {p.slug: 0 for p in pages}
    for p in pages:
        for link in p.forward_links:
            target = link.split("|")[0].split("/")[-1]
            if target in incoming:
                incoming[target] += 1
    # Namespaced extensions such as wiki/agentops keep their own generated index.
    # Treat all index files as navigation without scanning them as source pages.
    index_text = "\n".join(
        path.read_text()
        for path in sorted(wiki_dir.rglob("index.md"))
        if not any(part.startswith(".") or part in {"graph", "render", "outputs"} for part in path.relative_to(wiki_dir).parts[:-1])
    )
    findings: list[LintFinding] = []
    for p in pages:
        if incoming[p.slug] == 0 and f"[[{p.slug}]]" not in index_text:
            findings.append(LintFinding(
                check="orphan",
                severity=LintSeverity.WARNING,
                file=p.path,
                line=0,
                message=f"orphan: {p.slug} has no incoming links and is not in index.md",
                fix_available=False,
            ))
    return findings


def check_required_frontmatter(wiki_dir: Path, schema: dict[str, list[str]], dir_to_type: dict[str, str]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    pages = scan_wiki(wiki_dir)
    for p in pages:
        page_path = Path(p.path)
        relative = page_path.relative_to(wiki_dir)
        if relative.parts and relative.parts[0] == "agentops":
            continue  # checked against the namespaced AgentOps schema below
        type_name = None
        for part in page_path.parts:
            if part in dir_to_type:
                type_name = dir_to_type[part]
                break
        if type_name is None:
            continue
        required = schema.get(type_name, [])
        for field in required:
            if field not in p.frontmatter:
                findings.append(LintFinding(
                    check="missing-frontmatter-field",
                    severity=LintSeverity.ERROR,
                    file=p.path,
                    line=0,
                    message=f"{p.slug} missing required frontmatter `{field}` (type={type_name})",
                    fix_available=False,
                ))
    return findings


def check_duplicate_slugs(wiki_dir: Path) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    counts = Counter(p.slug for p in pages)
    findings: list[LintFinding] = []
    for slug, count in counts.items():
        if count > 1:
            offenders = [p.path for p in pages if p.slug == slug]
            findings.append(LintFinding(
                check="duplicate-slug",
                severity=LintSeverity.ERROR,
                file=offenders[0],
                line=0,
                message=f"duplicate slug `{slug}`: {offenders}",
                fix_available=False,
            ))
    return findings


import click
from tools.wiki_engine import add_edge


def check_dependency_rules(wiki_dir: Path, rules: list[dict]) -> list[LintFinding]:
    pages = scan_wiki(wiki_dir)
    by_slug = {p.slug: p for p in pages}
    findings: list[LintFinding] = []
    for src in pages:
        src_dir = str(Path(src.path).relative_to(wiki_dir).parent) + "/"
        for link in src.forward_links:
            target_slug = link.split("|")[0].split("/")[-1]
            tgt = by_slug.get(target_slug)
            if tgt is None:
                continue
            tgt_dir = str(Path(tgt.path).relative_to(wiki_dir).parent) + "/"
            for rule in rules:
                from_pattern = rule["from"]
                if not src_dir.startswith(from_pattern):
                    continue
                for forbidden in rule.get("forbidden_to", []):
                    if tgt_dir.startswith(forbidden):
                        findings.append(LintFinding(
                            check="dependency-rule-violation",
                            severity=LintSeverity.WARNING,
                            file=src.path,
                            line=0,
                            message=f"dependency rule: {from_pattern} → {forbidden} forbidden ({src.slug} → {tgt.slug})",
                            fix_available=False,
                        ))
    return findings


def check_cluster_links(wiki_dir: Path) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for page in scan_wiki(wiki_dir):
        for gap in cluster_gaps(wiki_dir, page):
            findings.append(LintFinding(
                check="cluster-link-gap",
                severity=LintSeverity.WARNING,
                file=page.path,
                line=0,
                message=f"{page.slug}: {gap}",
                fix_available=False,
                suggested_fix=(
                    "Add a typed cluster link such as belongs_to, affects, implements, "
                    "service, target_module, defined_in, or consumers."
                ),
            ))
    return findings


def check_agentops_state(wiki_dir: Path) -> list[LintFinding]:
    root = wiki_dir / "agentops"
    if not root.exists():
        return []
    from tools._agentops import GOVERNANCE_STATUSES, SESSION_STATUSES, list_entities
    from tools.backlog import validate_backlog
    from tools.handoff import validate_handoffs

    required = {
        "orchestrator": ["goal", "current_objective", "snapshot", "governance_status"],
        "track": ["objective", "owner", "agent_role", "dependencies", "acceptance_criteria"],
        "agent": ["role", "scope", "permissions"],
        "session": ["session_id", "agent_role", "goal", "scope", "snapshot", "files_changed", "contracts_changed", "decisions", "risks", "tests", "result", "next_steps"],
        "handoff": ["from_agent", "to_agent", "context_summary", "completed_work", "unfinished_work", "files", "contracts", "risks", "decisions", "next_action"],
        "decision": ["owner", "context", "decision", "consequences", "affected_refs", "source_session"],
        "backlog_item": ["description", "owner", "agent_role", "priority", "status", "track", "dependencies", "contracts", "files", "acceptance_criteria", "evidence"],
        "release": ["version", "governance_status", "blockers", "evidence"],
    }
    findings: list[LintFinding] = []
    for entity_type, fields in required.items():
        for entity in list_entities(wiki_dir, entity_type):
            for field in fields:
                if field not in entity.frontmatter:
                    findings.append(LintFinding(
                        check="agentops-schema",
                        severity=LintSeverity.ERROR,
                        file=str(entity.path),
                        line=0,
                        message=f"{entity.frontmatter.get('id', entity.path.stem)} missing `{field}`",
                    ))
            status = entity.frontmatter.get("status")
            if entity_type == "session" and status not in SESSION_STATUSES:
                findings.append(LintFinding(
                    check="agentops-session-status",
                    severity=LintSeverity.ERROR,
                    file=str(entity.path),
                    line=0,
                    message=f"invalid session status: {status}",
                ))
            governance = entity.frontmatter.get("governance_status")
            if governance is not None and governance not in GOVERNANCE_STATUSES:
                findings.append(LintFinding(
                    check="agentops-governance-status",
                    severity=LintSeverity.ERROR,
                    file=str(entity.path),
                    line=0,
                    message=f"invalid governance status: {governance}",
                ))
    for message in [*validate_backlog(wiki_dir), *validate_handoffs(wiki_dir)]:
        findings.append(LintFinding(
            check="agentops-state",
            severity=LintSeverity.ERROR,
            file=str(root),
            line=0,
            message=message,
        ))
    return findings


def run_all_checks(wiki_dir: Path, schema: dict, dir_to_type: dict, dependency_rules: list[dict]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    findings += check_broken_wikilinks(wiki_dir)
    findings += check_missing_reverse_links(wiki_dir)
    findings += check_orphans(wiki_dir)
    findings += check_required_frontmatter(wiki_dir, schema, dir_to_type)
    findings += check_duplicate_slugs(wiki_dir)
    findings += check_dependency_rules(wiki_dir, dependency_rules)
    findings += check_cluster_links(wiki_dir)
    findings += check_agentops_state(wiki_dir)
    return findings


def apply_fixes(findings: list[LintFinding], wiki_dir: Path) -> int:
    """Applies safe fixes; returns count of fixes applied."""
    fixed = 0
    for f in findings:
        if not f.fix_available:
            continue
        if f.check == "missing-reverse-link":
            # Parse: "<tgt-slug>.<reverse> missing reverse for <src-slug>.<key>"
            try:
                tgt_part, _, src_part = f.message.replace("missing reverse for ", "").partition(" ")
                tgt_slug, _, _ = tgt_part.partition(".")
                src_slug, _, key = src_part.partition(".")
                add_edge(wiki_dir, source=tgt_slug, target=src_slug,
                         relation=_lookup_reverse(key), bidirectional=False)
                fixed += 1
            except Exception:
                continue
    return fixed


def _lookup_reverse(key: str) -> str:
    from tools.wiki_engine import REVERSE_OF
    return REVERSE_OF.get(key, key)


@click.command()
@click.option("--wiki-dir", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--fix", is_flag=True, help="Apply safe fixes in place.")
@click.option("--suggest", is_flag=True, help="Print suggestions but don't write.")
@click.option("--dry-run", is_flag=True, help="Run checks, exit nonzero if any errors found.")
@click.option("--config", type=click.Path(path_type=Path, exists=True),
              help="Path to alpha-wiki config (preset+overlay merged) for schema.")
def cli(wiki_dir: Path, fix: bool, suggest: bool, dry_run: bool, config: Path | None):
    schema, dir_to_type, dep_rules = _load_config(config)
    findings = run_all_checks(wiki_dir, schema, dir_to_type, dep_rules)
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    warnings = [f for f in findings if f.severity == LintSeverity.WARNING]

    if fix:
        n = apply_fixes(findings, wiki_dir)
        click.echo(f"applied {n} fix(es); re-running checks...")
        findings = run_all_checks(wiki_dir, schema, dir_to_type, dep_rules)
        errors = [f for f in findings if f.severity == LintSeverity.ERROR]
        warnings = [f for f in findings if f.severity == LintSeverity.WARNING]

    for f in findings:
        icon = "ERROR" if f.severity == LintSeverity.ERROR else "WARN"
        click.echo(f"{icon} [{f.check}] {f.file}: {f.message}")
        if suggest and f.suggested_fix:
            click.echo(f"   -> {f.suggested_fix}")

    click.echo(f"\nsummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        raise SystemExit(1)
    if dry_run and warnings:
        raise SystemExit(2)


def _load_config(config_path: Path | None) -> tuple[dict, dict, list]:
    if config_path is None:
        return {}, {}, []
    import yaml
    cfg = yaml.safe_load(config_path.read_text())
    schema = {t["name"]: t.get("frontmatter_required", []) for t in cfg.get("entity_types", [])}
    dir_to_type = {t["dir"].rstrip("/"): t["name"] for t in cfg.get("entity_types", [])}
    dep_rules = cfg.get("dependency_rules", [])
    return schema, dir_to_type, dep_rules


if __name__ == "__main__":
    cli()
