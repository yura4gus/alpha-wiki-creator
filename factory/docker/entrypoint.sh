#!/usr/bin/env bash
# Docker entrypoint for platforms that honour ENTRYPOINT. Railway may run the
# configured start command directly, so factory-runtime sources the same
# library before starting workers.
set -Eeuo pipefail

umask 077
# shellcheck source=/dev/null
. /usr/local/bin/factory-lib.sh
materialize_secrets

exec "$@"
