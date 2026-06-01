#!/bin/bash

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
