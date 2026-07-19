#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_HOST_PREPARE — Idempotent production host preparation
# ROLE: Prepares the host environment for SolarSage Astro deployment (root-only).
# DEPENDENCIES: scripts/deploy/lib/prod-path-transaction.sh, bash, flock, getent, stat, install, runuser, systemd-analyze, systemctl, nginx, visudo, openssl, git, curl, cmp, sha256sum, python3.12, node, pnpm, docker, fail2ban-client, mktemp, readlink, dirname, mv, sleep
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-HOST-PREPARE
# purpose: Verify or apply system-level configuration, units, and directory setup.
# owns:
#   - scripts/deploy/prod-host-prepare.sh
# inputs:
#   - --check : read-only verification
#   - --apply : perform mutations
# outputs:
#   - exit 0 on success, non-zero on failure
# dependencies: none
# invariants:
#   - Must run as root.
#   - Single non-blocking lock.
#   - umask 027.
#   - Never start/restart/stop api, sidecar, frontend systemd units; Compose
#     owns app ports 8000/3002/18091 and pre-existing app units are only
#     disabled (never --now, never stopped) so a repeated apply after cutover
#     never restores autostart; the actual stop is a separate manual one-time
#     cutover step ordered by the owner before the first Compose deploy.
#   - Never print secrets or environment variable values.
# failure_policy: fails non-zero on any preflight or step error.
# END_MODULE_CONTRACT: M-PROD-HOST-PREPARE

# START_MODULE_MAP: M-PROD-HOST-PREPARE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - HOST_PREPARE: CLI parsing, preflight, state capture, rollback, verification, execution
# END_MODULE_MAP: M-PROD-HOST-PREPARE

# START_BLOCK: HOST_PREPARE
set -euo pipefail
umask 027

# 1. Compute SCRIPT_DIR and REPO_ROOT before functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Verify REPO_ROOT is a directory and not a symlink
if [ ! -d "$REPO_ROOT" ] || [ -L "$REPO_ROOT" ]; then
  echo "Error: REPO_ROOT '$REPO_ROOT' is not a directory or is a symlink" >&2
  exit 1
fi

# Source path transaction library (verifying library as regular non-symlink)
LIB_PATH="$REPO_ROOT/scripts/deploy/lib/prod-path-transaction.sh"
if [ ! -f "$LIB_PATH" ] || [ -L "$LIB_PATH" ]; then
  echo "Error: Path transaction library not found at $LIB_PATH or is a symlink" >&2
  exit 1
fi
source "$LIB_PATH"

# Constants
APP_ROOT=/opt/solarsage-astro
APP_USER=astro
APP_GROUP=astro
DOMAIN=astro.vasiliy-ivanov.ru
FINGERPRINT_FILE=/etc/solarsage/infra-fingerprint

