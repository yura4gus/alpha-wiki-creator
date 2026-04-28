#!/usr/bin/env bash
set -euo pipefail
WIKI_DIR="${WIKI_DIR:-wiki}"
TARGET_FILE="${1:-}"

if [ -z "$TARGET_FILE" ]; then exit 0; fi
case "$TARGET_FILE" in
  "$WIKI_DIR"/graph/*) exit 0 ;;
esac

uv run python tools/lint.py --wiki-dir "$WIKI_DIR" --config .alpha-wiki/config.yaml --dry-run 2>&1 | head -5 || true
