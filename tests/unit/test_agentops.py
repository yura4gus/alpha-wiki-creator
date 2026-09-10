from __future__ import annotations

from datetime import date
from pathlib import Path

from click.testing import CliRunner

from tools._agentops import ROLE_DEFINITIONS, initialize_agentops, list_entities, load_entity
from tools.backlog import cli as backlog_cli
from tools.backlog import dependency_gaps, validate_backlog
from tools.handoff import cli as handoff_cli
from tools.handoff import validate_handoffs
from tools.orchestrate import cli as orchestrate_cli
from tools.release_check import release_check_report
from tools.release_check import cli as release_check_cli
from tools.rollup import rollup_report, write_rollup


def _wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index\n")
    (wiki / "log.md").write_text("# Log\n")
    initialize_agentops(
        wiki,
        goal="Ship a reliable release",
        current_objective="Close release evidence",
        snapshot="abc123",
    )
    return wiki


def _add_item(
    runner: CliRunner,
    wiki: Path,
    item_id: str,
    *,
    status: str = "TODO",
    dependency: str | None = None,
    evidence: str | None = None,
) -> None:
    args = [
        "add", "--wiki-dir", str(wiki), "--id", item_id,
        "--title", f"Task {item_id}", "--description", "Bounded work",
        "--owner", "backend-owner", "--role", "backend", "--priority", "1",
        "--status", status, "--track", "general", "--acceptance", "Tests pass",
        "--file", f"src/{item_id}.py",
    ]
    if dependency:
        args.extend(["--dependency", dependency])
    if evidence:
        args.extend(["--evidence", evidence])
    result = runner.invoke(backlog_cli, args)
    assert result.exit_code == 0, result.output


def test_agentops_init_creates_namespaced_state_and_eight_roles(tmp_path: Path):
    wiki = _wiki(tmp_path)

    assert (wiki / "agentops" / "orchestrator.md").exists()
    assert (wiki / "agentops" / "SCHEMA.md").exists()
    assert set(ROLE_DEFINITIONS) == {
        entity.frontmatter["role"] for entity in list_entities(wiki, "agent")
    }
    assert len(list_entities(wiki, "agent")) == 8
    assert load_entity(wiki, "orchestrator", "orchestrator").frontmatter["snapshot"] == "abc123"


def test_backlog_supports_many_items_filters_and_dependency_validation(tmp_path: Path):
    wiki = _wiki(tmp_path)
    runner = CliRunner()

    for index in range(120):
        _add_item(runner, wiki, f"T-{index:03d}")

    files = list((wiki / "agentops" / "backlog").glob("*.md"))
    assert len(files) == 120
    listed = runner.invoke(
        backlog_cli,
        ["list", "--wiki-dir", str(wiki), "--role", "backend", "--track", "general"],
    )
    assert listed.exit_code == 0
    assert "Items: 120" in listed.output
    assert validate_backlog(wiki) == []

    items = [
        {"id": "base", "status": "TODO", "dependencies": []},
        {"id": "child", "status": "IN_PROGRESS", "dependencies": ["base"]},
    ]
    assert dependency_gaps(items) == ["child: dependency base is TODO"]


def test_backlog_rejects_unknown_role_and_done_without_evidence(tmp_path: Path):
    wiki = _wiki(tmp_path)
    runner = CliRunner()

    unknown = runner.invoke(
        backlog_cli,
        [
            "add", "--wiki-dir", str(wiki), "--id", "bad-role", "--title", "Bad",
            "--description", "Bad role", "--owner", "nobody", "--role", "unknown",
            "--priority", "1", "--track", "general", "--acceptance", "Never",
        ],
    )
    assert unknown.exit_code != 0
    assert "agent unknown" in unknown.output

    no_evidence = runner.invoke(
        backlog_cli,
        [
            "add", "--wiki-dir", str(wiki), "--id", "no-proof", "--title", "No proof",
            "--description", "Missing evidence", "--owner", "owner", "--role", "qa",
            "--priority", "1", "--status", "DONE", "--track", "general",
            "--acceptance", "Tests pass",
        ],
    )
    assert no_evidence.exit_code != 0
    assert "DONE requires" in no_evidence.output