# Helper to check if a command exists
cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Verification function
verify_host_state() {
  local check_marker="$1"
  local offsite_mode="$2"

  if [ "$check_marker" -ne 0 ] && [ "$check_marker" -ne 1 ]; then
    echo "Error: check_marker must be 0 or 1." >&2
    exit 1
  fi
  if [ "$offsite_mode" != "--preflight" ] && [ "$offsite_mode" != "--check" ]; then
    echo "Error: offsite_mode must be --preflight or --check." >&2
    exit 1
  fi

  local ver_errors=0
  report_ver_error() {
    echo "Verification Error: $1" >&2
    ver_errors=$((ver_errors + 1))
  }

  # 1. Check installed file equality (cmp -s) and owner/mode for units
  # All must be regular files and not symlinks. Only canonical units (DB and
  # the daily backup pair) are installed/byte-verified; obsolete app and
  # backup-maintenance templates are never installed or byte-verified here.
  local UNITS_TO_COMPARE=(
    "infra/systemd/solarsage-db.service:/etc/systemd/system/solarsage-db.service"
    "infra/systemd/solarsage-backup.service:/etc/systemd/system/solarsage-backup.service"
    "infra/systemd/solarsage-backup.timer:/etc/systemd/system/solarsage-backup.timer"
  )
  for item in "${UNITS_TO_COMPARE[@]}"; do
    IFS=":" read -r repo_path live_path <<< "$item"
    if [ ! -e "$live_path" ] || [ -L "$live_path" ] || [ ! -f "$live_path" ]; then
      report_ver_error "Installed unit '$live_path' is missing, is a symlink, or is not a regular file"
    else
      if ! cmp -s "$APP_ROOT/$repo_path" "$live_path"; then
        report_ver_error "Installed unit '$live_path' differs from repository '$repo_path'"
      fi
      local o_info
      o_info=$(stat -c "%U:%G:%a" "$live_path")
      if [ "$o_info" != "root:root:644" ]; then
        report_ver_error "Unit '$live_path' ownership/mode is $o_info, expected root:root:644"
      fi
    fi
  done

  # 1.5 GitHub host key known_hosts template check
  local gh_kh_template="infra/ssh/github.com.known_hosts"
  local gh_kh_live="/home/astro/.ssh/known_hosts.github"
  if [ -e "$gh_kh_live" ] || [ -L "$gh_kh_live" ]; then
    if [ ! -f "$gh_kh_live" ] || [ -L "$gh_kh_live" ]; then
      report_ver_error "GitHub known hosts file '$gh_kh_live' exists but is a symlink or not a regular file"
    else
      if ! cmp -s "$APP_ROOT/$gh_kh_template" "$gh_kh_live"; then
        report_ver_error "Installed GitHub known hosts '$gh_kh_live' differs from repository template '$gh_kh_template'"
      fi
      local gh_kh_info
      gh_kh_info=$(stat -c "%U:%G:%a" "$gh_kh_live")
      if [ "$gh_kh_info" != "astro:astro:600" ]; then
        report_ver_error "GitHub known hosts '$gh_kh_live' ownership/mode is $gh_kh_info, expected astro:astro:600"
      fi
    fi
  fi

  # 2. Wrapper verification (regular, not symlink)
  local wrap_path="/usr/local/sbin/solarsage-github-deploy"
  if [ ! -e "$wrap_path" ] || [ -L "$wrap_path" ] || [ ! -f "$wrap_path" ]; then
    report_ver_error "Wrapper '$wrap_path' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/production/solarsage-github-deploy" "$wrap_path"; then
      report_ver_error "Installed wrapper differs from repository template"
    fi
    local w_info
    w_info=$(stat -c "%U:%G:%a" "$wrap_path")
    if [ "$w_info" != "root:root:755" ]; then
      report_ver_error "Wrapper '$wrap_path' ownership/mode is $w_info, expected root:root:755"
    fi
  fi

  # 2.5 Orchestrator and canonical app compose verification (regular, not symlink)
  local orch_path="/usr/local/libexec/solarsage/prod-orchestrator"
  if [ ! -e "$orch_path" ] || [ -L "$orch_path" ] || [ ! -f "$orch_path" ]; then
    report_ver_error "Orchestrator '$orch_path' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/scripts/deploy/prod-orchestrator.sh" "$orch_path"; then
      report_ver_error "Installed orchestrator differs from repository source"
    fi
    local o_info
    o_info=$(stat -c "%U:%G:%a" "$orch_path")
    if [ "$o_info" != "root:root:755" ]; then
      report_ver_error "Orchestrator '$orch_path' ownership/mode is $o_info, expected root:root:755"
    fi
  fi

  # 2.6 Ephemeris installer + helper verification (regular, not symlink)
  local eph_inst="/usr/local/libexec/solarsage/prod-ephemeris-install"
  if [ ! -e "$eph_inst" ] || [ -L "$eph_inst" ] || [ ! -f "$eph_inst" ]; then
    report_ver_error "Ephemeris installer '$eph_inst' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/scripts/deploy/prod-ephemeris-install.sh" "$eph_inst"; then
      report_ver_error "Installed ephemeris installer differs from repository source"
    fi
    local e_info
    e_info=$(stat -c "%U:%G:%a" "$eph_inst")
    if [ "$e_info" != "root:root:755" ]; then
      report_ver_error "Ephemeris installer '$eph_inst' ownership/mode is $e_info, expected root:root:755"
    fi
  fi
  local eph_lib="/usr/local/libexec/solarsage/lib/ephemeris_artifact_check.py"
  if [ ! -e "$eph_lib" ] || [ -L "$eph_lib" ] || [ ! -f "$eph_lib" ]; then
    report_ver_error "Ephemeris verifier '$eph_lib' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/scripts/deploy/lib/ephemeris_artifact_check.py" "$eph_lib"; then
      report_ver_error "Installed ephemeris verifier differs from repository source"
    fi
  fi

  local compose_path="/etc/solarsage/compose/docker-compose.app.yml"
  if [ ! -e "$compose_path" ] || [ -L "$compose_path" ] || [ ! -f "$compose_path" ]; then
    report_ver_error "App compose '$compose_path' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/production/docker-compose.app.yml" "$compose_path"; then
      report_ver_error "Installed app compose differs from repository source"
    fi
    local c_info
    c_info=$(stat -c "%U:%G:%a" "$compose_path")
    if [ "$c_info" != "root:root:644" ]; then
      report_ver_error "App compose '$compose_path' ownership/mode is $c_info, expected root:root:644"
    fi
  fi

  # 2.6 Tmpfiles declaration and maintenance lock verification
  local tmpfiles_path="/etc/tmpfiles.d/solarsage.conf"
  if [ ! -e "$tmpfiles_path" ] || [ -L "$tmpfiles_path" ] || [ ! -f "$tmpfiles_path" ]; then
    report_ver_error "Tmpfiles declaration '$tmpfiles_path' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/production/tmpfiles.d/solarsage.conf" "$tmpfiles_path"; then
      report_ver_error "Installed tmpfiles declaration differs from repository source"
    fi
    local t_info
    t_info=$(stat -c "%U:%G:%a" "$tmpfiles_path")
    if [ "$t_info" != "root:root:644" ]; then
      report_ver_error "Tmpfiles declaration '$tmpfiles_path' ownership/mode is $t_info, expected root:root:644"
    fi
  fi

  local lock_path="/run/solarsage-maintenance.lock"
  if [ ! -e "$lock_path" ] || [ -L "$lock_path" ] || [ ! -f "$lock_path" ]; then
    report_ver_error "Maintenance lock '$lock_path' is missing, is a symlink, or is not a regular file"
  else
    local l_info
    l_info=$(stat -c "%U:%G:%a" "$lock_path")
    if [ "$l_info" != "root:astro:660" ]; then
      report_ver_error "Maintenance lock '$lock_path' ownership/mode is $l_info, expected root:astro:660"
    fi
  fi

  # 3. Sudoers verification (regular, not symlink)
  local sudoers_path="/etc/sudoers.d/90-solarsage-deploy"
  if [ ! -e "$sudoers_path" ] || [ -L "$sudoers_path" ] || [ ! -f "$sudoers_path" ]; then
    report_ver_error "Sudoers policy '$sudoers_path' is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/production/solarsage-deploy.sudoers" "$sudoers_path"; then
      report_ver_error "Installed sudoers policy differs from repository template"
    fi
    local s_info
    s_info=$(stat -c "%U:%G:%a" "$sudoers_path")
    if [ "$s_info" != "root:root:440" ]; then
      report_ver_error "Sudoers policy '$sudoers_path' ownership/mode is $s_info, expected root:root:440"
    fi
  fi

  # 4. Nginx verification (including symlink target)
  local nginx_avail="/etc/nginx/sites-available/astro.vasiliy-ivanov.ru.conf"
  local nginx_enabled="/etc/nginx/sites-enabled/astro.vasiliy-ivanov.ru.conf"
  local reject_live="/etc/nginx/conf.d/00-solarsage-default-reject.conf"

  if [ ! -e "$nginx_avail" ] || [ -L "$nginx_avail" ] || [ ! -f "$nginx_avail" ]; then
    report_ver_error "Nginx config in sites-available is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/nginx/astro.vasiliy-ivanov.ru.conf" "$nginx_avail"; then
      report_ver_error "Installed Nginx config differs from repository template"
    fi
    local n_info
    n_info=$(stat -c "%U:%G:%a" "$nginx_avail")
    if [ "$n_info" != "root:root:644" ]; then
      report_ver_error "Nginx config '$nginx_avail' ownership/mode is $n_info, expected root:root:644"
    fi
  fi

  if [ ! -L "$nginx_enabled" ]; then
    report_ver_error "Nginx enabled symlink '$nginx_enabled' is missing or not a symlink"
  else
    local link_target
    link_target=$(readlink -f "$nginx_enabled")
    if [ "$link_target" != "$nginx_avail" ]; then
      report_ver_error "Nginx enabled symlink target is $link_target, expected $nginx_avail"
    fi
  fi

  # Default Reject verification (regular, not symlink)
  if [ ! -e "$reject_live" ] || [ -L "$reject_live" ] || [ ! -f "$reject_live" ]; then
    report_ver_error "Default reject Nginx config is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/nginx/00-solarsage-default-reject.conf" "$reject_live"; then
      report_ver_error "Installed default reject config differs from repository template"
    fi
    local r_info
    r_info=$(stat -c "%U:%G:%a" "$reject_live")
    if [ "$r_info" != "root:root:644" ]; then
      report_ver_error "Default reject config ownership/mode is $r_info, expected root:root:644"
    fi
  fi

  # Fail2ban sshd jail verification (regular, not symlink)
  local jail_live="/etc/fail2ban/jail.d/solarsage-sshd.local"
  if [ ! -e "$jail_live" ] || [ -L "$jail_live" ] || [ ! -f "$jail_live" ]; then
    report_ver_error "Fail2ban sshd jail is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/fail2ban/jail.d/solarsage-sshd.local" "$jail_live"; then
      report_ver_error "Installed Fail2ban jail differs from repository template"
    fi
    local j_info
    j_info=$(stat -c "%U:%G:%a" "$jail_live")
    if [ "$j_info" != "root:root:644" ]; then
      report_ver_error "Fail2ban jail ownership/mode is $j_info, expected root:root:644"
    fi
  fi

  # Certbot deploy hook verification (regular, not symlink)
  local hook_live="/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"
  if [ ! -e "$hook_live" ] || [ -L "$hook_live" ] || [ ! -f "$hook_live" ]; then
    report_ver_error "Certbot deploy hook is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$APP_ROOT/infra/certbot/deploy-hooks/20-solarsage-reload-nginx" "$hook_live"; then
      report_ver_error "Installed deploy hook differs from repository template"
    fi
    local h_info
    h_info=$(stat -c "%U:%G:%a" "$hook_live")
    if [ "$h_info" != "root:root:755" ]; then
      report_ver_error "Deploy hook ownership/mode is $h_info, expected root:root:755"
    fi
  fi

  # Certbot timer verification
  # (Timer check disabled in dev/non-production verification)
  if [ "$check_marker" -eq 1 ]; then
    if ! systemctl is-enabled certbot.timer >/dev/null 2>&1; then
      report_ver_error "certbot.timer is not enabled"
    fi
    if [ "$(systemctl is-active certbot.timer)" != "active" ]; then
      report_ver_error "certbot.timer is not active"
    fi
  fi

  # Absence of enabled default/bootstrap sites (checked with ! -e && ! -L)
  if [ -e "/etc/nginx/sites-enabled/default" ] || [ -L "/etc/nginx/sites-enabled/default" ]; then
    report_ver_error "/etc/nginx/sites-enabled/default still exists"
  fi
  if [ -e "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf" ] || [ -L "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf" ]; then
    report_ver_error "Bootstrap Nginx enabled symlink still exists"
  fi
  if [ -e "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf" ] || [ -L "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf" ]; then
    report_ver_error "Bootstrap Nginx available file still exists"
  fi

  # 5. Enabled/disabled states
  # Enabled: DB and the canonical daily backup timer (installed orchestrator).
  local ENABLED_UNITS=(
    "solarsage-db.service"
    "solarsage-backup.timer"
  )
  for unit in "${ENABLED_UNITS[@]}"; do
    if ! systemctl is-enabled "$unit" >/dev/null 2>&1; then
      report_ver_error "Service '$unit' is not enabled"
    fi
  done

  # Disabled: app units (Compose owns app ports) and the parked backup timer.
  # A static unit (e.g. oneshot backup-maintenance.service) reports "static"
  # from is-enabled, which is accepted; only enabled/enabled-runtime is an error.
  # Host preparation never starts/stops/restarts any of these.
  local DISABLED_UNITS=(
    "solarsage-sidecar.service"
    "solarsage-api.service"
    "solarsage-frontend.service"
    "solarsage-backup-maintenance.timer"
  )
  for unit in "${DISABLED_UNITS[@]}"; do
    local unit_state
    unit_state=$(systemctl is-enabled "$unit" 2>/dev/null || echo "missing")
    if [ "$unit_state" = "enabled" ] || [ "$unit_state" = "enabled-runtime" ]; then
      report_ver_error "Unit '$unit' must be disabled (state: $unit_state; Compose owns app ports; parked timer)"
    fi
  done

  # Check active states for the canonical backup timer; parked units must not be active.
  if [ "$check_marker" -eq 1 ]; then
    if [ "$(systemctl is-active solarsage-backup.timer)" != "active" ]; then
      report_ver_error "solarsage-backup.timer is not active"
    fi
    local PARKED_INACTIVE_UNITS=(
      "solarsage-backup-maintenance.timer"
      "solarsage-backup-maintenance.service"
    )
    for unit in "${PARKED_INACTIVE_UNITS[@]}"; do
      if [ "$(systemctl is-active "$unit")" = "active" ]; then
        report_ver_error "Parked unit '$unit' is active"
      fi
    done
  fi

  # 6. DB active state
  if [ "$(systemctl is-active solarsage-db.service)" != "active" ]; then
    report_ver_error "solarsage-db.service is not active"
  fi

  # 7. Docker DB health status
  local container_name="solarsage-db"
  local running
  running=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "unknown")
  local health
  health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
  if [ "$running" != "running" ]; then
    report_ver_error "Docker container '$container_name' is not running ($running)"
  elif [ "$health" != "healthy" ]; then
    report_ver_error "Docker container '$container_name' is not healthy ($health)"
  fi

  # 8. Directory permissions
  verify_dir_perms() {
    local dir="$1"
    local expected_owner="$2"
    local expected_mode="$3"
    if [ ! -d "$dir" ] || [ -L "$dir" ]; then
      report_ver_error "Directory '$dir' does not exist or is a symlink"
    else
      local owner
      owner=$(stat -c "%U:%G" "$dir")
      local mode
      mode=$(stat -c "%a" "$dir")
      if [ "$owner" != "$expected_owner" ]; then
        report_ver_error "Directory '$dir' owner is $owner, expected $expected_owner"
      fi
      if [ "$mode" != "$expected_mode" ]; then
        report_ver_error "Directory '$dir' mode is $mode, expected $expected_mode"
      fi
    fi
  }
  verify_dir_perms "/var/backups/solarsage" "astro:astro" "700"
  verify_dir_perms "/opt/solarsage-ephemeris" "root:root" "755"
  verify_dir_perms "/opt/solarsage-ephemeris/releases" "root:root" "755"
  verify_dir_perms "/etc/solarsage" "root:root" "755"
  verify_dir_perms "/etc/solarsage/compose" "root:root" "755"
  verify_dir_perms "/usr/local/libexec/solarsage" "root:root" "755"
  verify_dir_perms "/usr/local/libexec/solarsage/lib" "root:root" "755"
  verify_dir_perms "/var/lib/solarsage/orchestrator" "astro:astro" "700"
  verify_dir_perms "/var/www/letsencrypt" "root:root" "755"
  verify_dir_perms "/var/www/letsencrypt/.well-known" "root:root" "755"
  verify_dir_perms "/var/www/letsencrypt/.well-known/acme-challenge" "root:root" "755"

  # 9. Sudoers valid
  if ! visudo -cf /etc/sudoers >/dev/null 2>&1; then
    report_ver_error "/etc/sudoers syntax validation failed"
  fi

  # 10. Nginx config valid
  if ! nginx -t >/dev/null 2>&1; then
    report_ver_error "Nginx syntax validation failed"
  fi

  # 11. Legacy units inactive/disabled
  local LEGACY_UNITS=("solarsage.service" "solarsage-frontend-preview-3001.service")
  for unit in "${LEGACY_UNITS[@]}"; do
    if systemctl list-unit-files "$unit" >/dev/null 2>&1; then
      if systemctl is-enabled "$unit" >/dev/null 2>&1; then
        report_ver_error "Legacy service '$unit' is still enabled"
      fi
      if [ "$(systemctl is-active "$unit")" = "active" ]; then
        report_ver_error "Legacy service '$unit' is active"
      fi
    fi
  done

  # 12. Fingerprint check
  if [ "$check_marker" -eq 1 ]; then
    if [ ! -f "$FINGERPRINT_FILE" ] || [ -L "$FINGERPRINT_FILE" ]; then
      report_ver_error "Fingerprint file '$FINGERPRINT_FILE' is missing or is a symlink"
    else
      local fp_info
      fp_info=$(stat -c "%U:%G:%a" "$FINGERPRINT_FILE")
      if [ "$fp_info" != "root:root:644" ]; then
        report_ver_error "Fingerprint file '$FINGERPRINT_FILE' ownership/mode is $fp_info, expected root:root:644"
      fi

      # Line-aware read/array validation (require exactly one line)
      local fp_lines=()
      while IFS= read -r line; do
        fp_lines+=("$line")
      done < "$FINGERPRINT_FILE"

      if [ "${#fp_lines[@]}" -ne 1 ]; then
        report_ver_error "Fingerprint file must contain exactly one line (has ${#fp_lines[@]} lines)"
      else
        local fp_val="${fp_lines[0]}"
        if [[ ! "$fp_val" =~ ^[0-9a-f]{64}$ ]]; then
          report_ver_error "Fingerprint file content is not exactly 64 lowercase hex characters"
        else
          local repo_fp
          repo_fp=$("$APP_ROOT/scripts/deploy/prod-infra-fingerprint.sh")
          if [ "$fp_val" != "$repo_fp" ]; then
            report_ver_error "Applied fingerprint does not match repository fingerprint"
          fi
        fi
      fi
    fi
  fi

  # 13. The old offsite/profile integration is intentionally absent here: the
  # active host preparation path never requires the parked profile engine
  # (source.env / generated current profiles). Offsite readiness belongs to the
  # canonical orchestrator preflight (restic binary + password file contract).

  if [ "$ver_errors" -gt 0 ]; then
    return 1
  fi
  return 0
}

