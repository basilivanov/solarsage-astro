#!/bin/bash


// ############################################################################
// AI_HEADER: MODULE_SCRIPTS_HEALTH_CHECK_WITH_ALERT
// ROLE: Tooling script
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-GUARDRAILS-TOOLING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Tooling script — scripts/health-check-with-alert.sh
// owns:
//   - scripts/health-check-with-alert.sh
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

# ############################################################################
# Health check with alerting
# WAVE: W-2.7
# ############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_CHECK="$SCRIPT_DIR/health-check.sh"
ALERT_SCRIPT="$SCRIPT_DIR/alert.sh"

# Run health check
$HEALTH_CHECK

# Check exit code
if [ $? -ne 0 ]; then
  # Health check failed, send alert if configured
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    $ALERT_SCRIPT "⚠️ SolarSage Health Check Failed

Timestamp: $(date -Iseconds)
Environment: dev.astro.vasiliy-ivanov.ru

Please check the logs for details."
  fi
fi
