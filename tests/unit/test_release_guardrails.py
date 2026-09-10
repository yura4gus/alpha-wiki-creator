"""Release guardrails: version-drift guard and minimal packaging smoke.

These tests exist to prevent the v0.1.0 stale-plugin class of bug: a release
that lands on `main` but leaves one or more version declarations unchanged, so
`claude plugin update` sees an unchanged version and serves a stale build.
"""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]

EXPECTED_SKILLS = {
    "init",
    "ingest",
    "lint",
    "query",
    "render",
    "evolve",
    "status",
    "spawn-agent",
    "doctor",
    "review",
    "rollup",
    "audit-project",
    "orchestrate",
    "backlog",
    "handoff",
    "release-check",
}


def _declared_versions() -> dict[str, str]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    codex_plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    return {
        "pyproject.toml [project.version]": pyproject["project"]["version"],
        ".claude-plugin/plugin.json [version]": plugin["version"],
        ".codex-plugin/plugin.json [version]": codex_plugin["version"],
        ".claude-plugin/marketplace.json [metadata.version]": marketplace["metadata"]["version"],
        ".claude-plugin/marketplace.json [plugins[0].version]": marketplace["plugins"][0]["version"],
    }


def test_version_declarations_are_consistent():
    versions = _declared_versions()
    unique = set(versions.values())
    assert len(unique) == 1, (
        "Version drift across manifests would let `claude plugin update` serve a "
        "stale build. Align every declaration:\n"
        + "\n".join(f"  {source} = {value}" for source, value in versions.items())
    )


def test_changelog_documents_current_version():
    version = _declared_versions()["pyproject.toml [project.version]"]
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert f"## [{version}]" in changelog, (
        f"CHANGELOG.md is missing a '## [{version}]' section for the packaged version."
    )


def test_expected_skills_are_present():
    skills_dir = ROOT / "skills"
    present = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").exists()}
    missing = EXPECTED_SKILLS - present
    assert not missing, f"Missing skills (broken install surface): {sorted(missing)}"
    # Guard the three skills that were absent from the stale 0.1.0 cache.
    for name in ("doctor", "review", "rollup"):
        assert name in present, f"Regression: '{name}' skill dropped from the release surface."


def test_readme_documents_reinstall_flow():
    readme = (ROOT / "README.md").read_text()
    for phrase in (
        "claude plugin marketplace update alpha",
        "claude plugin uninstall alpha-wiki@alpha",
        "claude plugin install alpha-wiki@alpha",
    ):
        assert phrase in readme, f"README is missing the reinstall/update instruction: {phrase!r}"


def test_readme_documents_current_codex_upgrade_flow():
    readme = (ROOT / "README.md").read_text()

    assert "npm install -g @openai/codex@latest" in readme
    assert "python3 scripts/install_codex.py --upgrade --remove-legacy" in readme
    assert "$alpha-wiki:init" in readme


def test_no_stale_skill_count_or_beta_release_references():
    readme = (ROOT / "README.md").read_text()
    marketplace = (ROOT / ".claude-plugin" / "marketplace.json").read_text()
    claude_md = (ROOT / "CLAUDE.md").read_text()
    for stale in ("11 skills", "11 slash commands", "11 skills + 11 slash"):
        assert stale not in readme, f"stale skill count in README: {stale!r}"
        assert stale not in marketplace, f"stale skill count in marketplace: {stale!r}"
    # audit-project must be visible in the primary surfaces.
    assert "audit-project" in readme
    assert "audit-project" in claude_md
    assert "audit-project" in marketplace
    # README must not advertise an old beta tag as the latest release.
    assert "Latest release: [`v0.2.0-beta.1`]" not in readme


def test_spawn_agent_contract_includes_scope_and_security():
    skill = (ROOT / "skills" / "spawn-agent" / "SKILL.md").read_text().lower()
    assert "active product scope" in skill, "spawn-agent must carry active scope into generated prompts"
    assert "out-of-scope" in skill, "spawn-agent must carry out-of-scope modules so agents don't drift"
    assert "security constraint" in skill, "spawn-agent must carry security constraints as hard limits"


def test_all_skills_define_codex_native_delegation_policy():
    for name in EXPECTED_SKILLS:
        skill = (ROOT / "skills" / name / "SKILL.md").read_text()
        assert "## Codex Native Delegation" in skill, (
            f"{name} must state whether and how native Codex subagents are used"
        )
        assert "references/codex-subagent-orchestration.md" in skill


def test_deterministic_operations_remain_controller_owned():
    required = {
        "doctor": "Do not spawn subagents for doctor",
        "lint": "Do not fan out lint",
        "status": "Do not spawn subagents for status",
        "render": "Do not spawn subagents for render",
        "rollup": "Do not fan out rollup",
    }
    for name, phrase in required.items():
        skill = (ROOT / "skills" / name / "SKILL.md").read_text()
        assert phrase in skill


def test_spawn_agent_supports_native_run_modes_without_new_skill():
    skill = (ROOT / "skills" / "spawn-agent" / "SKILL.md").read_text()

    for mode in ("create-profile", "run-now", "run-parallel"):
        assert mode in skill
    for status in ("GREEN", "FIXES_REQUIRED", "BLOCKED", "UNPROVEN", "STALE_SNAPSHOT"):
        assert status in skill
    assert len(EXPECTED_SKILLS) == 16


def test_codex_subagent_contract_covers_snapshot_synthesis_and_write_ownership():
    contract = (ROOT / "references" / "codex-subagent-orchestration.md").read_text()

    for phrase in (
        "Controller Preflight",
        "immutable snapshot",
        "STALE_SNAPSHOT",
        "Truth Precedence",
        "one writer per wave",
        "at most one bounded retry",
        "close their threads",
        "<sha>+worktree:<digest>",
        "path:line@snapshot:<digest>",
    ):
        assert phrase in contract


def test_docs_publishing_has_release_checklist():
    docs = (ROOT / "docs" / "docs-publishing.md").read_text()
    assert "Release Checklist" in docs, "docs/docs-publishing.md is missing the Release Checklist section."
    assert "Bump the version" in docs, "Release checklist must call out the mandatory version bump."
    assert "git tag" in docs, "Release checklist must document tagging the release."
