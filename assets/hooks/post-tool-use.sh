#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

if ! python3 -c '
import json
from pathlib import Path
import sys

wiki = Path(sys.argv[1]).resolve()
try:
    data = json.load(sys.stdin)
    cwd = Path(data.get("cwd") or ".")
    if not cwd.is_dir():
        cwd = Path.cwd()
    target = (cwd / data["tool_input"]["file_path"]).resolve().relative_to(wiki)
except (KeyError, OSError, TypeError, ValueError):
    sys.exit(1)

sys.exit(not target.parts or target.parts[0] in {"graph", "render", "outputs"}
         or target.suffix != ".md")
' "$WIKI_DIR"; then
  exit 0
fi

if ! python3 "$PROJECT_DIR/.alpha-wiki/run.py" -m tools.wiki_engine rebuild-graph \
    --wiki-dir "$WIKI_DIR" >/dev/null; then
  echo "Alpha-Wiki graph refresh failed. Run /alpha-wiki:doctor --refresh." >&2
  exit 1
fi
