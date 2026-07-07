#!/usr/bin/env bash
set -e
ARTIFACTS_DIR="docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-02"
SCRIPT_PATH="scripts/generate-telegram-test-initdata.py"
mkdir -p "$ARTIFACTS_DIR"
RESULTS_JSON="$ARTIFACTS_DIR/capture-results.json"
STDOUT_FILE="$ARTIFACTS_DIR/capture-stdout.txt"
echo "[" > "$RESULTS_JSON"
first=true

capture() {
  local label=$1 route=$2 name=$3 sentinel_text=$4 sentinel_testid=$5 sentinel_alt=$6
  local full_url="http://127.0.0.1:${label}${route}"
  local png_path="$ARTIFACTS_DIR/${label}-${name}.png"
  local txt_path="$ARTIFACTS_DIR/${label}-${name}.txt"
  local result="{\"label\":\"${label}\",\"route\":\"${route}\",\"finalUrl\":\"${full_url}\",\"valid\":false,\"artifact\":null,\"blocker\":null,\"sentinels\":{}}"

  echo "--- ${label}${route} ---"

  if [ "$label" = "3002" ]; then
    # Get auth session cookie
    INIT_DATA=$(python3 "$SCRIPT_PATH" 2>/dev/null | grep -v "^#" | grep -v "tgWebAppData" | grep "=" | head -1)
    if [ -n "$INIT_DATA" ]; then
      COOKIE=$(curl -s -X POST "http://127.0.0.1:8000/api/auth/telegram" \
        -H "Content-Type: application/json" \
        -d "{\"initData\":\"${INIT_DATA}\"}" \
        -c - 2>/dev/null | grep grace_session_v2 | awk "{print \$NF}")
    fi
  fi

  # Take screenshot with playwright CLI
  npx playwright screenshot --viewport-size="430,932" "${full_url}" "${png_path}" 2>/dev/null || true

  # Use python3 to check the page content via curl for sentinels
  PAGE_HTML=$(curl -s -L -b "grace_session_v2=${COOKIE}" "${full_url}" 2>/dev/null || echo "")

  # Check auth blockers
  local auth_loading=false; local auth_error=false; local auth_text=false; local sentinel_ok=false
  if echo "$PAGE_HTML" | grep -q "auth-loading"; then auth_loading=true; fi
  if echo "$PAGE_HTML" | grep -q "auth-error"; then auth_error=true; fi
  if echo "$PAGE_HTML" | grep -q "Авторизация"; then auth_text=true; fi

  # Check sentinel
  if [ -n "$sentinel_testid" ]; then
    if echo "$PAGE_HTML" | grep -q "data-testid=\"${sentinel_testid}\""; then sentinel_ok=true; fi
  fi
  if [ "$sentinel_ok" = false ] && [ -n "$sentinel_text" ]; then
    if echo "$PAGE_HTML" | grep -q "${sentinel_text}"; then sentinel_ok=true; fi
  fi
  if [ "$sentinel_ok" = false ] && [ -n "$sentinel_alt" ]; then
    if echo "$PAGE_HTML" | grep -q "${sentinel_alt}"; then sentinel_ok=true; fi
  fi

  echo "  authL=$auth_loading authE=$auth_error authT=$auth_text sentinel=$sentinel_ok"

  local valid=false; local blocker="null"
  if [ "$auth_loading" = false ] && [ "$auth_error" = false ] && [ "$auth_text" = false ] && [ "$sentinel_ok" = true ]; then
    valid=true
    echo "  ✅ VALID: ${label}${route}"
  else
    local reasons=""
    if [ "$auth_loading" = true ] || [ "$auth_error" = true ] || [ "$auth_text" = true ]; then reasons="auth_blocked"; fi
    if [ "$sentinel_ok" = false ]; then
      if [ -n "$reasons" ]; then reasons="${reasons},no_sentinel"; else reasons="no_sentinel"; fi
    fi
    blocker="\"${reasons}\""
    echo "$reasons" > "$txt_path"
    echo "  ❌ BLOCKED: $reasons"
  fi

  local comma=""
  if [ "$first" = false ]; then comma=","; fi
  first=false
  echo "${comma}{\"label\":\"${label}\",\"route\":\"${route}\",\"finalUrl\":\"${full_url}\",\"valid\":${valid},\"artifact\":\"${label}-${name}.png\",\"blocker\":${blocker},\"sentinels\":{\"authLoadingVisible\":${auth_loading},\"authErrorVisible\":${auth_error},\"authTextVisible\":${auth_text},\"routeSentinelVisible\":${sentinel_ok}}}" >> "$RESULTS_JSON"
}

cd /opt/solarsage-astro

# 3001 routes (no auth)
capture 3001 "/day/2026-07-05" "day-2026-07-05" "" "today-screen" "Конкретно сегодня"
capture 3001 "/calendar" "calendar" "" "" "Календарь"
capture 3001 "/profile" "profile" "" "" "Профиль"
capture 3001 "/readings" "readings" "" "" "Разборы"
capture 3001 "/readings/horary" "horary" "" "" "Хорарный оракул"
capture 3001 "/readings/natal" "natal" "" "" "Разбор по точным данным рождения"

# 3002 routes (with auth via cookie)
capture 3002 "/day/2026-07-05" "day-2026-07-05" "" "today-screen" ""
capture 3002 "/calendar" "calendar" "" "calendar-screen" ""
capture 3002 "/profile" "profile" "" "profile-screen" ""
capture 3002 "/readings" "readings" "" "readings-screen" ""
capture 3002 "/readings/horary" "horary" "" "horary-screen" ""
capture 3002 "/readings/natal" "natal" "" "natal-preview-screen" ""

echo "]" >> "$RESULTS_JSON"
# Remove trailing comma and final bracket
sed -i $
