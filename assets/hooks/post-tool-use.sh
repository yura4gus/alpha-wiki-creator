#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

INPUT="$(cat || true)"
TARGET_FILE="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try:
    data=json.load(sys.stdin)
    print(data.get("tool_input", {}).get("file_path", ""))
except Exception:
    print("")
' 2>/dev/null || true)"
case "$TARGET_FILE" in
  "$WIKI_DIR"/*) ;;
  *) exit 0 ;;
esac

LOCK="$WIKI_DIR/graph/.rebuild.lock"
NOW=$(date +%s)

run_python() {
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
  elif [ -x ".venv/bin/python" ]; then
    .venv/bin/python "$@"
  else
    python3 "$@"
  fi
}

if [ -f "$LOCK" ]; then
  LAST=$(cat "$LOCK")
  if [ $((NOW - LAST)) -lt 5 ]; then exit 0; fi
fi
echo "$NOW" > "$LOCK"
(
  run_python -m tools.wiki_engine rebuild-edges --wiki-dir "$WIKI_DIR" >/dev/null
  run_python -m tools.wiki_engine rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null
  run_python -m tools.wiki_engine rebuild-open-questions --wiki-dir "$WIKI_DIR" >/dev/null
) &
