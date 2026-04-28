#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"

uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix
RESULT=$?
if [ $RESULT -eq 0 ]; then
  git add "$WIKI_DIR"
  exit 0
fi
echo "Lint errors remain after --fix. Resolve before committing."
exit 1
