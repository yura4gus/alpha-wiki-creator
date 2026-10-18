"""Run copied Alpha-Wiki tools without using the product's dependencies."""
from __future__ import annotations

import importlib
import hashlib
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    runtime = project / ".alpha-wiki" / "runtime"
    python = runtime / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    args = sys.argv[1:]
    usage = "Usage: python3 .alpha-wiki/run.py -m tools.<module> [arguments]"
    if args in ([], ["--help"], ["-h"]):
        print(usage)
        return 0
    if len(args) < 2 or args[0] != "-m" or not re.fullmatch(r"tools\.[a-z_]+", args[1]):
        print(usage, file=sys.stderr)
        return 2
    module, tool_args = args[1], args[2:]
    if not (project / "tools" / (module.split(".")[1] + ".py")).is_file():
        print(f"Alpha-Wiki tool is missing: {module}. Rerun init/upgrade.", file=sys.stderr)
        return 1

    repair = f'UV_PROJECT_ENVIRONMENT="{runtime / ".venv"}" uv sync --project "{runtime}" --no-dev'
    manifest = runtime / "pyproject.toml"
    if not manifest.is_file():
        print("Alpha-Wiki runtime manifest is missing. Rerun init/upgrade.", file=sys.stderr)
        return 1
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    marker = runtime / ".venv" / ".alpha-wiki-manifest"
    synchronized = marker.is_file() and marker.read_text() == digest
    environment = dict(os.environ)
    for key in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    environment["UV_PROJECT_ENVIRONMENT"] = str(runtime / ".venv")
    if not python.is_file() or not synchronized:
        uv = shutil.which("uv")
        if not uv:
            print(f"Alpha-Wiki runtime setup/update needs uv. Install uv, then run: {repair}", file=sys.stderr)
            return 1
        result = subprocess.run(
            [uv, "sync", "--project", str(runtime), "--no-dev"],
            env=environment,
            check=False,
        )
        if result.returncode:
            print(f"Alpha-Wiki runtime setup failed. Retry: {repair}", file=sys.stderr)
            return result.returncode
        marker.write_text(digest)
    if Path(sys.prefix).resolve() != (runtime / ".venv").resolve():
        try:
            os.execve(str(python), [str(python), str(Path(__file__).resolve()), *args], environment)
        except OSError as exc:
            print(f"Alpha-Wiki runtime could not start: {exc}. Repair: {repair}", file=sys.stderr)
            return 1

    try:
        for dependency in ("click", "yaml", "jinja2"):
            importlib.import_module(dependency)
    except ImportError as exc:
        print(f"Alpha-Wiki runtime dependency is unavailable: {exc}. Repair: {repair}", file=sys.stderr)
        return 1
    os.chdir(project)
    sys.path.insert(0, str(project))
    sys.argv = [module, *tool_args]
    runpy.run_module(module, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
