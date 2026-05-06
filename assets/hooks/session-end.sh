#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"
DATE="$(date -u +%Y-%m-%d)"

run_python() {
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
  elif [ -x ".venv/bin/python" ]; then
    .venv/bin/python "$@"
  else
    python3 "$@"
  fi
}

REPORT="$(run_python -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --suggest 2>&1 || true)"
SUGGESTIONS=$(echo "$REPORT" | grep -c "^WARN" || true)
ERRORS=$(echo "$REPORT" | grep -c "^ERROR" || true)

echo "## [$DATE] session-end | suggestions=$SUGGESTIONS errors=$ERRORS" >> "$WIKI_DIR/log.md"

run_python -m tools.wiki_engine rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null

echo "Session ended. Lint: $ERRORS error(s), $SUGGESTIONS suggestion(s)."
echo "Run: /alpha-wiki:lint --fix or /alpha-wiki:review"
