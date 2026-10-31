#!/usr/bin/env bash
set -euo pipefail

# MiniPay Repeatable Health & Availability Check
API_URL="${MINIPAY_API_URL:-http://localhost:8080}"
HEALTH_ENDPOINT="${API_URL}/health"
LIVE_ENDPOINT="${API_URL}/health/live"

echo "=== MiniPay System Health Check ==="
echo "Target Base URL: ${API_URL}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "-----------------------------------"

# 1. Check Liveness
echo -n "1. Checking API process liveness (/health/live)... "
HTTP_LIVE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "${LIVE_ENDPOINT}" || echo "000")
if [ "$HTTP_LIVE" = "200" ]; then
  echo "OK (HTTP 200)"
else
  echo "FAILED (HTTP ${HTTP_LIVE})"
  exit 1
fi

# 2. Check Database Connectivity
echo -n "2. Checking database connectivity (/health)... "
RESP_BODY=$(curl -s --max-time 5 "${HEALTH_ENDPOINT}" || true)
if [[ "$RESP_BODY" =~ \"database\":\"up\" ]]; then
  echo "OK (Database UP)"
else
  echo "FAILED - Response: ${RESP_BODY}"
  exit 2
fi

# 3. Check Container Status
echo "3. Container runtime status:"
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker compose check skipped or not running locally."

echo "-----------------------------------"
echo "ALL HEALTH CHECKS PASSED"
exit 0