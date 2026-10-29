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
TARGET_FILE="${TARGET_FILE#"$PROJECT_DIR"/}"
if [ -z "$TARGET_FILE" ]; then exit 0; fi
case "$TARGET_FILE" in
  "$WIKI_DIR"/graph/*) exit 0 ;;
  "$WIKI_DIR"/*) ;;
  *) exit 0 ;;
esac

python3 "$PROJECT_DIR/.alpha-wiki/run.py" -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --dry-run 2>&1 | head -5 || true
