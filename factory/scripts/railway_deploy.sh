#!/usr/bin/env bash
# Deploy the factory control plane to an existing Railway project/environment.
#
# Required:
#   RAILWAY_PROJECT_ID
#   RAILWAY_ENVIRONMENT_ID
# Optional (defaults shown):
#   RAILWAY_RUNTIME_SERVICE=agent-factory-runtime
#   RAILWAY_HARNESS_SERVICE=agent-factory-harness
#
# This script only uploads the image and starts deployments. Service settings
# (Dockerfile path, start command, region, volume, health check) and secrets are
# one-time operator setup; see factory/RAILWAY.md. It never prints variables.
set -Eeuo pipefail

: "${RAILWAY_PROJECT_ID:?set RAILWAY_PROJECT_ID}"
: "${RAILWAY_ENVIRONMENT_ID:?set RAILWAY_ENVIRONMENT_ID}"
RUNTIME="${RAILWAY_RUNTIME_SERVICE:-agent-factory-runtime}"
HARNESS="${RAILWAY_HARNESS_SERVICE:-agent-factory-harness}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

railway whoami >/dev/null

for service in "$RUNTIME" "$HARNESS"; do
  echo "deploying ${service} from ${ROOT}"
  railway up \
    -p "$RAILWAY_PROJECT_ID" \
    -e "$RAILWAY_ENVIRONMENT_ID" \
    -s "$service" \
    --detach --yes
done

echo "deployments started; verify pollers and the private console as documented in factory/RAILWAY.md"