def test_validators_catch_manually_corrupted_references(tmp_path: Path):
    wiki = _wiki(tmp_path)
    runner = CliRunner()
    _add_item(runner, wiki, "T-1")
    backlog_path = wiki / "agentops" / "backlog" / "t-1.md"
    backlog_path.write_text(backlog_path.read_text().replace("agent_role: backend", "agent_role: missing"))
    assert "T-1: unknown agent_role missing" in validate_backlog(wiki)

    handoff = runner.invoke(
        handoff_cli,
        [
            "create", "--wiki-dir", str(wiki), "--id", "H-1", "--from-agent", "backend",
            "--to-agent", "qa", "--context", "Ready for QA", "--next-action", "Run tests",
        ],
    )
    assert handoff.exit_code == 0, handoff.output
    handoff_path = wiki / "agentops" / "handoffs" / "h-1.md"
    handoff_path.write_text(handoff_path.read_text().replace("to_agent: qa", "to_agent: missing"))
    assert "H-1: unknown to_agent missing" in validate_handoffs(wiki)


def test_agentops_writes_require_explicit_initialization(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index\n")
    (wiki / "log.md").write_text("# Log\n")

    release = CliRunner().invoke(
        release_check_cli,
        ["--wiki-dir", str(wiki), "--version", "test", "--write"],
    )
    assert release.exit_code != 0
    assert not (wiki / "agentops").exists()

    try:
        write_rollup(wiki, scope="agentops")
    except Exception as exc:
        assert "orchestrator" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("AgentOps rollup unexpectedly initialized state")
    assert not (wiki / "agentops").exists()


def test_session_handoff_rollup_and_release_check_form_closed_cycle(tmp_path: Path):
    wiki = _wiki(tmp_path)
    runner = CliRunner()
    _add_item(runner, wiki, "T-1")

    started = runner.invoke(
        orchestrate_cli,
        [
            "session-start", "--wiki-dir", str(wiki), "--id", "S-1",
            "--role", "backend", "--goal", "Implement task", "--scope", "src/task.py",
            "--snapshot", "abc123",
        ],
    )
    assert started.exit_code == 0, started.output
    completed = runner.invoke(
        orchestrate_cli,
        [
            "session-complete", "--wiki-dir", str(wiki), "S-1", "--status", "GREEN",
            "--result", "Implemented and verified", "--file", "src/task.py",
            "--contract", "wiki/contracts/task.md", "--test", "pytest tests/test_task.py",
            "--next-step", "Release review",
        ],
    )
    assert completed.exit_code == 0, completed.output
    session = load_entity(wiki, "session", "S-1").frontmatter
    for field in (
        "session_id", "agent_role", "goal", "scope", "snapshot", "files_changed",
        "contracts_changed", "decisions", "risks", "tests", "result", "next_steps",
    ):
        assert field in session

    handed_off = runner.invoke(
        handoff_cli,
        [
            "create", "--wiki-dir", str(wiki), "--id", "H-1", "--from-agent", "backend",
            "--to-agent", "qa", "--session", "S-1", "--context", "Implementation is ready",
            "--completed", "Code complete", "--unfinished", "Regression review",
            "--file", "src/task.py", "--contract", "wiki/contracts/task.md",
            "--risk", "Edge case needs review", "--decision", "Keep API stable",
            "--next-action", "Run regression suite",
        ],
    )
    assert handed_off.exit_code == 0, handed_off.output
    assert validate_handoffs(wiki) == []

    blocked, _, blockers, warnings = release_check_report(wiki, "0.2")
    assert blocked == "BLOCKED"
    assert any("T-1" in finding for finding in blockers)
    assert warnings == []

    done = runner.invoke(
        backlog_cli,
        [
            "update", "--wiki-dir", str(wiki), "T-1", "--status", "DONE",
            "--evidence", "pytest tests/test_task.py: PASS",
        ],
    )
    assert done.exit_code == 0, done.output
    verdict, report, blockers, warnings = release_check_report(wiki, "0.2")
    assert verdict == "GREEN"
    assert blockers == []
    assert warnings == []
    assert "Sessions: 1" in report

    label, rollup = rollup_report(wiki, period="month", today=date.today(), scope="agentops")
    assert label
    assert "[[agentops-session-s-1]]" in rollup
    assert "[[agentops-handoff-h-1]]" in rollup
    assert "[[agentops-backlog-item-t-1]]" in rollup
    output = write_rollup(wiki, period="month", today=date.today(), scope="agentops")
    assert output.parent == wiki / "agentops" / "rollups"
    assert "slug: agentops-rollup-" in output.read_text()
    assert "[[agentops-rollup-" in (wiki / "agentops" / "index.md").read_text()


def test_handoff_rejects_raw_sized_context(tmp_path: Path):
    wiki = _wiki(tmp_path)
    result = CliRunner().invoke(
        handoff_cli,
        [
            "create", "--wiki-dir", str(wiki), "--id", "raw", "--from-agent", "backend",
            "--to-agent", "qa", "--context", "x" * 4001, "--next-action", "Summarize",
        ],
    )

    assert result.exit_code != 0
    assert "summarize it" in result.output
