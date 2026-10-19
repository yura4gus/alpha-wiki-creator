from __future__ import annotations

from pathlib import Path, PurePosixPath
import json
import subprocess

import pytest

from tools.document_worker import check_document_governance, load_policy, record_change
from tools.document_maintenance import apply_maintenance, hierarchy_findings, plan_maintenance


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    (root / ".alpha-wiki").mkdir(parents=True)
    (root / "wiki" / "specs").mkdir(parents=True)
    (root / "wiki" / "graph").mkdir(parents=True)
    config = root / ".alpha-wiki" / "config.yaml"
    config.write_text(
        """document_governance:
  enabled: true
  global_log: wiki/log.md
  canonical_files: [README.md, AGENTS.md]
  canonical_roots: [wiki]
  excluded_files: [wiki/index.md, wiki/log.md]
  excluded_roots: [wiki/graph, wiki/render, wiki/agentops]
"""
    )
    (root / "README.md").write_text("# Project\n")
    (root / "AGENTS.md").write_text("# Agents\n")
    (root / "wiki" / "index.md").write_text("# Index\n")
    (root / "wiki" / "log.md").write_text("# Log\n")
    (root / "wiki" / "specs" / "product.md").write_text(
        "---\ntitle: Product\nslug: product-spec\n---\n# Product\n"
    )
    _git(root, "init")
    _git(root, "config", "user.email", "alpha-wiki@example.test")
    _git(root, "config", "user.name", "Alpha Wiki")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")
    return root, config


def test_changed_canonical_document_requires_global_log_entry(tmp_path: Path):
    root, config = _project(tmp_path)
    (root / "wiki" / "specs" / "product.md").write_text(
        "---\ntitle: Product\nslug: product-spec\n---\n# Product\n\nUpdated.\n"
    )

    findings = check_document_governance(root, config)

    assert len(findings) == 1
    assert "without a matching wiki/log.md entry" in findings[0]


def test_absolute_import_binding_survives_project_relocation(tmp_path):
    from tools.ingest_pipeline import ingest_files

    root, config = _project(tmp_path)
    source = root / "raw/new-source.md"
    source.parent.mkdir()
    source.write_text("# New Source\n")
    page = ingest_files(root / "wiki", [source.resolve()], slot="specs")[0].page
    assert 'source_file: "raw/new-source.md"' in page.read_text()
    _git(root, "add", ".")
    _git(root, "commit", "-m", "import")
    moved = root.rename(tmp_path / "moved")
    assert check_document_governance(moved, moved / ".alpha-wiki/config.yaml") == []
    plan = plan_maintenance(moved, moved / ".alpha-wiki/config.yaml",
                            (moved / "wiki/specs/new-source.md",))
    assert not plan["gaps"]
    assert "raw/new-source.md" in plan["jobs"][0]["sources"]


def test_legacy_moved_binding_is_a_gap_not_unrelated_governance_failure(tmp_path):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_text(page.read_text().replace("source_file: raw/brief.md",
                                            f"source_file: {source.resolve()}"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "legacy absolute binding")
    moved = root.rename(tmp_path / "moved")
    moved_config = moved / ".alpha-wiki/config.yaml"
    assert check_document_governance(moved, moved_config) == []
    plan = plan_maintenance(moved, moved_config)
    assert not plan["jobs"]
    assert any("relocated" in gap for gap in plan["gaps"])
    assert plan["source_bound_documents"] == 1


def test_retired_slug_can_be_imported_and_registered_again(tmp_path):
    from tools.ingest_pipeline import ingest_files

    root, config = _project(tmp_path)
    source = root / "raw/new-source.md"
    source.parent.mkdir()
    source.write_text("# New Source\n")
    page = ingest_files(root / "wiki", [source], slot="specs")[0].page
    _git(root, "add", ".")
    _git(root, "commit", "-m", "first import")
    page.unlink()
    record_change(root, config, (page,), "Retire source summary", operation="document-retire")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "retire")
    result = ingest_files(root / "wiki", [source], slot="specs")[0]
    assert result.created and result.page == page
    assert (root / "wiki/log.md").read_text().count("pages=[[new-source]]") == 2
    assert check_document_governance(root, config) == []


