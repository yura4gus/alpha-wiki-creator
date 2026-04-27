#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
LOCK="$WIKI_DIR/graph/.rebuild.lock"
NOW=$(date +%s)

if [ -f "$LOCK" ]; then
  LAST=$(cat "$LOCK")
  if [ $((NOW - LAST)) -lt 5 ]; then exit 0; fi
fi
echo "$NOW" > "$LOCK"
uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null &
