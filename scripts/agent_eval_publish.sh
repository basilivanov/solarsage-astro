#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TOOL_AGENT_EVAL_PUBLISH
# ROLE: Publish a generated agent-eval report directory through a Cloudflare
#       quick tunnel and print the public URL.
# DEPENDENCIES: bash, python3, curl, .eval-runs/bin/cloudflared
# GRACE_ANCHORS: [EVAL_PUBLISH]
# ############################################################################

# START_MODULE_CONTRACT: M-AGENT-EVAL-PUBLISH
# purpose: Serve an eval report directory on loopback and expose it via an
#   ephemeral Cloudflare quick tunnel (no account/login required).
# owns:
#   - scripts/agent_eval_publish.sh
# inputs: path to report.html (or its directory); --stop; --status
# outputs: public https://*.trycloudflare.com URL on stdout
# dependencies: python3 http.server, cloudflared binary in .eval-runs/bin
# side_effects: starts two background processes; writes pid/log/url state
#   under .eval-runs/publish/
# emitted_logs: none
# invariants:
#   - HTTP server binds 127.0.0.1 only; public exposure is tunnel-only
#   - state directory is gitignored (.eval-runs)
# failure_policy: non-zero exit with stderr message if tunnel URL never appears
# END_MODULE_CONTRACT: M-AGENT-EVAL-PUBLISH

# START_MODULE_MAP: M-AGENT-EVAL-PUBLISH
# public_entrypoints:
#   - publish <report-path>
#   - stop
#   - status
# semantic_blocks:
#   - EVAL_PUBLISH: process orchestration and tunnel URL capture
# owned_tests: none (manual: publish existing report, curl public URL)
# END_MODULE_MAP: M-AGENT-EVAL-PUBLISH

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$REPO_ROOT/.eval-runs/publish"
CLOUDFLARED="$REPO_ROOT/.eval-runs/bin/cloudflared"
PORT="${EVAL_PUBLISH_PORT:-18927}"

mkdir -p "$STATE_DIR"

# START_BLOCK: EVAL_PUBLISH

_pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

stop() {
  local stopped=0
  for name in tunnel http; do
    if _pid_alive "$STATE_DIR/$name.pid"; then
      kill "$(cat "$STATE_DIR/$name.pid")" 2>/dev/null || true
      stopped=1
    fi
    rm -f "$STATE_DIR/$name.pid"
  done
  rm -f "$STATE_DIR/url"
  [[ $stopped -eq 1 ]] && echo "stopped" || echo "nothing running"
}

status() {
  if _pid_alive "$STATE_DIR/tunnel.pid" && [[ -f "$STATE_DIR/url" ]]; then
    cat "$STATE_DIR/url"
  else
    echo "not running"
    return 1
  fi
}

publish() {
  local target="$1"
  [[ -d "$target" ]] || target="$(dirname "$target")"
  local serve_dir report_name
  serve_dir="$(cd "$target" && pwd)"
  report_name="$(basename "$2")"

  stop >/dev/null

  nohup python3 -m http.server "$PORT" --bind 127.0.0.1 \
    --directory "$serve_dir" >"$STATE_DIR/http.log" 2>&1 &
  echo $! >"$STATE_DIR/http.pid"

  nohup "$CLOUDFLARED" tunnel --url "http://127.0.0.1:$PORT" \
    --no-autoupdate >"$STATE_DIR/tunnel.log" 2>&1 &
  echo $! >"$STATE_DIR/tunnel.pid"

  local url="" i
  for i in $(seq 1 30); do
    url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$STATE_DIR/tunnel.log" | head -1 || true)"
    [[ -n "$url" ]] && break
    sleep 1
  done

  if [[ -z "$url" ]]; then
    echo "error: tunnel URL did not appear within 30s; see $STATE_DIR/tunnel.log" >&2
    stop >/dev/null
    return 1
  fi

  echo "${url}/${report_name}" | tee "$STATE_DIR/url"
}

case "${1:-}" in
  --stop) stop ;;
  --status) status ;;
  "")
    echo "usage: $0 <path-to-report.html> | --stop | --status" >&2
    exit 2
    ;;
  *)
    [[ -f "$CLOUDFLARED" ]] || {
      echo "error: $CLOUDFLARED missing" >&2
      exit 1
    }
    publish "$(dirname "$1")" "$1"
    ;;
esac
# END_BLOCK: EVAL_PUBLISH