def test_record_synchronizes_document_and_global_log(tmp_path: Path):
    root, config = _project(tmp_path)
    document = root / "wiki" / "specs" / "product.md"
    document.write_text(document.read_text() + "\nUpdated.\n")

    entry = record_change(root, config, (document,), "Clarify product boundary")

    assert "document-update" in entry
    assert "`wiki/specs/product.md`" in entry
    assert check_document_governance(root, config) == []


def test_ingest_log_registers_new_wiki_page(tmp_path: Path):
    root, config = _project(tmp_path)
    (root / "wiki" / "specs" / "feature.md").write_text(
        "---\ntitle: Feature\nslug: feature-one\n---\n# Feature\n"
    )
    with (root / "wiki" / "log.md").open("a") as stream:
        stream.write("\n## [2026-09-29] ingest | source | pages=[[feature-one]]\n")

    assert check_document_governance(root, config) == []


def test_new_canonical_page_requires_explicit_registration_operation(tmp_path: Path):
    root, config = _project(tmp_path)
    page = root / "wiki" / "specs" / "feature.md"
    page.write_text("---\ntitle: Feature\nslug: feature-one\n---\n# Feature\n")
    with (root / "wiki" / "log.md").open("a") as stream:
        stream.write("\n## [2026-09-29] update | created | pages=[[feature-one]]\n")

    findings = check_document_governance(root, config)

    assert any("requires `ingest` or `document-register`" in finding for finding in findings)
    with pytest.raises(ValueError, match="requires --allow-new"):
        record_change(root, config, (page,), "Add feature spec")


def test_document_log_cannot_claim_unchanged_document(tmp_path: Path):
    root, config = _project(tmp_path)
    with (root / "wiki" / "log.md").open("a") as stream:
        stream.write(
            "\n## [2026-09-29] document-update | no actual edit | "
            "documents=`wiki/specs/product.md`\n"
        )

    findings = check_document_governance(root, config)

    assert any("document did not change" in finding for finding in findings)


def test_generated_and_agentops_files_are_not_canonical(tmp_path: Path):
    root, config = _project(tmp_path)
    (root / "wiki" / "graph" / "context_brief.md").write_text("generated\n")
    agentops = root / "wiki" / "agentops" / "sessions" / "s1.md"
    agentops.parent.mkdir(parents=True)
    agentops.write_text("session\n")

    assert check_document_governance(root, config) == []


def test_initial_commit_uses_bootstrap_as_canonical_registration(tmp_path: Path):
    root = tmp_path / "new-project"
    (root / ".alpha-wiki").mkdir(parents=True)
    (root / "wiki" / "specs").mkdir(parents=True)
    config = root / ".alpha-wiki" / "config.yaml"
    config.write_text(
        """document_governance:
  enabled: true
  global_log: wiki/log.md
  canonical_roots: [wiki]
  excluded_files: [wiki/log.md]
"""
    )
    (root / "wiki" / "specs" / "product.md").write_text("# Product\n")
    (root / "wiki" / "log.md").write_text(
        "# Log\n\n## [2026-09-29] bootstrap | alpha-wiki initialized\n"
    )
    _git(root, "init")
    _git(root, "add", ".")

    assert check_document_governance(root, config, staged=True) == []


def test_hidden_custom_wiki_directory_is_preserved(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """document_governance:
  enabled: true
  global_log: .wiki/log.md
  canonical_roots: [.wiki]
  excluded_roots: [.wiki/graph]
"""
    )

    policy = load_policy(config)

    assert policy.global_log == PurePosixPath(".wiki/log.md")
    assert policy.is_canonical(PurePosixPath(".wiki/specs/product.md"))
    assert not policy.is_canonical(PurePosixPath(".wiki/graph/context_brief.md"))


