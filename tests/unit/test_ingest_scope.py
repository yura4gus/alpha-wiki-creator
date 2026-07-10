"""Warning-only scope enforcement during ingest (v0.3 tail).

Records active-scope discipline: ingest surfaces a non-blocking warning when a
source matches an out-of-scope module recorded in the init source manifest.
Deterministic; no wall-clock coupling.
"""
from pathlib import Path

from tools.ingest_pipeline import scope_warnings


def _manifest(project: Path, out_of_scope: str) -> None:
    manifest = project / "raw" / "docs" / "source-manifest.md"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# Source Manifest\n\n## Scope\n\n"
        "- Active scope: ZamWallet Web / Web Wallet\n"
        f"- Out of scope: {out_of_scope}\n"
    )


def test_scope_warning_flags_out_of_scope_source(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _manifest(tmp_path, "Launchpad, ZAMpad, dApp, DeFi")

    sources = [
        tmp_path / "docs" / "launchpad-spec.md",
        tmp_path / "docs" / "wallet-web-auth.md",
    ]
    warnings = scope_warnings(wiki, sources)

    assert len(warnings) == 1
    assert "launchpad-spec.md" in warnings[0]
    assert "Launchpad" in warnings[0]


def test_no_warning_when_scope_unrecorded(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    # No manifest at all.
    assert scope_warnings(wiki, [tmp_path / "docs" / "launchpad.md"]) == []


def test_no_warning_when_out_of_scope_is_empty(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _manifest(tmp_path, "_(none recorded)_")
    assert scope_warnings(wiki, [tmp_path / "docs" / "launchpad.md"]) == []


def test_in_scope_sources_produce_no_warnings(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _manifest(tmp_path, "Launchpad, DeFi")
    sources = [tmp_path / "docs" / "wallet-web-session.md", tmp_path / "docs" / "api-auth.md"]
    assert scope_warnings(wiki, sources) == []