# Transaction Management Variables
ROLLBACK_STARTED=0
TRANSACTION_COMMITTED=0

post_host_restore() {
  echo "Restoring host daemon-reload, Nginx reload, and Fail2ban restart..." >&2
  /usr/bin/systemctl daemon-reload || true

  if /usr/sbin/nginx -t >/dev/null 2>&1; then
    /usr/bin/systemctl reload nginx.service || true
  else
    echo "Warning: Restored Nginx configuration failed syntax validation." >&2
  fi

  if /usr/bin/fail2ban-client -d >/dev/null 2>&1; then
    /usr/bin/systemctl restart fail2ban || true
  else
    echo "Warning: Restored Fail2ban configuration failed validation." >&2
  fi
}

on_transaction_exit() {
  local exit_status=$?
  trap - EXIT INT TERM

  if [ "$TRANSACTION_COMMITTED" -ne 1 ]; then
    if [ "$ROLLBACK_STARTED" -ne 1 ]; then
      ROLLBACK_STARTED=1
      if prod_tx_rollback; then
        post_host_restore
        prod_tx_cleanup
      else
        echo "Warning: Transaction rollback failed. Snapshot directory preserved at: ${PROD_TX_TEMP_DIR:-}" >&2
      fi
    fi
    # If uncommitted path exits with 0, turn it into an internal error (exit 1)
    if [ "$exit_status" -eq 0 ]; then
      exit_status=1
    fi
  else
    prod_tx_cleanup
  fi
  exit "$exit_status"
}

