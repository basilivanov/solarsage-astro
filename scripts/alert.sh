#!/bin/bash


# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_ALERT
# ROLE: Send alert message to Telegram via bot API.
# DEPENDENCIES: bash, curl, env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
# GRACE_ANCHORS: [SEND_ALERT]
# SLICE: SLICE-GUARDRAILS-TOOLING
# ############################################################################
# START_MODULE_CONTRACT: M-SCRIPTS-ALERT
# purpose: Send an alert message to a configured Telegram chat via bot API.
# owns:
#   - scripts/alert.sh
# inputs:
#   - $1: MESSAGE (string) — alert text to send
#   - env: TELEGRAM_BOT_TOKEN — bot token
#   - env: TELEGRAM_CHAT_ID — target chat ID
# outputs:
#   - stdout: "Alert sent successfully" on success
#   - stderr: "ERROR:..." on failure
# dependencies:
#   - bash
#   - curl
# side_effects:
#   - HTTP POST to api.telegram.org/bot{token}/sendMessage
#   - reads env vars TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# invariants:
#   - exits 1 if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty
#   - exits 1 if MESSAGE argument is empty
#   - exits 1 if curl fails
# failure_policy:
#   - exits 1 with error message to stderr on missing config
#   - exits 1 with error message on curl failure
# END_MODULE_CONTRACT: M-SCRIPTS-ALERT
# ############################################################################
# WAVE: W-2.7
# ############################################################################

# Configuration (set these environment variables or edit here)
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

MESSAGE="$1"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set"
  echo "Usage: export TELEGRAM_BOT_TOKEN=your_token"
  echo "       export TELEGRAM_CHAT_ID=your_chat_id"
  echo "       $0 'Your message'"
  exit 1
fi

if [ -z "$MESSAGE" ]; then
  echo "ERROR: Message is required"
  echo "Usage: $0 'Your message'"
  exit 1
fi

# Send message to Telegram
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID" \
  -d "text=$MESSAGE" \
  -d "parse_mode=HTML" > /dev/null

if [ $? -eq 0 ]; then
  echo "Alert sent successfully"
else
  echo "ERROR: Failed to send alert"
  exit 1
fi
