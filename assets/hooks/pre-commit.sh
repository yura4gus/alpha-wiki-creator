#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="$(git rev-parse --show-toplevel)"
cd "$PROJECT_DIR"

if ! python3 "$PROJECT_DIR/.alpha-wiki/run.py" -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix; then
  echo "Lint errors remain after --fix. Resolve before committing."
  exit 1
fi
git add "$WIKI_DIR"
