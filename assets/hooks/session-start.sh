#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"
BRIEF="$WIKI_DIR/graph/context_brief.md"
if [ -f "$BRIEF" ]; then
  cat "$BRIEF"
fi
