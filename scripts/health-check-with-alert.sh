#!/bin/bash


# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_HEALTH_CHECK_WITH_ALERT
# ROLE: Shell script for operations automation
# DEPENDENCIES: bash, standard utils
# GRACE_ANCHORS: [SCRIPT]
# SLICE: SLICE-GUARDRAILS-TOOLING
# ############################################################################
# START_MODULE_CONTRACT
# purpose: Tool: health-check-with-alert
# owns:
#   - scripts/health-check-with-alert.sh
# inputs: CLI arguments, environment variables
# outputs: exit codes, stdout, stderr
# dependencies: bash, standard CLI utils
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: exit 1 on error
# END_MODULE_CONTRACT
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