on_transaction_int() {
  trap - INT TERM
  exit 130
}

on_transaction_term() {
  trap - INT TERM
  exit 143
}

# Main main implementation
main() {
  local errors=0
  report_error() {
    echo "Preflight Error: $1" >&2
    errors=$((errors + 1))
  }

  # 1. Argument validation must happen before root check
  if [ "$#" -ne 1 ] || { [ "$1" != "--check" ] && [ "$1" != "--apply" ]; }; then
    echo "Usage: $0 {--check|--apply}" >&2
    exit 2
  fi
  local MODE="$1"

  # 2. Root check
  if [ "$EUID" -ne 0 ]; then
    echo "Error: this script must be run as root." >&2
    exit 1
  fi

  # 3. Lock file under root-owned /run
  local LOCKFILE="/run/solarsage-host-prepare.lock"
  exec 9>"$LOCKFILE"
  if ! flock -n 9; then
    echo "Error: another host-prepare instance is running." >&2
    exit 1
  fi

  # 4. Common preflight checks
  # OS checks
  if [ -f /etc/os-release ]; then
    local OS_VER OS_NAME
    OS_VER=$( (source /etc/os-release && echo "${VERSION_ID:-}") )
    OS_NAME=$( (source /etc/os-release && echo "${NAME:-}") )
    if [ "$OS_VER" != "24.04" ] || [[ ! "$OS_NAME" =~ Ubuntu ]]; then
      report_error "OS is not Ubuntu 24.04 (detected $OS_NAME $OS_VER)"
    fi
  else
    report_error "/etc/os-release not found"
  fi

  # User/group checks
  local HAS_USER=0
  local HAS_GROUP=0
  if getent passwd "$APP_USER" >/dev/null; then
    HAS_USER=1
  else
    report_error "User '$APP_USER' does not exist"
  fi
  if getent group "$APP_GROUP" >/dev/null; then
    HAS_GROUP=1
  else
    report_error "Group '$APP_GROUP' does not exist"
  fi

  # APP_ROOT validation
  local HAS_APP_ROOT=0
  if [ ! -d "$APP_ROOT" ] || [ -L "$APP_ROOT" ]; then
    report_error "Directory $APP_ROOT does not exist or is a symlink"
  else
    HAS_APP_ROOT=1
    local OWNER_INFO
    OWNER_INFO=$(stat -c "%U:%G" "$APP_ROOT")
    if [ "$OWNER_INFO" != "$APP_USER:$APP_GROUP" ]; then
      report_error "$APP_ROOT ownership is $OWNER_INFO, expected $APP_USER:$APP_GROUP"
    fi
  fi

  # Canonical environment file check (operator-created per runbook): real
  # non-symlink root:astro 0640 with the required DB keys present. Values are
  # never printed. The active host preparation path never requires the parked
  # profile engine (source.env / generated current profiles).
  local APP_ENV_FILE="/etc/solarsage/app.env"
  if [ ! -f "$APP_ENV_FILE" ] || [ -L "$APP_ENV_FILE" ]; then
    report_error "Canonical env file $APP_ENV_FILE is missing or not a regular file"
  else
    local env_info
    env_info=$(stat -c "%U:%G:%a" "$APP_ENV_FILE")
    if [ "$env_info" != "root:astro:640" ]; then
      report_error "Canonical env file $APP_ENV_FILE ownership/mode is $env_info, expected root:astro:640"
    fi
    local db_key
    for db_key in POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB; do
      if ! grep -qE "^${db_key}=.+" "$APP_ENV_FILE"; then
        report_error "Canonical env file $APP_ENV_FILE is missing required key $db_key"
      fi
    done
  fi

  # Required commands (including helper dependencies)
  local REQUIRED_CMDS=(git curl cmp sha256sum python3.12 node pnpm docker nginx certbot pg_dump pg_isready systemctl systemd-tmpfiles visudo openssl runuser install flock getent stat systemd-analyze mktemp readlink dirname mv fail2ban-client sleep restic ssh timeout wc tail od)
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! cmd_exists "$cmd"; then
      report_error "Required command '$cmd' is missing"
    fi
  done

  # Docker compose check
  if cmd_exists docker; then
    if ! docker compose version >/dev/null 2>&1; then
      report_error "'docker compose version' failed"
    fi
  fi

  # Node & pnpm checks
  if [ "$HAS_USER" -eq 1 ] && [ "$HAS_APP_ROOT" -eq 1 ] && cmd_exists runuser; then
    if cmd_exists node; then
      local NODE_VER
      NODE_VER=$(runuser -u "$APP_USER" -- bash -c "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; cd \"$APP_ROOT\" && node -v" 2>/dev/null | tr -d 'v' || true)
      if [ -n "$NODE_VER" ]; then
        local major minor patch_num
        IFS='.' read -r major minor patch_num <<< "$NODE_VER" || true
        if [[ "$major" =~ ^[0-9]+$ ]] && [[ "$minor" =~ ^[0-9]+$ ]]; then
          if [ "$major" -lt 20 ] || { [ "$major" -eq 20 ] && [ "$minor" -lt 9 ]; }; then
            report_error "Node version is $NODE_VER, expected >= 20.9"
          fi
        else
          report_error "Invalid Node version format detected: $NODE_VER"
        fi
      else
        report_error "Failed to retrieve Node version"
      fi
    fi

    if cmd_exists pnpm; then
      local PNPM_VER
      PNPM_VER=$(runuser -u "$APP_USER" -- bash -c "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; cd \"$APP_ROOT\" && pnpm -v" 2>/dev/null || true)
      if [ "$PNPM_VER" != "10.32.1" ]; then
        report_error "pnpm version is $PNPM_VER, expected exact 10.32.1"
      fi
    fi

    # Git worktree check
    if ! runuser -u "$APP_USER" -- git -C "$APP_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      report_error "$APP_ROOT is not a Git worktree"
    fi
  fi

  # Repository templates preflight (no symlinks in repo templates, regular files check)
  if [ "$HAS_APP_ROOT" -eq 1 ]; then
    local INVENTORY_FILES=(
      "infra/nginx/astro.vasiliy-ivanov.ru.conf"
      "infra/nginx/00-solarsage-default-reject.conf"
      "infra/certbot/deploy-hooks/20-solarsage-reload-nginx"
      "infra/fail2ban/jail.d/solarsage-sshd.local"
      "infra/production/docker-compose.yml"
      "infra/production/docker-compose.app.yml"
      "infra/production/solarsage-deploy.sudoers"
      "infra/production/solarsage-github-deploy"
      "infra/production/tmpfiles.d/solarsage.conf"
      "infra/ssh/github.com.known_hosts"
      "infra/systemd/solarsage-db.service"
      "infra/systemd/solarsage-backup.service"
      "infra/systemd/solarsage-backup.timer"
      "scripts/deploy/prod-orchestrator.sh"
      "scripts/deploy/prod-host-prepare.sh"
      "scripts/deploy/prod-infra-fingerprint.sh"
      "scripts/deploy/prod-os-bootstrap.sh"
      "scripts/deploy/prod-cert-prepare.sh"
      "scripts/deploy/prod-github-access.sh"
      "scripts/deploy/lib/prod-path-transaction.sh"
    )

    for inv_file in "${INVENTORY_FILES[@]}"; do
      local full_inv_path="$APP_ROOT/$inv_file"
      if [ ! -e "$full_inv_path" ] || [ -L "$full_inv_path" ] || [ ! -f "$full_inv_path" ]; then
        report_error "Template file '$inv_file' is missing in repository, is a symlink, or is not a regular file"
      fi
    done

    # bash -n syntax checks
    local SHELL_SCRIPTS=(
      "scripts/deploy/prod-orchestrator.sh"
      "scripts/deploy/prod-host-prepare.sh"
      "scripts/deploy/prod-infra-fingerprint.sh"
      "scripts/deploy/prod-os-bootstrap.sh"
      "scripts/deploy/prod-cert-prepare.sh"
      "scripts/deploy/prod-github-access.sh"
      "infra/production/solarsage-github-deploy"
       "infra/certbot/deploy-hooks/20-solarsage-reload-nginx"
      "scripts/deploy/lib/prod-path-transaction.sh"
    )
    for script_path in "${SHELL_SCRIPTS[@]}"; do
      if [ -f "$APP_ROOT/$script_path" ]; then
        if ! bash -n "$APP_ROOT/$script_path"; then
          report_error "Syntax check failed for $script_path"
        fi
      fi
    done

    if cmd_exists visudo; then
      if [ -f "$APP_ROOT/infra/production/solarsage-deploy.sudoers" ]; then
        if ! visudo -cf "$APP_ROOT/infra/production/solarsage-deploy.sudoers" >/dev/null 2>&1; then
          report_error "visudo syntax check failed for solarsage-deploy.sudoers template"
        fi
      fi
    fi

    if cmd_exists systemd-analyze; then
      local UNITS=(
        "infra/systemd/solarsage-db.service"
        "infra/systemd/solarsage-backup.timer"
      )
      for unit in "${UNITS[@]}"; do
        if [ -f "$APP_ROOT/$unit" ]; then
          if ! systemd-analyze verify "$APP_ROOT/$unit" >/dev/null 2>&1; then
            report_error "systemd-analyze verify failed for $unit"
          fi
        fi
      done
      # The canonical backup unit references the installed orchestrator, which
      # this very --apply installs later. On a clean host (installed path not
      # yet present) verify a temporary unit copy whose ExecStart points at the
      # repository source instead; no installation or runtime mutation. When
      # the installed path already exists, verify the unit as-is.
      local BACKUP_UNIT="infra/systemd/solarsage-backup.service"
      if [ -f "$APP_ROOT/$BACKUP_UNIT" ]; then
        if [ -x "/usr/local/libexec/solarsage/prod-orchestrator" ] && [ ! -L "/usr/local/libexec/solarsage/prod-orchestrator" ]; then
          if ! systemd-analyze verify "$APP_ROOT/$BACKUP_UNIT" >/dev/null 2>&1; then
            report_error "systemd-analyze verify failed for $BACKUP_UNIT"
          fi
        else
          local STAGED_UNIT_DIR
          STAGED_UNIT_DIR=$(mktemp -d)
          trap 'rm -rf "$STAGED_UNIT_DIR"' EXIT
          cp "$APP_ROOT/infra/systemd/solarsage-db.service" "$STAGED_UNIT_DIR/"
          sed "s|/usr/local/libexec/solarsage/prod-orchestrator|$APP_ROOT/scripts/deploy/prod-orchestrator.sh|g" \
            "$APP_ROOT/$BACKUP_UNIT" > "$STAGED_UNIT_DIR/solarsage-backup.service"
          if ! systemd-analyze verify "$STAGED_UNIT_DIR/solarsage-backup.service" >/dev/null 2>&1; then
            report_error "systemd-analyze verify failed for $BACKUP_UNIT (staged repository ExecStart)"
          fi
          rm -rf "$STAGED_UNIT_DIR"
          trap - EXIT
        fi
      fi
    fi

    if [ -f "$APP_ROOT/infra/production/docker-compose.yml" ] && cmd_exists docker; then
      if docker compose version >/dev/null 2>&1; then
        local TMP_COMPOSE
        TMP_COMPOSE=$(mktemp)
        trap 'rm -f "$TMP_COMPOSE"' EXIT
        if ! /usr/bin/docker compose --env-file /etc/solarsage/app.env -f "$APP_ROOT/infra/production/docker-compose.yml" config >"$TMP_COMPOSE" 2>/dev/null; then
          report_error "docker compose config validation failed"
        fi
        rm -f "$TMP_COMPOSE"
        trap - EXIT
      fi
    fi
  fi

  # SSL Certificate check
  if cmd_exists openssl; then
    local CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    local KEY_FILE="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
    if [ ! -e "$CERT_FILE" ] || [ ! -e "$KEY_FILE" ]; then
      report_error "SSL Certificate/Key not found at Let's Encrypt path. Please complete cert-prepare setup first."
    else
      local resolved_cert resolved_key
      resolved_cert=$(readlink -f "$CERT_FILE")
      resolved_key=$(readlink -f "$KEY_FILE")

      if [ ! -f "$resolved_cert" ] || [ -L "$resolved_cert" ] || [ ! -r "$resolved_cert" ]; then
        report_error "Resolved certificate path '$resolved_cert' is not a readable regular file"
      fi
      if [ ! -f "$resolved_key" ] || [ -L "$resolved_key" ] || [ ! -r "$resolved_key" ]; then
        report_error "Resolved private key path '$resolved_key' is not a readable regular file"
      fi

      if ! openssl x509 -noout -checkhost "$DOMAIN" -in "$resolved_cert" >/dev/null 2>&1; then
        report_error "SSL Certificate domain validation failed for '$DOMAIN'"
      fi
      if ! openssl x509 -noout -checkend 1209600 -in "$resolved_cert" >/dev/null 2>&1; then
        report_error "SSL Certificate at $CERT_FILE is expired or near expiry (< 14 days)."
      fi
    fi
  fi

  if [ "$errors" -gt 0 ]; then
    echo "Error: Host preflight checks failed with $errors error(s)." >&2
    exit 1
  fi

  if [ "$MODE" = "--check" ]; then
    if verify_host_state 1 --check; then
      echo "HOST PREPARE CHECK PASS"
      exit 0
    else
      echo "Error: Host prepare verification checks failed." >&2
      exit 1
    fi
  fi

  if [ "$MODE" = "--apply" ]; then
    # Verify repository source is clean
    local DIRTY_CHECK
    DIRTY_CHECK=$(
      runuser -u "$APP_USER" -- bash -c "
        set -euo pipefail
        cd \"$APP_ROOT\"
        has_changes=0
        if ! git diff --quiet; then has_changes=1; fi
        if ! git diff --cached --quiet; then has_changes=1; fi

        tmp_untracked=\$(mktemp)
        chmod 0600 \"\$tmp_untracked\"
        trap 'rm -f \"\$tmp_untracked\"' EXIT INT TERM
        if ! git ls-files --others --exclude-standard -z > \"\$tmp_untracked\"; then
          echo \"Error: git ls-files failed\" >&2
          rm -f \"\$tmp_untracked\"
          trap - EXIT INT TERM
          exit 1
        fi

        untracked_count=0
        while IFS= read -r -d '' file; do
          untracked_count=\$((untracked_count + 1))
        done < \"\$tmp_untracked\"
        rm -f \"\$tmp_untracked\"
        trap - EXIT INT TERM

        if [ \"\$untracked_count\" -gt 0 ]; then has_changes=1; fi
        echo \"\$has_changes\"
      "
    )
    if [ "$DIRTY_CHECK" -ne 0 ]; then
      echo "Error: Repository source is dirty. Host preparation requires clean worktree." >&2
      exit 1
    fi

    # 1. Register paths for the transaction helper (canonical installs only;
    # obsolete app/backup-maintenance unit templates are never installed)
    PROD_TX_PATHS["db_unit"]="/etc/systemd/system/solarsage-db.service"
    PROD_TX_PATHS["backup_unit"]="/etc/systemd/system/solarsage-backup.service"
    PROD_TX_PATHS["backup_timer"]="/etc/systemd/system/solarsage-backup.timer"
    PROD_TX_PATHS["wrapper"]="/usr/local/sbin/solarsage-github-deploy"
    PROD_TX_PATHS["sudoers"]="/etc/sudoers.d/90-solarsage-deploy"
    PROD_TX_PATHS["nginx_avail"]="/etc/nginx/sites-available/astro.vasiliy-ivanov.ru.conf"
    PROD_TX_PATHS["nginx_enabled"]="/etc/nginx/sites-enabled/astro.vasiliy-ivanov.ru.conf"
    PROD_TX_PATHS["default_enabled"]="/etc/nginx/sites-enabled/default"
    PROD_TX_PATHS["reject"]="/etc/nginx/conf.d/00-solarsage-default-reject.conf"
    PROD_TX_PATHS["hook"]="/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"
    PROD_TX_PATHS["jail"]="/etc/fail2ban/jail.d/solarsage-sshd.local"
    PROD_TX_PATHS["bootstrap_avail"]="/etc/nginx/sites-available/$DOMAIN-bootstrap.conf"
    PROD_TX_PATHS["bootstrap_enabled"]="/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf"
    PROD_TX_PATHS["fingerprint"]="/etc/solarsage/infra-fingerprint"
    PROD_TX_PATHS["gh_known_hosts"]="/home/astro/.ssh/known_hosts.github"
    PROD_TX_PATHS["orchestrator"]="/usr/local/libexec/solarsage/prod-orchestrator"
    PROD_TX_PATHS["app_compose"]="/etc/solarsage/compose/docker-compose.app.yml"
    PROD_TX_PATHS["tmpfiles"]="/etc/tmpfiles.d/solarsage.conf"

    # 2. Capture host state before mutations
    if ! prod_tx_capture "/run"; then
      echo "Error: failed to capture path state for transaction" >&2
      exit 1
    fi

    # 3. Setup traps for exit/interrupts
    trap on_transaction_exit EXIT
    trap on_transaction_int INT
    trap on_transaction_term TERM

    # 4. Create directories idempotently
    install -d -o "$APP_USER" -g "$APP_GROUP" -m 0700 /var/backups/solarsage
    install -d -o root -g root -m 0755 /opt/solarsage-ephemeris
    install -d -o root -g root -m 0755 /opt/solarsage-ephemeris/releases
    install -d -o root -g root -m 0755 /etc/solarsage
    install -d -o root -g root -m 0755 /etc/solarsage/compose
    install -d -o root -g root -m 0755 /usr/local/libexec/solarsage
    install -d -o "$APP_USER" -g "$APP_GROUP" -m 0700 /var/lib/solarsage/orchestrator
    install -d -o root -g root -m 0755 /var/www/letsencrypt
    install -d -o root -g root -m 0755 /var/www/letsencrypt/.well-known
    install -d -o root -g root -m 0755 /var/www/letsencrypt/.well-known/acme-challenge

    # 4.1 Install the canonical app orchestrator and compose stack byte-exact
    install -o root -g root -m 0755 "$APP_ROOT/scripts/deploy/prod-orchestrator.sh" "/usr/local/libexec/solarsage/prod-orchestrator"
    install -o root -g root -m 0755 "$APP_ROOT/scripts/deploy/prod-ephemeris-install.sh" "/usr/local/libexec/solarsage/prod-ephemeris-install"
    install -d -o root -g root -m 0755 /usr/local/libexec/solarsage/lib
    install -o root -g root -m 0644 "$APP_ROOT/scripts/deploy/lib/ephemeris_artifact_check.py" "/usr/local/libexec/solarsage/lib/ephemeris_artifact_check.py"
    install -o root -g root -m 0644 "$APP_ROOT/infra/production/docker-compose.app.yml" "/etc/solarsage/compose/docker-compose.app.yml"

    # 4.2 Install the tmpfiles declaration and materialize the maintenance lock
    install -o root -g root -m 0644 "$APP_ROOT/infra/production/tmpfiles.d/solarsage.conf" "/etc/tmpfiles.d/solarsage.conf"
    if ! systemd-tmpfiles --create /etc/tmpfiles.d/solarsage.conf; then
      echo "Error: systemd-tmpfiles --create failed for the maintenance lock declaration." >&2
      exit 1
    fi

    # 5. Install canonical systemd service units only (DB and the daily backup
    # pair). Obsolete app and backup-maintenance unit templates are never
    # installed; their already-installed names are only disabled (see below).
    local SYSTEMD_SRC_FILES=(
      "solarsage-db.service"
      "solarsage-backup.service"
      "solarsage-backup.timer"
    )
    for unit in "${SYSTEMD_SRC_FILES[@]}"; do
      install -o root -g root -m 0644 "$APP_ROOT/infra/systemd/$unit" "/etc/systemd/system/$unit"
    done

    # 6. Install deploy wrapper and sudoers policy
    visudo -cf "$APP_ROOT/infra/production/solarsage-deploy.sudoers" >/dev/null
    install -o root -g root -m 0755 "$APP_ROOT/infra/production/solarsage-github-deploy" "/usr/local/sbin/solarsage-github-deploy"
    install -o root -g root -m 0440 "$APP_ROOT/infra/production/solarsage-deploy.sudoers" "/etc/sudoers.d/90-solarsage-deploy"

    # Verify sudoers candidate
    if ! visudo -cf /etc/sudoers >/dev/null 2>&1; then
      echo "Error: Sudoers policy candidate failed validation." >&2
      exit 1
    fi

    # 7. Install Nginx config, default reject, certbot hook, and fail2ban jail
    install -o root -g root -m 0644 "$APP_ROOT/infra/nginx/00-solarsage-default-reject.conf" "/etc/nginx/conf.d/00-solarsage-default-reject.conf"
    install -o root -g root -m 0644 "$APP_ROOT/infra/nginx/astro.vasiliy-ivanov.ru.conf" "/etc/nginx/sites-available/$DOMAIN.conf"
    rm -f "/etc/nginx/sites-enabled/$DOMAIN.conf"
    ln -sf "/etc/nginx/sites-available/$DOMAIN.conf" "/etc/nginx/sites-enabled/$DOMAIN.conf"

    install -d -o root -g root -m 0755 "/etc/letsencrypt/renewal-hooks/deploy"
    install -o root -g root -m 0755 "$APP_ROOT/infra/certbot/deploy-hooks/20-solarsage-reload-nginx" "/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"
    install -o root -g root -m 0644 "$APP_ROOT/infra/fail2ban/jail.d/solarsage-sshd.local" "/etc/fail2ban/jail.d/solarsage-sshd.local"

    # Remove default site enabled and bootstrap files if they exist
    rm -f "/etc/nginx/sites-enabled/default"
    rm -f "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf"
    rm -f "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf"

    # Validate Nginx candidate config
    if ! nginx -t >/dev/null 2>&1; then
      echo "Error: Nginx candidate config failed validation." >&2
      exit 1
    fi
    systemctl reload nginx.service

    # Validate Fail2ban candidate config
    if ! fail2ban-client -d >/dev/null 2>&1; then
      echo "Error: Fail2ban candidate config failed validation." >&2
      exit 1
    fi
    systemctl restart fail2ban

    # 8. systemctl daemon-reload
    systemctl daemon-reload

    # 9. Disable and stop legacy units
    local LEGACY_UNITS=("solarsage.service" "solarsage-frontend-preview-3001.service")
    for unit in "${LEGACY_UNITS[@]}"; do
      if systemctl list-unit-files "$unit" >/dev/null 2>&1; then
        systemctl stop "$unit" || true
        systemctl disable "$unit" || true
      fi
    done

    # 10. Enable the canonical daily backup timer only (installed orchestrator).
    local APP_UNITS=(
      "solarsage-backup.timer"
    )
    for unit in "${APP_UNITS[@]}"; do
      systemctl enable "$unit"
    done

    # Compose owns app ports 8000/3002/18091. Disable pre-existing systemd app
    # units WITHOUT --now (metadata-only: no stop, no downtime) so a repeated
    # host-prepare after cutover never restores autostart. The actual stop is a
    # separate manual one-time cutover step ordered by the owner immediately
    # before the first Compose deploy.
    local COMPOSE_OWNED_UNITS=(
      "solarsage-sidecar.service"
      "solarsage-api.service"
      "solarsage-frontend.service"
    )
    for unit in "${COMPOSE_OWNED_UNITS[@]}"; do
      if systemctl list-unit-files "$unit" >/dev/null 2>&1; then
        systemctl disable "$unit" || true
      fi
    done

    # The old backup-maintenance path is parked: never enabled/started here.
    local PARKED_UNITS=(
      "solarsage-backup-maintenance.timer"
      "solarsage-backup-maintenance.service"
    )
    for unit in "${PARKED_UNITS[@]}"; do
      if systemctl list-unit-files "$unit" >/dev/null 2>&1; then
        systemctl disable "$unit" || true
      fi
    done

    # Enable and start/reload certbot.timer (timer state not rolled back on failure)
    systemctl enable certbot.timer
    systemctl start certbot.timer

    # Enable and start/reload the canonical daily backup timer only.
    systemctl enable solarsage-backup.timer
    systemctl start solarsage-backup.timer

    # 11. Enable and start/reload only solarsage-db.service
    systemctl enable solarsage-db.service
    if [ "$(systemctl is-active solarsage-db.service)" = "active" ]; then
      systemctl reload solarsage-db.service
    else
      systemctl start solarsage-db.service
    fi

    # Wait loop (hard health failure)
    local db_healthy=0
    for i in {1..30}; do
      if [ "$(systemctl is-active solarsage-db.service)" = "active" ]; then
        local HEALTH_STATUS
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' solarsage-db 2>/dev/null || echo "unknown")
        if [ "$HEALTH_STATUS" = "healthy" ]; then
          db_healthy=1
          break
        fi
      fi
      sleep 2
    done
    if [ "$db_healthy" -ne 1 ]; then
      echo "Error: solarsage-db.service started, but health checks timed out. Hard exit." >&2
      exit 1
    fi

    # 12. Verification without marker first
    # Note: --apply stage verification uses check_marker=0 which invokes offsite preflight check
    if ! verify_host_state 0 --preflight; then
      echo "Error: Host state verification failed before writing fingerprint marker." >&2
      exit 1
    fi

    # Compute new fingerprint and write it atomically
    local FP_VAL TMP_FP
    FP_VAL=$("$APP_ROOT/scripts/deploy/prod-infra-fingerprint.sh")
    TMP_FP=$(mktemp /etc/solarsage/infra-fingerprint.XXXXXX)
    echo "$FP_VAL" > "$TMP_FP"
    chown root:root "$TMP_FP"
    chmod 0644 "$TMP_FP"
    mv "$TMP_FP" "$FINGERPRINT_FILE"

    # 13. Run full verification including marker equality.
    if ! verify_host_state 1 --preflight; then
      echo "Error: Host verification failed after writing fingerprint marker." >&2
      exit 1
    fi

    # Mark transaction committed successfully
    TRANSACTION_COMMITTED=1
    echo "HOST PREPARE APPLY SUCCESS"
    exit 0
  fi
}

main "$@"
# END_BLOCK: HOST_PREPARE