@pytest.mark.parametrize("name", ["спецификация.md", "product notes.md", "product\tnotes.md"])
def test_git_path_quoting_cannot_hide_document_changes(tmp_path: Path, name: str):
    root, config = _project(tmp_path)
    page = root / "wiki/specs" / name
    page.write_text("# Original\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "unusual name")
    page.write_text("# Updated\n")
    assert any(name in item for item in check_document_governance(root, config))
    record_change(root, config, (page,), "Update existing document")
    assert check_document_governance(root, config) == []


def test_custom_wiki_ingest_slug_is_recognized(tmp_path: Path):
    root, config = _project(tmp_path)
    (root / "wiki").rename(root / ".wiki")
    config.write_text(config.read_text().replace("wiki", ".wiki"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "custom wiki")
    (root / ".wiki/specs/feature.md").write_text("---\nslug: feature-one\n---\n# Feature\n")
    with (root / ".wiki/log.md").open("a") as stream:
        stream.write("\n## [2026-10-18] ingest | source | pages=[[feature-one]]\n")
    assert check_document_governance(root, config) == []


def test_staged_check_reads_staged_slug_and_deleted_log_worktree(tmp_path: Path):
    root, config = _project(tmp_path)
    page = root / "wiki/specs/product.md"
    page.write_text("---\nslug: staged-slug\n---\n# Updated\n")
    (root / "wiki/log.md").write_text("# Log\n\n## [2026-10-18] update | actual | pages=[[staged-slug]]\n")
    _git(root, "add", ".")
    page.write_text("---\nslug: unstaged-slug\n---\n# Later\n")
    (root / "wiki/log.md").unlink()
    assert check_document_governance(root, config, staged=True) == []


def test_record_cannot_disguise_registration_as_update(tmp_path: Path):
    root, config = _project(tmp_path)
    page = root / "wiki/specs/new.md"
    page.write_text("# New\n")
    with pytest.raises(ValueError, match="allow-new"):
        record_change(root, config, (page,), "New", operation="document-update")
    with pytest.raises(ValueError, match="separate records"):
        record_change(root, config, (page,), "New", operation="document-update", allow_new=True)


def test_record_does_not_repeat_identical_change(tmp_path: Path):
    root, config = _project(tmp_path)
    page = root / "README.md"
    page.write_text("# Revised\n")
    record_change(root, config, (page,), "Clarify")
    before = (root / "wiki/log.md").read_bytes()
    record_change(root, config, (page,), "Different wording does not create another change")
    assert (root / "wiki/log.md").read_bytes() == before


def _maintenance_project(tmp_path: Path):
    root, config = _project(tmp_path)
    source = root / "raw/brief.md"
    source.parent.mkdir()
    source.write_text("# Brief\nThe product uses local Markdown memory.\n")
    page = root / "wiki/specs/product.md"
    page.write_text(
        "---\ntitle: Product\nslug: product-spec\nsource_file: raw/brief.md\n---\n# Product\n\n"
        "Repeated narrative.\nRepeated narrative.\n\n## Requirements\n\n- Keep evidence immutable.\n"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "source mapping")
    return root, config, page, source


def _edits(page: Path, root: Path, text: str | None = None):
    return {"summary": "Consolidate repeated context, preserving requirements",
            "updates": [{"document": page.relative_to(root).as_posix(),
                         "text": text if text is not None else page.read_text().replace("Repeated narrative.\n", "", 1)}]}


def test_worker_compacts_existing_page_and_refreshes_once(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    raw_before = source.read_bytes()
    plan = plan_maintenance(root, config, (page,), compact=True)
    proposal = _edits(page, root)
    assert apply_maintenance(root, plan, proposal)["changed"] == ["wiki/specs/product.md"]
    assert page.read_text().count("Repeated narrative.") == 1
    assert "Keep evidence immutable." in page.read_text()
    assert source.read_bytes() == raw_before
    assert check_document_governance(root, config) == []
    for name in ("edges.jsonl", "context_brief.md", "open_questions.md"):
        assert (root / "wiki/graph" / name).is_file()
    snapshot = {path: path.read_bytes() for path in root.rglob("*")
                if path.is_file() and ".git" not in path.parts}
    assert apply_maintenance(root, plan, proposal)["status"] == "unchanged"
    assert all(path.read_bytes() == content for path, content in snapshot.items())
    assert plan_maintenance(root, config)["jobs"] == []
    source.write_text(source.read_text() + "An additional requirement.\n")
    assert len(plan_maintenance(root, config)["jobs"]) == 1


@pytest.mark.parametrize("mutate", ["source", "document", "config"])
def test_worker_rejects_stale_plan_before_edits(tmp_path: Path, mutate: str):
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    proposal = _edits(page, root)
    target = {"source": source, "document": page, "config": config}[mutate]
    target.write_text(target.read_text() + "\n# Concurrent change\n")
    before = page.read_bytes()
    log = (root / "wiki/log.md").read_bytes()
    with pytest.raises(ValueError, match="stale"):
        apply_maintenance(root, plan, proposal)
    assert page.read_bytes() == before
    assert (root / "wiki/log.md").read_bytes() == log
    assert not (root / ".alpha-wiki/maintenance/state.json").exists()


@pytest.mark.parametrize("replacement", ["", "# Lost metadata\n", "remove-requirement", "grow"])
def test_worker_rejects_lossy_compaction(tmp_path: Path, replacement: str):
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config, (page,), compact=True)
    text = {"remove-requirement": page.read_text().replace("- Keep evidence immutable.\n", ""),
            "grow": page.read_text() + "More prose.\n"}.get(replacement, replacement)
    before = page.read_bytes()
    with pytest.raises(ValueError):
        apply_maintenance(root, plan, _edits(page, root, text))
    assert page.read_bytes() == before


def test_worker_structural_preview_prevents_broken_links(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    before = page.read_bytes()
    with pytest.raises(ValueError, match="structural errors"):
        apply_maintenance(root, plan, _edits(page, root, page.read_text() + "\n[[missing-document]]\n"))
    assert page.read_bytes() == before
    assert not (root / "wiki/graph/edges.jsonl").exists()


def test_worker_interrupted_refresh_is_resumable_without_duplicate_log(tmp_path: Path, monkeypatch):
    from tools import wiki_engine
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    edits = _edits(page, root)
    with monkeypatch.context() as patch:
        def interrupted(*args):
            raise OSError("simulated graph write failure")
        patch.setattr(wiki_engine, "rebuild_edges", interrupted)
        with pytest.raises(OSError, match="simulated"):
            apply_maintenance(root, plan, edits)
    assert (root / ".alpha-wiki/maintenance/pending.json").exists()
    assert not (root / ".alpha-wiki/maintenance/state.json").exists()
    with pytest.raises(ValueError, match="unfinished"):
        plan_maintenance(root, config)
    log = (root / "wiki/log.md").read_bytes()
    assert apply_maintenance(root, plan, edits)["status"] == "applied"
    assert (root / "wiki/log.md").read_bytes() == log
    assert not (root / ".alpha-wiki/maintenance/pending.json").exists()


def test_worker_preserves_concurrent_edits_during_recovery(tmp_path: Path, monkeypatch):
    from tools import wiki_engine
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    edits = _edits(page, root)
    with monkeypatch.context() as patch:
        patch.setattr(wiki_engine, "rebuild_edges", lambda *args: (_ for _ in ()).throw(OSError("stop")))
        with pytest.raises(OSError):
            apply_maintenance(root, plan, edits)
    page.write_text(page.read_text() + "\nConcurrent human edit.\n")
    before = page.read_bytes()
    with pytest.raises(ValueError, match="concurrent document"):
        apply_maintenance(root, plan, edits)
    assert page.read_bytes() == before
    assert (root / ".alpha-wiki/maintenance/pending.json").exists()


def test_worker_reviewed_no_change_checkpoints_without_log_noise(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    log = (root / "wiki/log.md").read_bytes()
    result = apply_maintenance(root, plan, _edits(page, root, page.read_text()))
    assert result["changed"] == []
    assert (root / "wiki/log.md").read_bytes() == log
    assert plan_maintenance(root, config)["jobs"] == []


def test_worker_preserves_unprocessed_batch_jobs(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    second = page.with_name("second.md")
    second.write_text(page.read_text().replace("product-spec", "second-spec"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "second projection")
    plan = plan_maintenance(root, config)
    assert len(plan["jobs"]) == 2
    apply_maintenance(root, plan, _edits(page, root))
    assert [job["document"] for job in plan_maintenance(root, config)["jobs"]] == ["wiki/specs/second.md"]
    apply_maintenance(root, plan, _edits(second, root))
    assert plan_maintenance(root, config)["jobs"] == []


def test_worker_reports_missing_sources_without_claiming_sync(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    source.unlink()
    plan = plan_maintenance(root, config)
    assert plan["jobs"] == [] and "missing source" in plan["gaps"][0]


def test_worker_bounds_batches_and_requires_explicit_compaction_scope(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    with pytest.raises(ValueError, match="explicit"):
        plan_maintenance(root, config, compact=True)
    second = page.with_name("second.md")
    second.write_text(page.read_text().replace("product-spec", "second-spec"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "another projection")
    plan = plan_maintenance(root, config, limit=1)
    assert len(plan["jobs"]) == 1 and plan["deferred"] == 1


@pytest.mark.parametrize("source", ["../outside.md", "wiki/graph/context_brief.md", ".alpha-wiki/config.yaml"])
def test_worker_rejects_escaping_or_generated_source_bindings(tmp_path: Path, source: str):
    root, config, page, original = _maintenance_project(tmp_path)
    page.write_text(page.read_text().replace("raw/brief.md", source))
    with pytest.raises(ValueError):
        plan_maintenance(root, config)


def test_worker_rejects_symlink_and_concurrent_writer(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    original = page.read_text()
    page.unlink()
    page.symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        plan_maintenance(root, config)
    page.unlink()
    page.write_text(original)
    plan = plan_maintenance(root, config)
    state = root / ".alpha-wiki/maintenance"
    state.mkdir()
    (state / "worker.lock").write_text("another worker")
    with pytest.raises(ValueError, match="locked"):
        apply_maintenance(root, plan, _edits(page, root))


@pytest.mark.parametrize("parent", ['["[[product-spec]]", "[[other]]"]', '"[[missing]]"', '"[[product-spec]]"'])
def test_worker_validates_ownership_not_dependency_hierarchy(tmp_path: Path, parent: str):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_text(page.read_text().replace("source_file:", f"belongs_to: {parent}\nsource_file:"))
    assert hierarchy_findings(root, config)
    assert check_document_governance(root, config)


def test_worker_cli_plan_is_read_only_and_output_is_generated(tmp_path: Path):
    from click.testing import CliRunner
    from tools.document_worker import cli
    root, config, page, source = _maintenance_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "--root", str(root), "--document", "wiki/specs/product.md"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.output)["jobs"]) == 1
    assert not (root / ".alpha-wiki/maintenance").exists()
    result = runner.invoke(cli, ["plan", "--root", str(root), "--output", "README.md"])
    assert result.exit_code != 0


def test_compaction_preserves_nested_normative_sections(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_text(page.read_text() + "\n### Security\n\nPrivate keys never enter the backend.\n")
    plan = plan_maintenance(root, config, (page,), compact=True)
    with pytest.raises(ValueError, match="requirements section"):
        apply_maintenance(root, plan, _edits(page, root, page.read_text().replace("Private keys never enter the backend.\n", "")))


def test_compaction_cannot_remove_cross_document_references(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_text(page.read_text().replace("# Product\n", "# Product\n\nSee [source](../../raw/brief.md).\n"))
    plan = plan_maintenance(root, config, (page,), compact=True)
    with pytest.raises(ValueError, match="references"):
        apply_maintenance(root, plan, _edits(page, root, page.read_text().replace("See [source](../../raw/brief.md).\n", "")))


def test_source_owners_and_dependents_need_separate_batches(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    dependent = page.with_name("dependent.md")
    dependent.write_text(page.read_text().replace("product-spec", "dependent-spec").replace("raw/brief.md", "wiki/specs/product.md"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "dependent projection")
    plan = plan_maintenance(root, config)
    edits = _edits(page, root)
    edits["updates"].extend(_edits(dependent, root)["updates"])
    with pytest.raises(ValueError, match="owner first"):
        apply_maintenance(root, plan, edits)


def test_registered_uncommitted_page_can_be_maintained(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    new = page.with_name("registered.md")
    new.write_text(page.read_text().replace("product-spec", "registered-spec"))
    plan = plan_maintenance(root, config, (new,))
    assert plan["jobs"] == [] and "register" in plan["gaps"][0]
    record_change(root, config, (new,), "Register independently owned page", allow_new=True)
    plan = plan_maintenance(root, config, (new,))
    assert len(plan["jobs"]) == 1
    apply_maintenance(root, plan, _edits(new, root))
    assert check_document_governance(root, config) == []


def test_global_journal_source_mention_does_not_cover_unrelated_document(tmp_path: Path):
    root, config = _project(tmp_path)
    (root / "README.md").write_text("# Changed\n")
    (root / "wiki/log.md").write_text(
        "# Log\n\n## [2026-10-18] document-update | actual | documents=`AGENTS.md` | sources=`README.md`\n"
    )
    assert any("README.md: canonical document changed" in finding
               for finding in check_document_governance(root, config))


def test_latest_context_works_with_prepended_and_appended_journal(tmp_path: Path):
    from tools.wiki_engine import rebuild_context_brief
    root, config = _project(tmp_path)
    (root / "wiki/log.md").write_text(
        "# Log\n\n## [2026-10-17] update | newer prepended\n"
        "\n## [2026-05-05] bootstrap | historical\n"
        "\n## [2026-10-18] document-update | latest appended\n"
    )
    result = rebuild_context_brief(root / "wiki").read_text()
    assert result.index("latest appended") < result.index("newer prepended") < result.index("historical")


def test_compaction_preserves_russian_normative_sections(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_text(page.read_text().replace("## Requirements", "## Требования"))
    plan = plan_maintenance(root, config, (page,), compact=True)
    with pytest.raises(ValueError, match="требования"):
        apply_maintenance(root, plan, _edits(page, root, page.read_text().replace("- Keep evidence immutable.\n", "")))


def test_no_change_review_preserves_crlf_and_its_checkpoint(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
    plan = plan_maintenance(root, config)
    before = page.read_bytes()
    proposal = _edits(page, root, page.read_text())
    assert apply_maintenance(root, plan, proposal)["changed"] == []
    assert page.read_bytes() == before
    assert plan_maintenance(root, config)["jobs"] == []
    assert apply_maintenance(root, plan, proposal)["status"] == "unchanged"


def test_repository_root_aliases_resolve_like_macos_var_paths(tmp_path: Path):
    root, config, page, source = _maintenance_project(tmp_path)
    alias = tmp_path / "project-alias"
    alias.symlink_to(root, target_is_directory=True)
    aliased_config = alias / ".alpha-wiki/config.yaml"
    assert check_document_governance(alias, aliased_config) == []
    plan = plan_maintenance(alias, aliased_config)
    assert plan["root"] == str(root.resolve()) and len(plan["jobs"]) == 1
    apply_maintenance(alias, plan, _edits(page, root))
    assert check_document_governance(alias, aliased_config) == []


def test_recovery_rechecks_documents_reviewed_without_edits(tmp_path: Path, monkeypatch):
    from tools import wiki_engine
    root, config, page, source = _maintenance_project(tmp_path)
    second = page.with_name("second.md")
    second.write_text(page.read_text().replace("product-spec", "second-spec"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "second page")
    plan = plan_maintenance(root, config)
    edits = _edits(page, root)
    edits["updates"].extend(_edits(second, root, second.read_text())["updates"])
    with monkeypatch.context() as patch:
        patch.setattr(wiki_engine, "rebuild_edges", lambda *args: (_ for _ in ()).throw(OSError("stop")))
        with pytest.raises(OSError):
            apply_maintenance(root, plan, edits)
    second.write_text(second.read_text() + "Concurrent change after review.\n")
    with pytest.raises(ValueError, match="concurrent document"):
        apply_maintenance(root, plan, edits)
    assert not (root / ".alpha-wiki/maintenance/state.json").exists()


def test_sources_changed_during_refresh_are_not_checkpointed(tmp_path: Path, monkeypatch):
    from tools import wiki_engine
    root, config, page, source = _maintenance_project(tmp_path)
    plan = plan_maintenance(root, config)
    original = wiki_engine.rebuild_edges
    def concurrent_change(wiki):
        result = original(wiki)
        source.write_text(source.read_text() + "Changed during refresh.\n")
        return result
    monkeypatch.setattr(wiki_engine, "rebuild_edges", concurrent_change)
    with pytest.raises(ValueError, match="source changed before checkpoint"):
        apply_maintenance(root, plan, _edits(page, root))
    assert not (root / ".alpha-wiki/maintenance/state.json").exists()
    assert (root / ".alpha-wiki/maintenance/pending.json").exists()
