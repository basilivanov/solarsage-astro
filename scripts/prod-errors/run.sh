#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_PROD_ERRORS_RUN_SH
# ROLE: Flock wrapper script for automated production error triage cron job.
# DEPENDENCIES: bash, flock, python3, triage.py
# GRACE_ANCHORS: [RUN_SH]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-PROD-ERRORS-RUN-SH
# purpose: Acquire flock lock to ensure single-instance execution of triage.py.
# owns:
#   - scripts/prod-errors/run.sh
# inputs: optional script flags (--dry-run)
# outputs: triage.py stdout/stderr
# dependencies: bash, flock, python3
# side_effects: executes triage.py
# failure_policy: exits immediately if lock cannot be acquired
# END_MODULE_CONTRACT: M-SCRIPTS-PROD-ERRORS-RUN-SH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="/tmp/solarsage_prod_errors_triage.lock"
PROD_HOST="${PROD_ERRORS_SSH_HOST:-root@2.26.20.80}"
PROD_SSH_KEY="${PROD_ERRORS_SSH_KEY:-$HOME/.ssh/solarsage_prod_server_ed25519}"
BUGSINK_LOCAL_PORT="${BUGSINK_LOCAL_PORT:-18095}"

exec 200>"$LOCK_FILE"
flock -n 200 || { echo "Another triage instance is running. Exiting."; exit 0; }

cd "$SCRIPT_DIR/../.."

if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Bugsink UI/API binds to prod loopback only; open an ephemeral SSH tunnel
# for the duration of the triage when nothing already listens locally.
TUNNEL_PID=""
if ! curl -s -o /dev/null --max-time 3 "http://127.0.0.1:${BUGSINK_LOCAL_PORT}/"; then
  ssh -N -L "${BUGSINK_LOCAL_PORT}:127.0.0.1:${BUGSINK_LOCAL_PORT}" -i "$PROD_SSH_KEY" -o BatchMode=yes -o ExitOnForwardFailure=yes "$PROD_HOST" &
  TUNNEL_PID=$!
  trap '[[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null || true' EXIT
  sleep 3
fi

python3 "$SCRIPT_DIR/triage.py" "$@"
