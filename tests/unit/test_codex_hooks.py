import importlib.util
import json
import subprocess
import sys
import shutil
from pathlib import Path

import pytest


HOOK_PATH = Path(__file__).resolve().parents[2] / "assets" / "codex-hooks" / "alpha_wiki_hook.py"
SPEC = importlib.util.spec_from_file_location("alpha_wiki_hook", HOOK_PATH)
assert SPEC and SPEC.loader
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


@pytest.mark.parametrize("command", ["cat wiki/index.md", "rg title wiki/", "git diff -- wiki/index.md", "sed -n '1,10p' wiki/index.md"])
def test_read_only_wiki_calls_do_not_refresh(command):
    assert not HOOK._touches_wiki({"tool_name": "Bash", "tool_input": {"command": command}}, "wiki")


@pytest.mark.parametrize("command", ["cat source.md > wiki/index.md", "cat wiki/index.md; touch wiki/new.md", "sed -i '' s/old/new/ wiki/index.md"])
def test_wiki_shell_writes_still_refresh(command):
    assert HOOK._touches_wiki({"tool_name": "Bash", "tool_input": {"command": command}}, "wiki")


@pytest.mark.parametrize("event", ["session-start", "subagent-start", "pre-tool", "post-tool", "session-end"])
@pytest.mark.parametrize("payload", ["{broken", "[]", '{"cwd":"/missing-worktree","tool_input":{"command":"pwd"}}'])
@pytest.mark.parametrize("interpreter", ["python3", "/usr/bin/python3"])
def test_all_events_run_with_path_python_without_product_dependencies(tmp_path: Path, event, payload, interpreter):
    python = shutil.which(interpreter)
    if not python:
        pytest.skip(f"{interpreter} is unavailable")
    hook = tmp_path / ".codex/hooks/alpha_wiki_hook.py"
    hook.parent.mkdir(parents=True)
    shutil.copyfile(HOOK_PATH, hook)
    # No wiki or runtime: startup reports missing context, tool events do no work.
    result = subprocess.run([python, str(hook), event], input=payload,
                            cwd=tmp_path, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert "hook skipped" not in result.stdout


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("runtime", 1), OSError("runtime missing")])
def test_runtime_launch_errors_are_reported_without_crashing(tmp_path, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(HOOK.subprocess, "run", fail)
    result = HOOK._run(tmp_path, ["-m", "tools.lint"], timeout=1)
    assert result.returncode in {124, 127}
    assert result.stderr


def test_codex_hook_detects_source_wiki_write():
    payload = {
        "tool_input": {
            "patch": "*** Begin Patch\n*** Update File: wiki/modules/payments.md\n"
        }
    }

    assert HOOK._touches_wiki(payload, "wiki")
    assert not HOOK._touches_generated_graph(payload, "wiki")


def test_codex_hook_does_not_rebuild_for_graph_only_write():
    payload = {
        "tool_input": {
            "patch": "*** Begin Patch\n*** Update File: wiki/graph/edges.jsonl\n"
        }
    }

    assert not HOOK._touches_wiki(payload, "wiki")
    assert HOOK._touches_generated_graph(payload, "wiki")


def test_codex_hook_keeps_source_detection_when_patch_also_mentions_graph():
    payload = {
        "tool_input": {
            "patch": (
                "*** Update File: wiki/modules/payments.md\n"
                "*** Update File: wiki/graph/context_brief.md\n"
            )
        }
    }

    assert HOOK._touches_wiki(payload, "wiki")
    assert HOOK._touches_generated_graph(payload, "wiki")


def test_codex_hook_uses_project_isolated_launcher(tmp_path: Path, monkeypatch):
    runtime = tmp_path / "alpha-wiki"
    runtime.mkdir()
    (runtime / "pyproject.toml").write_text("[project]\nname='alpha-wiki'\nversion='0.5.0'\n")
    monkeypatch.setenv("ALPHA_WIKI_RUNTIME", str(runtime))
    monkeypatch.setattr(HOOK.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    prefix = HOOK._python_prefix(tmp_path)

    assert prefix == [sys.executable, str(tmp_path / ".alpha-wiki" / "run.py")]


def test_subagent_context_is_bounded_and_evidence_first(tmp_path: Path):
    brief = tmp_path / "wiki" / "graph" / "context_brief.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# Context\n\nCurrent project memory.\n" + ("x" * 10_000) + "\nUNBOUNDED_TAIL\n")

    context = HOOK._subagent_context(tmp_path, "wiki")

    assert "Alpha-Wiki native subagent contract" in context
    assert "pinned repository snapshot" in context
    assert "tools.worktree_snapshot" in context
    assert "do not refresh shared refs independently" in context
    assert "do not create nested subagents" in context
    assert "Current project memory" in context
    assert len(context) <= 6000
    assert "UNBOUNDED_TAIL" not in context


def test_codex_hook_template_registers_subagent_start():
    template = (HOOK_PATH.parent / "hooks.json.j2").read_text()

    assert '"SubagentStart"' in template
    assert "subagent-start --wiki-dir" in template


def test_codex_hook_survives_stale_session_cwd():
    payload = {
        "cwd": "/alpha-wiki/removed-worktree",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git status --short"},
    }

    result = subprocess.run(
        [sys.executable, str(HOOK_PATH), "pre-tool", "--wiki-dir", "wiki"],
        cwd=HOOK_PATH.parents[2],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert result.returncode == 0, result.stderr


def test_session_end_checks_governance_without_polluting_log(tmp_path: Path, monkeypatch):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    log = wiki / "log.md"
    log.write_text("# Log\n")
    calls: list[list[str]] = []

    def fake_run(project: Path, args: list[str], timeout: float):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "PASS\n", "")

    monkeypatch.setattr(HOOK, "_run", fake_run)

    HOOK._session_end(tmp_path, "wiki")

    assert log.read_text() == "# Log\n"
    assert any("tools.document_worker" in args for args in calls)
