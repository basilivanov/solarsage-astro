#!/bin/bash


# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_DASHBOARD
# ROLE: Tooling script
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-GUARDRAILS-TOOLING
# #########################################// START_MODULE_CONTRACT
# purpose: Tool: dashboard
# owns:
#   - scripts/dashboard.sh
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# ############################################################################
# Simple dashboard for production monitoring
# WAVE: W-2.7
# ############################################################################

API_URL="https://dev.astro.vasiliy-ivanov.ru"

while true; do
  clear
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         SolarSage Production Dashboard                        ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "HEALTH STATUS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  health_response=$(curl -s "$API_URL/api/health/extended" 2>/dev/null)
  if [ $? -eq 0 ]; then
    status=$(echo "$health_response" | jq -r '.status // "unknown"')

    if [ "$status" = "healthy" ]; then
      echo "✓ Status: HEALTHY"
    else
      echo "✗ Status: DEGRADED"
    fi

    echo ""
    echo "$health_response" | jq -r '.checks | to_entries | .[] | "  \(.key): \(.value)"'
  else
    echo "✗ ERROR: Cannot reach API"
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "METRICS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  metrics_response=$(curl -s "$API_URL/api/metrics" 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "$metrics_response" | jq -r '
      "Users:",
      "  Total: \(.users.total)",
      "  New (24h): \(.users.new_24h)",
      "  New (7d): \(.users.new_7d)",
      "",
      "Onboarding:",
      "  Completed: \(.onboarding.completed)",
      "  Completed (24h): \(.onboarding.completed_24h)",
      "  Completed (7d): \(.onboarding.completed_7d)",
      "  Rate: \(.onboarding.rate)%"
    '
  else
    echo "✗ ERROR: Cannot fetch metrics"
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "SYSTEM"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  echo "Processes:"
  ps aux | grep -E "uvicorn|node.*next" | grep -v grep | awk '{printf "  PID %s: %s %s %s\n", $2, $11, $12, $13}'

  echo ""
  echo "Disk Usage:"
  df -h /opt/solarsage-astro 2>/dev/null | tail -1 | awk '{printf "  %s used of %s (%s)\n", $3, $2, $5}'

  echo ""
  echo "Memory:"
  free -h | grep Mem | awk '{printf "  %s used of %s\n", $3, $2}'

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Press Ctrl+C to exit | Refreshing every 5 seconds..."

  sleep 5
done
