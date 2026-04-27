#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
BRIEF="$WIKI_DIR/graph/context_brief.md"
if [ -f "$BRIEF" ]; then
  cat "$BRIEF"
fi
