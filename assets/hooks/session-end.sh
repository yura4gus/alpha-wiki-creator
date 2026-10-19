#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"
run_python() {
  python3 "$PROJECT_DIR/.alpha-wiki/run.py" "$@"
}

REPORT="$(run_python -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --suggest 2>&1 || true)"
SUGGESTIONS=$(echo "$REPORT" | grep -c "^WARN" || true)
ERRORS=$(echo "$REPORT" | grep -c "^ERROR" || true)
GOVERNANCE="$(run_python -m tools.document_worker check --root . --config .alpha-wiki/config.yaml 2>&1 || true)"

run_python -m tools.wiki_engine rebuild-context-brief --wiki-dir "$WIKI_DIR" >/dev/null || true

echo "Session ended. Lint: $ERRORS error(s), $SUGGESTIONS suggestion(s)."
echo "$GOVERNANCE"
echo "Run: /alpha-wiki:lint --fix or /alpha-wiki:review"
