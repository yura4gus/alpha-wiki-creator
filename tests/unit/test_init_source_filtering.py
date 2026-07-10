"""Init corpus curation: vendor exclusion, classification, duplicates, scope, Batch 1.

Regression coverage for the Zamio / ZamWallet finding where init proposed 253
candidates dominated by `repos/*/vendor/**` noise. Deterministic — no wall clock.
"""
from pathlib import Path

from tools.init_audit import (
    CAT_DUPLICATE,
    CAT_GENERATED,
    CAT_THIRD_PARTY,
    InitScope,
    batch1_plan,
    discover_sources,
    write_source_manifest,
)


def _write(path: Path, text: str = "# doc\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_vendor_and_dependency_dirs_are_excluded(tmp_path: Path):
    _write(tmp_path / "repos" / "wallet" / "vendor" / "lib" / "README.md")
    _write(tmp_path / "node_modules" / "pkg" / "README.md")
    _write(tmp_path / ".next" / "cache" / "meta.json", "{}\n")
    _write(tmp_path / "coverage" / "report.md")
    _write(tmp_path / "logs" / "run.txt", "log\n")
    _write(tmp_path / "docs" / "architecture.md")

    paths = {str(item.path) for item in discover_sources(tmp_path)}

    assert "docs/architecture.md" in paths
    assert not any("vendor" in p for p in paths)
    assert not any("node_modules" in p for p in paths)
    assert not any(".next" in p for p in paths)
    assert not any("coverage" in p for p in paths)
    assert not any(p.startswith("logs/") for p in paths)


def test_third_party_and_lockfiles_are_classified_as_noise(tmp_path: Path):
    _write(tmp_path / "LICENSE.md", "MIT License\n")
    _write(tmp_path / "uv.lock", "lock\n")            # .lock suffix: excluded before classification
    _write(tmp_path / "package-lock.json", "{}\n")    # doc-ish suffix: kept but marked generated
    _write(tmp_path / "docs" / "design-overview.md")

    by_name = {str(item.path): item for item in discover_sources(tmp_path)}

    assert "uv.lock" not in by_name, "lockfiles with non-doc suffixes should be excluded outright"
    assert by_name["LICENSE.md"].category == CAT_THIRD_PARTY
    assert by_name["package-lock.json"].category == CAT_GENERATED

    batch1_paths = {str(i.path) for i in batch1_plan(list(by_name.values()))}
    assert "LICENSE.md" not in batch1_paths
    assert "package-lock.json" not in batch1_paths
    assert "docs/design-overview.md" in batch1_paths


def test_duplicate_docs_pick_canonical_source_of_truth(tmp_path: Path):
    # Workspace-level copy vs. the repo's own docs copy (canonical).
    _write(tmp_path / "docs" / "adr-010.md", "# ADR 10 (workspace draft)\n")
    _write(tmp_path / "repos" / "wallet-trade-v2" / "docs" / "adr-010.md", "# ADR 10 (canonical)\n")

    items = {str(i.path): i for i in discover_sources(tmp_path)}
    canonical = items["repos/wallet-trade-v2/docs/adr-010.md"]
    mirror = items["docs/adr-010.md"]

    assert canonical.canonical is True
    assert mirror.canonical is False
    assert mirror.category == CAT_DUPLICATE
    assert mirror.duplicate_of == "repos/wallet-trade-v2/docs/adr-010.md"
    assert str(mirror.path) not in {str(i.path) for i in batch1_plan(list(items.values()))}


def test_scope_is_recorded_in_manifest(tmp_path: Path):
    _write(tmp_path / "docs" / "architecture.md")
    scope = InitScope(
        active=["ZamWallet Web / Web Wallet"],
        out_of_scope=["Launchpad", "ZAMpad", "dApp", "DeFi"],
        deferred=["ecosystem expansion"],
        canonical_notes=["Canonical ADRs live under repos/wallet-trade-v2/docs/"],
        decisions=["Narrowed focus to Web Wallet first"],
    )

    out = write_source_manifest(tmp_path, scope=scope)
    text = out.read_text()

    assert "Active scope: ZamWallet Web / Web Wallet" in text
    assert "Out of scope: Launchpad, ZAMpad, dApp, DeFi" in text
    assert "Deferred: ecosystem expansion" in text
    assert "Canonical ADRs live under repos/wallet-trade-v2/docs/" in text
    assert "Narrowed focus to Web Wallet first" in text


def test_manifest_has_structured_sections(tmp_path: Path):
    _write(tmp_path / "docs" / "architecture.md")
    _write(tmp_path / "LICENSE", "MIT\n")

    text = write_source_manifest(tmp_path).read_text()

    for heading in (
        "## Scope",
        "## Canonical Sources (Batch 1)",
        "## Deferred Sources (later batches)",
        "## Duplicates / Source Mirrors",
        "## Excluded Folders",
        "## Excluded File Categories",
    ):
        assert heading in text, f"manifest missing section: {heading}"


def test_batch1_prefers_durable_memory_over_noise(tmp_path: Path):
    _write(tmp_path / "docs" / "architecture.md")
    _write(tmp_path / "docs" / "security-model.md")
    _write(tmp_path / "docs" / "release-notes.md")
    _write(tmp_path / "repos" / "x" / "vendor" / "dep" / "README.md")  # excluded entirely
    _write(tmp_path / "NOTICE", "third party\n")

    candidates = discover_sources(tmp_path)
    plan = {str(i.path) for i in batch1_plan(candidates)}

    assert "docs/architecture.md" in plan
    assert "docs/security-model.md" in plan
    assert "docs/release-notes.md" in plan
    assert "NOTICE" not in plan
    assert not any("vendor" in p for p in plan)
