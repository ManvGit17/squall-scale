#!/usr/bin/env bash
# Smoke test: bring the fleet up (if asked), then check the load balancer
# serves requests and exposes health and metrics through to the backends.
set -euo pipefail

BASE="${1:-http://localhost:8088}"

echo "waiting for ${BASE} ..."
ready=""
for _ in $(seq 1 45); do
  if curl -fsS "${BASE}/healthz" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [ -z "${ready}" ]; then
  echo "FAIL: ${BASE} did not become ready"
  exit 1
fi

echo "checking /healthz"
curl -fsS "${BASE}/healthz" | grep -q '^ok$'

echo "checking / (greeting)"
curl -fsS "${BASE}/" | grep -q 'Served by backend:'

echo "checking /metrics (Prometheus format)"
curl -fsS "${BASE}/metrics" | grep -q '^squallscale_requests_total '

echo "smoke OK"
