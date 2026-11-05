#!/usr/bin/env bash
# Tear down the platform, including backends the controller spawned (which
# are not part of the Compose project).
set -euo pipefail

docker compose down -v

spawned="$(docker ps -aq --filter label=squallscale.role=backend || true)"
if [ -n "${spawned}" ]; then
  echo "removing spawned backends"
  docker rm -f ${spawned} >/dev/null
fi
echo "down"
