#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_CERT_PREPARE — ACME Let's Encrypt bootstrap and Nginx TLS deployment
# ROLE: Secures domain TLS certificates and configures Nginx HTTPS.
# DEPENDENCIES: scripts/deploy/lib/prod-path-transaction.sh, nginx, certbot, openssl, curl, getent, install, systemctl, cmp, readlink, mktemp, flock, awk, sort, wc, dpkg
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-CERT-PREPARE
# purpose: Securely request and configure SSL certificates for Nginx.
# owns:
#   - scripts/deploy/prod-cert-prepare.sh
# inputs:
#   - --check : read-only check of certificate state and Nginx config
#   - --apply : obtain/configure certificates and configure Nginx
#   - --email <email> : option to provide email for new certificate registration
# outputs:
#   - exit 0 on success, non-zero on failure
# dependencies: none
# side_effects:
#   - Invokes certbot to issue certificates
#   - Modifies Nginx configs in /etc/nginx/sites-available and sites-enabled
#   - Reloads Nginx service
# emitted_logs: none
# invariants:
#   - Must run as root.
#   - Single non-blocking lock.
#   - umask 027.
#   - DNS A record must be exactly 157.22.192.242.
#   - Never start/restart/stop api, sidecar, frontend.
# failure_policy: fails non-zero on any verification or configuration failure, performs rollback on error.
# END_MODULE_CONTRACT: M-PROD-CERT-PREPARE

# START_MODULE_MAP: M-PROD-CERT-PREPARE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - CERT_PREPARE: CLI parsing, preflight, state capture, rollback, verification, execution
# END_MODULE_MAP: M-PROD-CERT-PREPARE

# START_BLOCK: CERT_PREPARE
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

# Domain & IP constraints
DOMAIN="astro.vasiliy-ivanov.ru"
EXPECTED_IP="157.22.192.242"
ACME_WEBROOT="/var/www/letsencrypt"
CERT_FRESHNESS_THRESHOLD=1209600 # 14 days in seconds

# Helper to check command existence
cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Email validation
validate_email() {
  local email="$1"
  # One line, no whitespace/control chars, exactly one @, non-empty local/domain parts
  # Check for ASCII control chars (0x00-0x1f, 0x7f) and whitespace
  if [[ "$email" =~ [[:space:]] ]]; then return 1; fi
  if [[ "$email" =~ [[:cntrl:]] ]]; then return 1; fi

  local parts
  IFS='@' read -ra parts <<< "$email"
  if [ "${#parts[@]}" -ne 2 ]; then return 1; fi
  if [ -z "${parts[0]}" ] || [ -z "${parts[1]}" ]; then return 1; fi
  return 0
}

# DNS A record resolution check
check_dns_a_record() {
  local DNS_IPS=()
  if cmd_exists getent; then
    # getent ahost returns multiple lines for IPv4/IPv6, filter for exact IPv4
    # Format: <ip> STREAM <host>
    while IFS= read -r line; do
      local ip
      ip=$(echo "$line" | awk '{print $1}')
      if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        DNS_IPS+=("$ip")
      fi
    done < <(getent ahosts "$DOMAIN" 2>/dev/null || true)
  fi

  if [ "${#DNS_IPS[@]}" -eq 0 ]; then
    echo "DNS A record for $DOMAIN did not resolve" >&2
    return 1
  else
    # Unique and sort
    local UNIQUE_IPS
    UNIQUE_IPS=$(printf '%s\n' "${DNS_IPS[@]}" | sort -u)
    local NUM_UNIQUE
    NUM_UNIQUE=$(echo "$UNIQUE_IPS" | wc -l)
    if [ "$NUM_UNIQUE" -ne 1 ] || [ "$UNIQUE_IPS" != "$EXPECTED_IP" ]; then
      echo "DNS A record resolves to unexpected IP(s): $UNIQUE_IPS (expected exact $EXPECTED_IP)" >&2
      return 1
    fi
  fi
  return 0
}

