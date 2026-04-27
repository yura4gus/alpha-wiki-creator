"""Wiki structural lint. Pure Python, no LLM."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from tools._models import LintFinding, LintSeverity
from tools.wiki_engine import scan_wiki, parse_page, EDGE_KEYS, REVERSE_OF, _coerce_targets, rebuild_edges


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
    index_text = (wiki_dir / "index.md").read_text() if (wiki_dir / "index.md").exists() else ""
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
