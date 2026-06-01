#!/bin/bash

# ############################################################################
# Alert script - sends message to Telegram
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