# Common Preflight (before any mutation)
preflight() {
  local pre_errors=0
  report_pre_error() {
    echo "Preflight Error: $1" >&2
    pre_errors=$((pre_errors + 1))
  }

  # Exact OS/codename/arch
  if [ -f /etc/os-release ]; then
    local OS_VER OS_NAME OS_CODENAME
    OS_VER=$( (source /etc/os-release && echo "${VERSION_ID:-}") )
    OS_NAME=$( (source /etc/os-release && echo "${NAME:-}") )
    OS_CODENAME=$( (source /etc/os-release && echo "${VERSION_CODENAME:-}") )
    if [ "$OS_VER" != "24.04" ] || [[ ! "$OS_NAME" =~ Ubuntu ]] || [ "$OS_CODENAME" != "noble" ]; then
      report_pre_error "OS is not Ubuntu 24.04 noble (detected $OS_NAME $OS_VER $OS_CODENAME)"
    fi
  else
    report_pre_error "/etc/os-release not found"
  fi

  local ACTUAL_ARCH
  ACTUAL_ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
  if [ "$ACTUAL_ARCH" != "amd64" ]; then
    report_pre_error "Architecture is not amd64 (detected $ACTUAL_ARCH)"
  fi

  # Required repo files exist as regular files (not symlinks in repo)
  local REPO_FILES=(
    "infra/nginx/00-solarsage-default-reject.conf"
    "infra/nginx/astro-acme-bootstrap.conf"
    "infra/nginx/astro.vasiliy-ivanov.ru.conf"
    "infra/certbot/deploy-hooks/20-solarsage-reload-nginx"
  )
  for r_file in "${REPO_FILES[@]}"; do
    local f_path="$REPO_ROOT/$r_file"
    if [ ! -f "$f_path" ] || [ -L "$f_path" ]; then
      report_pre_error "Repository template file '$r_file' is missing or is a symlink"
    fi
  done

  # Required commands exist
  local REQUIRED_CMDS=(nginx certbot openssl curl getent install systemctl cmp readlink mktemp flock awk sort wc dpkg mv rm ln chown chmod dirname)
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! cmd_exists "$cmd"; then
      report_pre_error "Required command '$cmd' is missing"
    fi
  done

  # DNS A record check
  if ! check_dns_a_record; then
    report_pre_error "DNS A record validation failed"
  fi

  if [ "$pre_errors" -gt 0 ]; then
    echo "Error: Preflight checks failed with $pre_errors error(s)." >&2
    exit 1
  fi
}

# Validate existing certificate freshness and SAN
validate_existing_cert() {
  local cert_path="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
  local key_path="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

  # The targets after resolution must be readable regular files
  if [ ! -e "$cert_path" ] || [ ! -e "$key_path" ]; then
    return 1
  fi

  local resolved_cert resolved_key
  resolved_cert=$(readlink -f "$cert_path")
  resolved_key=$(readlink -f "$key_path")

  if [ ! -f "$resolved_cert" ] || [ -L "$resolved_cert" ] || [ ! -r "$resolved_cert" ]; then
    return 1
  fi
  if [ ! -f "$resolved_key" ] || [ -L "$resolved_key" ] || [ ! -r "$resolved_key" ]; then
    return 1
  fi

  # Verify hostname via subjectAltName exact match (no substring regex)
  if ! openssl x509 -noout -checkhost "$DOMAIN" -in "$resolved_cert" >/dev/null 2>&1; then
    return 1
  fi

  # Verify freshness (not expiring within 14 days)
  if ! openssl x509 -noout -checkend "$CERT_FRESHNESS_THRESHOLD" -in "$resolved_cert" >/dev/null 2>&1; then
    return 1
  fi

  return 0
}

