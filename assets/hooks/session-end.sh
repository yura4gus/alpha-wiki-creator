#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
DATE="$(date -u +%Y-%m-%d)"

REPORT="$(uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --suggest 2>&1 || true)"
SUGGESTIONS=$(echo "$REPORT" | grep -c "^🟡" || true)
ERRORS=$(echo "$REPORT" | grep -c "^🔴" || true)

echo "## [$DATE] session-end | suggestions=$SUGGESTIONS errors=$ERRORS" >> "$WIKI_DIR/log.md"

uv run python tools/wiki_engine.py rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null

echo "Session ended. Lint: $ERRORS error(s), $SUGGESTIONS suggestion(s)."
echo "Run: /wiki-lint --fix or /wiki-review"
