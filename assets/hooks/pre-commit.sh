#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"

if command -v uv >/dev/null 2>&1; then
  uv run python -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix
elif [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix
else
  python3 -m tools.lint --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --fix
fi
RESULT=$?
if [ $RESULT -eq 0 ]; then
  git add "$WIKI_DIR"
  exit 0
fi
echo "Lint errors remain after --fix. Resolve before committing."
exit 1
