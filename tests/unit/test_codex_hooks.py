import importlib.util
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[2] / "assets" / "codex-hooks" / "alpha_wiki_hook.py"
SPEC = importlib.util.spec_from_file_location("alpha_wiki_hook", HOOK_PATH)
assert SPEC and SPEC.loader
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


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


def test_codex_hook_prefers_installed_runtime_for_dependencies(tmp_path: Path, monkeypatch):
    runtime = tmp_path / "alpha-wiki"
    runtime.mkdir()
    (runtime / "pyproject.toml").write_text("[project]\nname='alpha-wiki'\nversion='0.5.0'\n")
    monkeypatch.setenv("ALPHA_WIKI_RUNTIME", str(runtime))
    monkeypatch.setattr(HOOK.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    prefix = HOOK._python_prefix(tmp_path)

    assert prefix == ["uv", "run", "--project", str(runtime), "python"]


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
