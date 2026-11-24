#!/usr/bin/env bash
# Shared boot-time secret materialisation. Sourced by the image entrypoint and
# by the runtime supervisor so a platform that overrides ENTRYPOINT still gets
# the OpenCode auth store.
#
# Values arrive as service variables, are written 0600, and are removed from
# the environment before long-running workers start.
set -Eeuo pipefail

materialize_secrets() {
  : "${HOME:=/tmp/home}"
  export HOME
  mkdir -p "$HOME"

  if [[ -n "${OPENCODE_AUTH_EXPORT_B64:-}" ]]; then
    # OpenCode 2 stores integrations in its local database, not auth.json.
    # `auth export` is the supported way to move them between machines.
    local auth_dir="${XDG_DATA_HOME:-$HOME/.local/share}/opencode"
    local export_file
    mkdir -p "$auth_dir"
    export_file="$(mktemp "$HOME/.opencode-auth.XXXXXX")"
    printf '%s' "$OPENCODE_AUTH_EXPORT_B64" | base64 --decode > "$export_file"
    chmod 600 "$export_file"
    opencode auth import --standalone "$export_file"
    rm -f "$export_file"
    unset OPENCODE_AUTH_EXPORT_B64
  fi

  if [[ -n "${GIT_CREDENTIALS_B64:-}" ]]; then
    printf '%s' "$GIT_CREDENTIALS_B64" | base64 --decode > "$HOME/.git-credentials"
    chmod 600 "$HOME/.git-credentials"
    git config --global credential.helper store
    unset GIT_CREDENTIALS_B64
  fi

  git config --global user.name "${GIT_AUTHOR_NAME:-Alpha-Wiki Agent Factory}"
  git config --global user.email "${GIT_AUTHOR_EMAIL:-agent-factory@localhost}"
  git config --global --add safe.directory '*'
}
