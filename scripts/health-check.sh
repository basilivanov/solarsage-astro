#!/bin/bash

# ############################################################################
# Health check script for production monitoring
# WAVE: W-2.7
# ############################################################################

API_URL="https://dev.astro.vasiliy-ivanov.ru/api/health/extended"
METRICS_URL="https://dev.astro.vasiliy-ivanov.ru/api/metrics"
FRONTEND_URL="https://dev.astro.vasiliy-ivanov.ru/"

echo "=== SolarSage Health Check ==="
echo "Timestamp: $(date -Iseconds)"
echo ""

# Check extended API health
echo "=== API Health Check ==="
api_response=$(curl -s "$API_URL")
api_status=$(echo "$api_response" | jq -r '.status // "unknown"')
echo "Status: $api_status"

if [ "$api_status" != "healthy" ]; then
  echo "WARNING: API is not healthy!"
  echo "$api_response" | jq '.checks'
else
  echo "All checks passed"
fi

echo ""

# Get metrics
echo "=== Production Metrics ==="
metrics_response=$(curl -s "$METRICS_URL")
if [ $? -eq 0 ]; then
  echo "$metrics_response" | jq '{
    users: .users,
    onboarding: .onboarding
  }'
else
  echo "ERROR: Failed to fetch metrics"
fi

echo ""

# Check frontend
echo "=== Frontend Check ==="
frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
echo "HTTP Status: $frontend_status"

if [ "$frontend_status" != "200" ]; then
  echo "WARNING: Frontend is not responding correctly!"
fi

echo ""

# Summary
echo "=== Summary ==="
if [ "$api_status" = "healthy" ] && [ "$frontend_status" = "200" ]; then
  echo "✓ All systems operational"
  exit 0
else
  echo "✗ Some systems are degraded"
  exit 1
fi