# State Verification (used by --check and at the end of --apply)
verify_cert_state() {
  local ver_errors=0
  report_ver_error() {
    echo "Verification Error: $1" >&2
    ver_errors=$((ver_errors + 1))
  }

  # 1. Certificate validation
  if ! validate_existing_cert; then
    report_ver_error "SSL Certificate for $DOMAIN is missing, expired, or invalid (< 14 days left)"
  fi

  # 2. default reject config byte-equal repo template, root:root 0644, regular, not symlink
  local reject_live="/etc/nginx/conf.d/00-solarsage-default-reject.conf"
  if [ ! -e "$reject_live" ] || [ -L "$reject_live" ] || [ ! -f "$reject_live" ]; then
    report_ver_error "$reject_live is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$REPO_ROOT/infra/nginx/00-solarsage-default-reject.conf" "$reject_live"; then
      report_ver_error "$reject_live differs from repository template"
    fi
    local r_info
    r_info=$(stat -c "%U:%G:%a" "$reject_live")
    if [ "$r_info" != "root:root:644" ]; then
      report_ver_error "$reject_live ownership/mode is $r_info, expected root:root:644"
    fi
  fi

  # 3. final Nginx config byte-equal repo template, root:root 0644, regular, not symlink
  local final_avail="/etc/nginx/sites-available/$DOMAIN.conf"
  if [ ! -e "$final_avail" ] || [ -L "$final_avail" ] || [ ! -f "$final_avail" ]; then
    report_ver_error "$final_avail is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$REPO_ROOT/infra/nginx/astro.vasiliy-ivanov.ru.conf" "$final_avail"; then
      report_ver_error "$final_avail differs from repository template"
    fi
    local f_info
    f_info=$(stat -c "%U:%G:%a" "$final_avail")
    if [ "$f_info" != "root:root:644" ]; then
      report_ver_error "$final_avail ownership/mode is $f_info, expected root:root:644"
    fi
  fi

  # 4. exact enabled symlink points to final site
  local final_enabled="/etc/nginx/sites-enabled/$DOMAIN.conf"
  if [ ! -L "$final_enabled" ]; then
    report_ver_error "$final_enabled is missing or is not a symlink"
  else
    local link_target
    link_target=$(readlink -f "$final_enabled")
    if [ "$link_target" != "$final_avail" ]; then
      report_ver_error "$final_enabled symlink target is $link_target, expected $final_avail"
    fi
  fi

  # 5. /etc/nginx/sites-enabled/default is absent (checked with -e || -L)
  if [ -e "/etc/nginx/sites-enabled/default" ] || [ -L "/etc/nginx/sites-enabled/default" ]; then
    report_ver_error "/etc/nginx/sites-enabled/default still exists"
  fi

  # 6. bootstrap site and its enabled symlink are absent (checked with -e || -L)
  if [ -e "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf" ] || [ -L "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf" ] || \
     [ -e "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf" ] || [ -L "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf" ]; then
    report_ver_error "Bootstrap Nginx files still exist"
  fi

  # 7. deploy hook byte-equal repo template, root:root 0755, regular, not symlink
  local hook_live="/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"
  if [ ! -e "$hook_live" ] || [ -L "$hook_live" ] || [ ! -f "$hook_live" ]; then
    report_ver_error "$hook_live is missing, is a symlink, or is not a regular file"
  else
    if ! cmp -s "$REPO_ROOT/infra/certbot/deploy-hooks/20-solarsage-reload-nginx" "$hook_live"; then
      report_ver_error "$hook_live differs from repository template"
    fi
    local h_info
    h_info=$(stat -c "%U:%G:%a" "$hook_live")
    if [ "$h_info" != "root:root:755" ]; then
      report_ver_error "$hook_live ownership/mode is $h_info, expected root:root:755"
    fi
  fi

  # 8. ACME webroot and challenge dir exist, root:root, mode 0755
  local acme_dirs=("$ACME_WEBROOT" "$ACME_WEBROOT/.well-known" "$ACME_WEBROOT/.well-known/acme-challenge")
  for dir in "${acme_dirs[@]}"; do
    if [ ! -d "$dir" ] || [ -L "$dir" ]; then
      report_ver_error "Directory $dir is missing or is a symlink"
    else
      local d_info
      d_info=$(stat -c "%U:%G:%a" "$dir")
      if [ "$d_info" != "root:root:755" ]; then
        report_ver_error "$dir ownership/mode is $d_info, expected root:root:755"
      fi
    fi
  done

  # 9. certbot.timer enabled and active
  if ! systemctl is-enabled certbot.timer >/dev/null 2>&1; then
    report_ver_error "certbot.timer is not enabled"
  fi
  if [ "$(systemctl is-active certbot.timer)" != "active" ]; then
    report_ver_error "certbot.timer is not active"
  fi

  # 10. nginx -t is successful
  if ! nginx -t >/dev/null 2>&1; then
    report_ver_error "Nginx configuration syntax check failed"
  fi

  # 11. local TLS handshake check using bounded curl resolved to 127.0.0.1
  local curl_code=0
  local curl_out
  curl_out=$(curl --resolve "$DOMAIN:443:127.0.0.1" --connect-timeout 5 --max-time 10 -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/.well-known/acme-challenge/healthcheck" || curl_code=$?)
  if [ "$curl_code" -ne 0 ]; then
    report_ver_error "Local TLS handshake test failed with curl exit code $curl_code"
  fi

  if [ "$ver_errors" -gt 0 ]; then
    return 1
  fi
  return 0
}

# Transaction Management Variables
ROLLBACK_STARTED=0
TRANSACTION_COMMITTED=0

post_cert_restore() {
  echo "Validating and reloading restored Nginx configuration..." >&2
  if /usr/sbin/nginx -t >/dev/null 2>&1; then
    /usr/bin/systemctl reload nginx.service || true
  else
    echo "Warning: Restored Nginx configuration failed syntax validation." >&2
  fi
}

on_transaction_exit() {
  local exit_status=$?
  trap - EXIT INT TERM

  if [ "$TRANSACTION_COMMITTED" -ne 1 ]; then
    if [ "$ROLLBACK_STARTED" -ne 1 ]; then
      ROLLBACK_STARTED=1
      if prod_tx_rollback; then
        post_cert_restore
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

apply_cert_state() {
  local EMAIL="$1"
  local HAS_CERT="$2"

  # 1. Create ACME directories with canonical owner/mode 0755
  install -d -o root -g root -m 0755 "$ACME_WEBROOT"
  install -d -o root -g root -m 0755 "$ACME_WEBROOT/.well-known"
  install -d -o root -g root -m 0755 "$ACME_WEBROOT/.well-known/acme-challenge"

  # 2. Register paths for the transaction helper
  PROD_TX_PATHS["reject"]="/etc/nginx/conf.d/00-solarsage-default-reject.conf"
  PROD_TX_PATHS["bootstrap_avail"]="/etc/nginx/sites-available/$DOMAIN-bootstrap.conf"
  PROD_TX_PATHS["bootstrap_enabled"]="/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf"
  PROD_TX_PATHS["final_avail"]="/etc/nginx/sites-available/$DOMAIN.conf"
  PROD_TX_PATHS["final_enabled"]="/etc/nginx/sites-enabled/$DOMAIN.conf"
  PROD_TX_PATHS["default_enabled"]="/etc/nginx/sites-enabled/default"
  PROD_TX_PATHS["hook"]="/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"

  # 3. Capture current state
  if ! prod_tx_capture "/run"; then
    echo "Error: failed to capture path state for transaction" >&2
    exit 1
  fi

  # 4. Setup traps for exit/interrupts
  trap on_transaction_exit EXIT
  trap on_transaction_int INT
  trap on_transaction_term TERM

  # 5. Perform mutations
  # Install default reject
  install -o root -g root -m 0644 "$REPO_ROOT/infra/nginx/00-solarsage-default-reject.conf" "/etc/nginx/conf.d/00-solarsage-default-reject.conf"

  # Remove default site enabled if it exists
  rm -f "/etc/nginx/sites-enabled/default"

  # If certificate is missing/invalid, bootstrap via HTTP
  if [ "$HAS_CERT" -eq 0 ]; then
    echo "Certificate is missing/expired. Running HTTP bootstrap flow..."

    # Install bootstrap site
    install -o root -g root -m 0644 "$REPO_ROOT/infra/nginx/astro-acme-bootstrap.conf" "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf"
    ln -sf "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf" "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf"

    # Temporarily disable final site symlink if it exists to avoid nginx -t failures
    rm -f "/etc/nginx/sites-enabled/$DOMAIN.conf"

    # Validate Nginx and reload
    nginx -t >/dev/null
    systemctl reload nginx.service

    # Issue certificate via Certbot webroot
    certbot certonly --webroot --webroot-path "$ACME_WEBROOT" --domain "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive --no-eff-email --key-type ecdsa

    # Verify the newly issued certificate is valid
    if ! validate_existing_cert; then
      echo "Error: Issued certificate failed verification checks." >&2
      exit 1
    fi

    # Clean up bootstrap site
    rm -f "/etc/nginx/sites-enabled/$DOMAIN-bootstrap.conf"
    rm -f "/etc/nginx/sites-available/$DOMAIN-bootstrap.conf"
  else
    echo "Valid certificate already exists. Skipping Certbot issuance."
  fi

  # Install final site, symlink, and deploy hook
  install -o root -g root -m 0644 "$REPO_ROOT/infra/nginx/astro.vasiliy-ivanov.ru.conf" "/etc/nginx/sites-available/$DOMAIN.conf"
  ln -sf "/etc/nginx/sites-available/$DOMAIN.conf" "/etc/nginx/sites-enabled/$DOMAIN.conf"

  # Install certbot deploy hook
  install -d -o root -g root -m 0755 "/etc/letsencrypt/renewal-hooks/deploy"
  install -o root -g root -m 0755 "$REPO_ROOT/infra/certbot/deploy-hooks/20-solarsage-reload-nginx" "/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx"

  # Enable and start certbot timer (not rolled back on failure)
  systemctl enable certbot.timer
  systemctl start certbot.timer

  # Final Nginx reload
  nginx -t >/dev/null
  systemctl reload nginx.service

  # Run final verification within the transaction
  if ! verify_cert_state; then
    echo "Error: Final cert state verification failed." >&2
    exit 1
  fi

  # Mark transaction committed successfully
  TRANSACTION_COMMITTED=1
}

main() {
  local MODE=""
  local EMAIL=""

  if [ "$#" -eq 1 ]; then
    if [ "$1" = "--check" ]; then
      MODE="--check"
    elif [ "$1" = "--apply" ]; then
      MODE="--apply"
    else
      echo "Usage: $0 {--check|--apply} [--email <email>]" >&2
      exit 2
    fi
  elif [ "$#" -eq 3 ]; then
    if [ "$1" = "--apply" ] && [ "$2" = "--email" ]; then
      MODE="--apply"
      EMAIL="$3"
    else
      echo "Usage: $0 {--check|--apply} [--email <email>]" >&2
      exit 2
    fi
  else
    echo "Usage: $0 {--check|--apply} [--email <email>]" >&2
    exit 2
  fi

  # Validate email format BEFORE root check and lock
  if [ "$MODE" = "--apply" ] && [ -n "$EMAIL" ]; then
    if ! validate_email "$EMAIL"; then
      echo "Error: Invalid email address format." >&2
      exit 2
    fi
  fi

  # 2. Root check
  if [ "$EUID" -ne 0 ]; then
    echo "Error: this script must be run as root." >&2
    exit 1
  fi

  # 3. Lock file under root-owned /run
  local LOCKFILE="/run/solarsage-cert-prepare.lock"
  exec 9>"$LOCKFILE"
  if ! flock -n 9; then
    echo "Error: another cert-prepare instance is running." >&2
    exit 1
  fi

  # Run preflight
  preflight

  if [ "$MODE" = "--check" ]; then
    if verify_cert_state; then
      echo "CERT PREPARE CHECK PASS"
      exit 0
    else
      echo "Error: Cert prepare verification checks failed." >&2
      exit 1
    fi
  fi

  if [ "$MODE" = "--apply" ]; then
    local HAS_CERT=0
    if validate_existing_cert; then
      HAS_CERT=1
    fi

    if [ "$HAS_CERT" -eq 0 ] && [ -z "$EMAIL" ]; then
      echo "Error: Certificate is missing or invalid, but --email was not provided." >&2
      exit 2
    fi

    apply_cert_state "$EMAIL" "$HAS_CERT"
    echo "CERT PREPARE APPLY SUCCESS"
    exit 0
  fi
}

main "$@"
# END_BLOCK: CERT_PREPARE
