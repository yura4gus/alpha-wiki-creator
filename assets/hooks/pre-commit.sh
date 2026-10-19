#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
PROJECT_DIR="$(git rev-parse --show-toplevel)"
cd "$PROJECT_DIR"

run_python() {
  python3 "$PROJECT_DIR/.alpha-wiki/run.py" "$@"
}

if ! run_python -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix; then
  echo "Lint errors remain after --fix. Resolve before committing."
  exit 1
fi

git add "$WIKI_DIR"
run_python -m tools.document_worker check \
  --root . --config .alpha-wiki/config.yaml --staged
