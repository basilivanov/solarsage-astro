#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3001}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

fetch() {
  local url="$1"
  local output="$2"
  local status
  status="$(curl -fsS -L -o "$output" -w '%{http_code}' "$url")" || fail "request failed: $url"
  [[ "$status" == "200" ]] || fail "expected 200 from $url, got $status"
}

assert_app_html() {
  local path="$1"
  local output="$2"
  local url="${BASE_URL}${path}"

  fetch "$url" "$output"

  grep -qi '<!DOCTYPE html' "$output" || fail "$path did not return HTML"
  grep -q '/_next/static/' "$output" || fail "$path HTML does not reference Next static assets"
  if grep -Eqi 'mock-preview|demo[[:space:]_-]*api|NEXT_PUBLIC_DEMO_MODE' "$output"; then
    fail "$path HTML contains mock/demo runtime markers"
  fi

  echo "OK app HTML: $path"
}

check_static_assets() {
  local html_files=("$@")
  local assets_file="$TMP_DIR/assets.txt"
  : > "$assets_file"

  python3 - "$BASE_URL" "${html_files[@]}" > "$assets_file" <<'PY'
import html.parser
import sys
from urllib.parse import urljoin, urlparse

base_url = sys.argv[1]
html_files = sys.argv[2:]
assets = set()

class AssetParser(html.parser.HTMLParser):
    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        for key in ("src", "href"):
            value = attr_map.get(key)
            if not value:
                continue
            absolute = urljoin(base_url, value)
            parsed = urlparse(absolute)
            if parsed.path.startswith("/_next/static/"):
                assets.add(absolute)

for path in html_files:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        AssetParser().feed(handle.read())

for asset in sorted(assets):
    print(asset)
PY

  [[ -s "$assets_file" ]] || fail "no /_next/static assets found"

  while IFS= read -r asset_url; do
    local status
    status="$(curl -fsS -L -o /dev/null -w '%{http_code}' "$asset_url")" || fail "static asset request failed: $asset_url"
    [[ "$status" == "200" ]] || fail "expected 200 from static asset $asset_url, got $status"
    echo "OK static asset: $asset_url"
  done < "$assets_file"
}

check_api_health() {
  local output="$TMP_DIR/api-health.json"
  local url="${BASE_URL}/api/health"

  fetch "$url" "$output"

  python3 - "$output" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    body = handle.read()

try:
    payload = json.loads(body)
except json.JSONDecodeError as exc:
    raise SystemExit(f"/api/health did not return JSON: {exc}")

serialized = json.dumps(payload, sort_keys=True).lower()
if payload.get("demo") is True or payload.get("mock") is True or "mock-preview" in serialized:
    raise SystemExit("/api/health returned mock/demo health payload")

status = str(payload.get("status") or payload.get("ok") or payload.get("healthy") or "").lower()
if not status and "database" not in serialized and "api" not in serialized:
    raise SystemExit("/api/health payload does not look like FastAPI health")

print("OK API health: FastAPI response through preview route")
PY
}

day_html="$TMP_DIR/day.html"
calendar_html="$TMP_DIR/calendar.html"

assert_app_html "/day/2026-07-05" "$day_html"
assert_app_html "/calendar" "$calendar_html"
check_static_assets "$day_html" "$calendar_html"
check_api_health
