#!/usr/bin/env bash
# One container, two Temporal workers: the factory executor (`factory-code`)
# and the harness coordinator (`factory-coordinator`). They share /data so the
# coordinator can read the receipts the executor writes.
#
# If either process exits, the whole container exits non-zero so Railway's
# ALWAYS restart policy recreates both pollers together.
set -Eeuo pipefail

umask 077
# Materialise secrets here as well: Railway may bypass the image ENTRYPOINT and
# exec this script as the start command. The function is idempotent.
# shellcheck source=/dev/null
. /usr/local/bin/factory-lib.sh
materialize_secrets

pids=()

shutdown() {
  local code="${1:-$?}"
  trap - TERM INT
  for pid in "${pids[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  exit "$code"
}
trap 'shutdown $?' TERM INT

python -m agent_factory.worker &
pids+=("$!")

python -m agent_factory.harness.worker &
pids+=("$!")

# Wait for the first child to exit, then stop its sibling and fail the
# container. `wait -n` is available in bash 5 (bookworm).
set +e
wait -n "${pids[@]}"
status=$?
set -e
echo "factory runtime: a worker exited (status ${status}); stopping the container" >&2
shutdown "$status"
