#!/usr/bin/env bash
set -euo pipefail
HOOK_SRC=".claude/hooks"

for HOOK in pre-commit post-commit; do
  if [ -f "$HOOK_SRC/${HOOK}.sh" ]; then
    cp "$HOOK_SRC/${HOOK}.sh" ".git/hooks/$HOOK"
    chmod +x ".git/hooks/$HOOK"
    echo "installed: .git/hooks/$HOOK"
  fi
done
