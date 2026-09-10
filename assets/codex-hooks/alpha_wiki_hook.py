#!/usr/bin/env python3
"""Small Codex hook adapter for an initialized Alpha-Wiki project."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _read_payload() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}


def _project_root(payload: dict[str, Any]) -> Path:
    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else cwd


def _tool_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload.get("tool_input", {}), ensure_ascii=True)


def _touches_wiki(payload: dict[str, Any], wiki_dir: str) -> bool:
    normalized = _tool_text(payload).replace("\\\\", "/")
    token = wiki_dir.strip("/") + "/"
    return re.search(re.escape(token) + r"(?!graph/)", normalized) is not None


def _touches_generated_graph(payload: dict[str, Any], wiki_dir: str) -> bool:
    normalized = _tool_text(payload).replace("\\\\", "/")
    return f"{wiki_dir.strip('/')}/graph/" in normalized


def _python_prefix(project: Path) -> list[str]:
    runtime = Path(os.environ.get("ALPHA_WIKI_RUNTIME", Path.home() / "plugins" / "alpha-wiki")).expanduser()
    if shutil.which("uv") and (runtime / "pyproject.toml").exists():
        return ["uv", "run", "--project", str(runtime), "python"]
    if shutil.which("uv"):
        return ["uv", "run", "python"]
    venv_python = project / ".venv" / "bin" / "python"
    if venv_python.exists():
        return [str(venv_python)]
    return [sys.executable]


def _run(project: Path, args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_python_prefix(project), *args],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _emit(message: str) -> None:
    print(json.dumps({"systemMessage": message}, ensure_ascii=True))


def _session_start(project: Path, wiki_dir: str) -> None:
    brief = project / wiki_dir / "graph" / "context_brief.md"
    if brief.exists():
        _emit("Alpha-Wiki context brief:\n\n" + brief.read_text()[:8000])
    else:
        _emit("Alpha-Wiki context brief is missing. Run $alpha-wiki:doctor with refresh.")


def _subagent_context(project: Path, wiki_dir: str) -> str:
    lines = [
        "Alpha-Wiki native subagent contract:",
        "- Read applicable AGENTS.md files before analysis.",
        f"- Read {wiki_dir}/graph/context_brief.md and relevant source pages.",
        "- Use the controller's pinned repository snapshot; verify dirty worktrees with tools.worktree_snapshot and do not refresh shared refs independently.",
        "- Treat runtime at the pinned SHA as implementation evidence and accepted contracts as intended behavior.",
        "- Keep raw/** read-only and never hand-edit generated graph artifacts.",
        "- Stay inside the assigned scope, do not create nested subagents, and do not expose secrets.",
        "- Return concise evidence, inference, unknowns, owner decisions, and a terminal status.",
    ]
    brief = project / wiki_dir / "graph" / "context_brief.md"
    if brief.exists():
        lines.extend(["", "Alpha-Wiki context brief:", "", brief.read_text()[:4000]])
    else:
        lines.append(f"- {wiki_dir}/graph/context_brief.md is missing; report UNPROVEN where context is required.")
    return "\n".join(lines)


def _subagent_start(project: Path, wiki_dir: str) -> None:
    # SubagentStart treats plain stdout as additional developer context.
    print(_subagent_context(project, wiki_dir))


def _pre_tool(payload: dict[str, Any], wiki_dir: str) -> None:
    if _touches_generated_graph(payload, wiki_dir):
        _emit(f"{wiki_dir}/graph is generated. Change source wiki pages and rebuild instead of hand-editing graph artifacts.")


def _post_tool(project: Path, payload: dict[str, Any], wiki_dir: str) -> None:
    if not _touches_wiki(payload, wiki_dir):
        return
    commands = [
        ["-m", "tools.wiki_engine", "rebuild-edges", "--wiki-dir", wiki_dir],
        ["-m", "tools.wiki_engine", "rebuild-context-brief", "--wiki-dir", wiki_dir],
        ["-m", "tools.wiki_engine", "rebuild-open-questions", "--wiki-dir", wiki_dir],
    ]
    failures = []
    for command in commands:
        result = _run(project, command, timeout=8)
        if result.returncode:
            failures.append(result.stderr.strip() or result.stdout.strip() or "unknown error")
    if failures:
        _emit("Alpha-Wiki graph refresh failed: " + "; ".join(failures[:2]))


def _session_end(project: Path, wiki_dir: str) -> None:
    wiki = project / wiki_dir
    if not wiki.exists():
        return
    try:
        result = _run(
            project,
            ["-m", "tools.lint", "--wiki-dir", wiki_dir, "--config", ".alpha-wiki/config.yaml", "--suggest"],
            timeout=2,
        )
        errors = result.stdout.count("ERROR")
        warnings = result.stdout.count("WARN")
        log = wiki / "log.md"
        if log.exists():
            with log.open("a") as stream:
                stream.write(f"\n## [{date.today().isoformat()}] session-end | codex lint errors={errors} warnings={warnings}\n")
    except (subprocess.TimeoutExpired, OSError):
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "event",
        choices=["session-start", "subagent-start", "pre-tool", "post-tool", "session-end"],
    )
    parser.add_argument("--wiki-dir", default="wiki")
    args = parser.parse_args()
    payload = _read_payload()
    project = _project_root(payload)

    if args.event == "session-start":
        _session_start(project, args.wiki_dir)
    elif args.event == "subagent-start":
        _subagent_start(project, args.wiki_dir)
    elif args.event == "pre-tool":
        _pre_tool(payload, args.wiki_dir)
    elif args.event == "post-tool":
        _post_tool(project, payload, args.wiki_dir)
    else:
        _session_end(project, args.wiki_dir)


if __name__ == "__main__":
    main()
