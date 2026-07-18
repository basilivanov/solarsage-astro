#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_OS_BOOTSTRAP — Idempotent Ubuntu 24.04 OS bootstrap
# ROLE: Configures base system dependencies, security packages, Docker, Node.js 22, pnpm, Fail2ban, and UFW.
# DEPENDENCIES: bash, flock, getent, stat, install, runuser, systemctl, nginx, certbot, ufw, fail2ban-client, timedatectl, dpkg
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-OS-BOOTSTRAP
# purpose: Setup and verify OS-level requirements for production.
# owns:
#   - scripts/deploy/prod-os-bootstrap.sh
# inputs:
#   - --check : read-only system audit
#   - --apply : system packages/services configuration
# outputs:
#   - exit 0 on success, non-zero on failure
# dependencies: none
# side_effects:
#   - Installs system packages (apt)
#   - Adds repositories (Docker, NodeSource)
#   - Configures and enables systemd units
#   - Configures UFW and Fail2ban rules
# emitted_logs: none
# invariants:
#   - Must run as root.
#   - Single non-blocking lock.
#   - umask 027.
#   - Never start/restart/stop api, sidecar, frontend.
#   - astro is never in the docker group; apply converges membership by removal
#     (idempotent, fresh users unaffected; SSH reconnect required for
#     supplementary group refresh).
# failure_policy: fails non-zero on any check or configuration error.
# END_MODULE_CONTRACT: M-PROD-OS-BOOTSTRAP

# START_MODULE_MAP: M-PROD-OS-BOOTSTRAP
# public_entrypoints:
#   - main
# semantic_blocks:
#   - OS_BOOTSTRAP: preflight, package setup, security config, verification
# END_MODULE_MAP: M-PROD-OS-BOOTSTRAP

# START_BLOCK: OS_BOOTSTRAP
set -euo pipefail
umask 027

# 1. Argument validation must happen before root check
# strictly: --check or --apply
if [ "$#" -ne 1 ] || { [ "$1" != "--check" ] && [ "$1" != "--apply" ]; }; then
  echo "Usage: $0 {--check|--apply}" >&2
  exit 2
fi
MODE="$1"

# 2. Root check
if [ "$EUID" -ne 0 ]; then
  echo "Error: this script must be run as root." >&2
  exit 1
fi

# 3. Compute SCRIPT_DIR and REPO_ROOT before functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

APP_USER="astro"
APP_GROUP="astro"
EXPECTED_OS_VER="24.04"
EXPECTED_OS_CODENAME="noble"
EXPECTED_ARCH="amd64"

# Helper to check command existence
cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Verification function used by --check and at the end of --apply
verify_os_state() {
  local ver_errors=0
  report_ver_error() {
    echo "Verification Error: $1" >&2
    ver_errors=$((ver_errors + 1))
  }

  # 1. Exact Ubuntu 24.04 noble amd64
  if [ -f /etc/os-release ]; then
    local OS_VER OS_NAME OS_CODENAME
    OS_VER=$( (source /etc/os-release && echo "${VERSION_ID:-}") )
    OS_NAME=$( (source /etc/os-release && echo "${NAME:-}") )
    OS_CODENAME=$( (source /etc/os-release && echo "${VERSION_CODENAME:-}") )
    if [ "$OS_VER" != "$EXPECTED_OS_VER" ] || [[ ! "$OS_NAME" =~ Ubuntu ]] || [ "$OS_CODENAME" != "$EXPECTED_OS_CODENAME" ]; then
      report_ver_error "OS is not Ubuntu 24.04 noble (detected $OS_NAME $OS_VER $OS_CODENAME)"
    fi
  else
    report_ver_error "/etc/os-release not found"
  fi

  local ACTUAL_ARCH
  ACTUAL_ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
  if [ "$ACTUAL_ARCH" != "$EXPECTED_ARCH" ]; then
    report_ver_error "Architecture is not amd64 (detected $ACTUAL_ARCH)"
  fi

  # 2. User/group astro exist and meet contracts
  if ! getent passwd "$APP_USER" >/dev/null; then
    report_ver_error "User '$APP_USER' does not exist"
  else
    local USER_SHELL USER_HOME PRIMARY_GROUP
    USER_SHELL=$(getent passwd "$APP_USER" | cut -d: -f7)
    USER_HOME=$(getent passwd "$APP_USER" | cut -d: -f6)
    PRIMARY_GROUP=$(id -gn "$APP_USER")

    if [ "$PRIMARY_GROUP" != "$APP_GROUP" ]; then
      report_ver_error "User '$APP_USER' primary group is $PRIMARY_GROUP, expected $APP_GROUP"
    fi
    if [ "$USER_SHELL" != "/bin/bash" ]; then
      report_ver_error "User '$APP_USER' shell is $USER_SHELL, expected /bin/bash"
    fi
    if [ "$USER_HOME" != "/home/astro" ]; then
      report_ver_error "User '$APP_USER' home is $USER_HOME, expected /home/astro"
    fi
    if [ -e "$USER_HOME" ]; then
      if [ -L "$USER_HOME" ] || [ ! -d "$USER_HOME" ]; then
        report_ver_error "Home directory $USER_HOME exists but is a symlink or not a directory"
      else
        local home_owner home_mode
        home_owner=$(stat -c "%U:%G" "$USER_HOME")
        home_mode=$(stat -c "%a" "$USER_HOME")
        if [ "$home_owner" != "$APP_USER:$APP_GROUP" ]; then
          report_ver_error "Home directory ownership is $home_owner, expected $APP_USER:$APP_GROUP"
        fi
        # Mode check: mode must not be wider than 0750
        if [ "${home_mode:1:1}" -gt 5 ] || [ "${home_mode:2:1}" -gt 0 ]; then
          report_ver_error "Home directory permissions are too wide: $home_mode (expected not wider than 0750)"
        fi
      fi
    else
      report_ver_error "Home directory $USER_HOME does not exist"
    fi
  fi

  if ! getent group "$APP_GROUP" >/dev/null; then
    report_ver_error "Group '$APP_GROUP' does not exist"
  fi

  # Verify astro is NOT in the docker group
  if getent group docker >/dev/null; then
    if id -nG "$APP_USER" | grep -qw docker; then
      report_ver_error "User '$APP_USER' is in the 'docker' group (forbidden root-equivalent privilege)"
    fi
  fi

  # 3. Commands exist
  local REQUIRED_CMDS=(git curl cmp sha256sum python3.12 node corepack pnpm docker nginx certbot pg_dump pg_isready systemctl visudo openssl runuser install flock getent stat systemd-analyze ufw fail2ban-client timedatectl dpkg restic ssh timeout wc tail od gpasswd)
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! cmd_exists "$cmd"; then
      report_ver_error "Required command '$cmd' is missing"
    fi
  done

  # 4. Node major 22, pnpm 10.32.1, python3.12
  if cmd_exists node; then
    local NODE_VER NODE_MAJOR
    NODE_VER=$(node -v | tr -d 'v')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" != "22" ]; then
      report_ver_error "Node major version is $NODE_MAJOR, expected 22"
    fi
  fi

  if cmd_exists pnpm; then
    # Validate pnpm version as root
    local PNPM_VER_ROOT
    PNPM_VER_ROOT=$(pnpm -v 2>/dev/null || echo "none")
    if [ "$PNPM_VER_ROOT" != "10.32.1" ]; then
      report_ver_error "pnpm version as root is $PNPM_VER_ROOT, expected 10.32.1"
    fi
    # Validate pnpm version as astro user with deterministic PATH
    if cmd_exists runuser && getent passwd "$APP_USER" >/dev/null; then
      local PNPM_VER_ASTRO
      PNPM_VER_ASTRO=$(runuser -u "$APP_USER" -- env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" pnpm -v 2>/dev/null || echo "none")
      if [ "$PNPM_VER_ASTRO" != "10.32.1" ]; then
        report_ver_error "pnpm version as user '$APP_USER' is $PNPM_VER_ASTRO, expected 10.32.1"
      fi
    fi
  fi

  if cmd_exists python3.12; then
    local PY_VER
    PY_VER=$(python3.12 --version 2>&1 | cut -d' ' -f2)
    if [[ ! "$PY_VER" =~ ^3\.12 ]]; then
      report_ver_error "python3.12 version is $PY_VER, expected 3.12"
    fi
  fi

  # 5. docker compose validation
  if cmd_exists docker; then
    if ! docker compose version >/dev/null 2>&1; then
      report_ver_error "'docker compose version' failed"
    fi
  fi

  # 6. Systemd units exist and are enabled/active
  # unit existence check via LoadState
  local SYSTEMD_UNITS=(docker.service nginx.service fail2ban.service certbot.timer unattended-upgrades.service)
  for unit in "${SYSTEMD_UNITS[@]}"; do
    local load_state
    if load_state=$(systemctl show -p LoadState --value "$unit" 2>/dev/null); then :; else load_state="not-found"; fi
    if [ "$load_state" != "loaded" ]; then
      report_ver_error "Systemd unit '$unit' LoadState is $load_state, expected loaded"
    else
      if ! systemctl is-enabled "$unit" >/dev/null 2>&1; then
        report_ver_error "Systemd unit '$unit' is not enabled"
      fi
      if [ "$unit" = "unattended-upgrades.service" ]; then
        # unattended-upgrades is active or exited/oneshot
        local ua_state
        if ua_state=$(systemctl is-active "$unit" 2>/dev/null); then :; else ua_state=inactive; fi
        if [ "$ua_state" != "active" ] && [ "$ua_state" != "inactive" ]; then
          report_ver_error "Systemd unit '$unit' state is $ua_state, expected active or inactive (oneshot)"
        fi
      else
        if [ "$(systemctl is-active "$unit")" != "active" ]; then
          report_ver_error "Systemd unit '$unit' is not active"
        fi
      fi
    fi
  done

  # 7. fail2ban-client status sshd succeeds
  if cmd_exists fail2ban-client; then
    if ! fail2ban-client status sshd >/dev/null 2>&1; then
      report_ver_error "fail2ban sshd jail status check failed"
    fi
  fi

  # 8. UFW active, canonical rules check
  if cmd_exists ufw; then
    export LC_ALL=C
    local ufw_status
    ufw_status=$(ufw status verbose 2>/dev/null || true)
    if [[ ! "$ufw_status" =~ "Status: active" ]]; then
      report_ver_error "UFW is not active"
    else
      if ! echo "$ufw_status" | grep -qE '^Default:\s+deny\s+\(incoming\)'; then
        report_ver_error "UFW default incoming policy is not deny"
      fi
      if ! echo "$ufw_status" | grep -qE 'allow\s+\(outgoing\)'; then
        report_ver_error "UFW default outgoing policy is not allow"
      fi

      # Parse rules deterministically via "ufw show added"
      local added_rules
      added_rules=$(ufw show added 2>/dev/null || true)

      # We require EXACTLY:
      # - ufw allow 22/tcp
      # - ufw allow 80/tcp
      # - ufw allow 443/tcp
      while IFS= read -r rule; do
        [ -z "$rule" ] && continue
        [[ "$rule" =~ ^Added\ user\ rules ]] && continue
        local norm_rule
        norm_rule=$(echo "$rule" | awk '{$1=$1;print}')
        if [[ "$norm_rule" != "ufw allow 22/tcp" ]] && \
           [[ "$norm_rule" != "ufw allow 80/tcp" ]] && \
           [[ "$norm_rule" != "ufw allow 443/tcp" ]]; then
          report_ver_error "UFW contains unexpected rule: '$norm_rule'"
        fi
      done < <(echo "$added_rules")

      # Verify required rules are present
      if ! echo "$added_rules" | grep -qE '^ufw allow 22/tcp'; then
        report_ver_error "UFW is missing required rule: 'ufw allow 22/tcp'"
      fi
      if ! echo "$added_rules" | grep -qE '^ufw allow 80/tcp'; then
        report_ver_error "UFW is missing required rule: 'ufw allow 80/tcp'"
      fi
      if ! echo "$added_rules" | grep -qE '^ufw allow 443/tcp'; then
        report_ver_error "UFW is missing required rule: 'ufw allow 443/tcp'"
      fi
    fi
  fi

  # 9. NTP synchronized
  if cmd_exists timedatectl; then
    local ntp_sync
    ntp_sync=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo "no")
    if [ "$ntp_sync" != "yes" ]; then
      report_ver_error "NTP is not synchronized (timedatectl show -p NTPSynchronized --value is not yes)"
    fi
  fi

  if [ "$ver_errors" -gt 0 ]; then
    return 1
  fi
  return 0
}

# Preflight checks (Repo templates, OS, codename, architecture before any mutation)
os_preflight() {
  local pre_errors=0
  report_pre_error() {
    echo "Preflight Error: $1" >&2
    pre_errors=$((pre_errors + 1))
  }

  # 1. Exact Ubuntu 24.04 noble amd64
  if [ -f /etc/os-release ]; then
    local OS_VER OS_NAME OS_CODENAME
    OS_VER=$( (source /etc/os-release && echo "${VERSION_ID:-}") )
    OS_NAME=$( (source /etc/os-release && echo "${NAME:-}") )
    OS_CODENAME=$( (source /etc/os-release && echo "${VERSION_CODENAME:-}") )
    if [ "$OS_VER" != "$EXPECTED_OS_VER" ] || [[ ! "$OS_NAME" =~ Ubuntu ]] || [ "$OS_CODENAME" != "$EXPECTED_OS_CODENAME" ]; then
      report_pre_error "OS is not Ubuntu 24.04 noble (detected $OS_NAME $OS_VER $OS_CODENAME)"
    fi
  else
    report_pre_error "/etc/os-release not found"
  fi

  local ACTUAL_ARCH
  ACTUAL_ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
  if [ "$ACTUAL_ARCH" != "$EXPECTED_ARCH" ]; then
    report_pre_error "Architecture is not amd64 (detected $ACTUAL_ARCH)"
  fi

  # 2. Fail2ban template check
  local JAIL_TEMPLATE="$REPO_ROOT/infra/fail2ban/jail.d/solarsage-sshd.local"
  if [ ! -e "$JAIL_TEMPLATE" ] || [ -L "$JAIL_TEMPLATE" ] || [ ! -f "$JAIL_TEMPLATE" ]; then
    report_pre_error "Fail2ban template $JAIL_TEMPLATE is missing, is a symlink, or is not a regular file"
  fi

  if [ "$pre_errors" -gt 0 ]; then
    echo "Error: OS preflight checks failed." >&2
    exit 1
  fi
}

# Lock file under root-owned /run
LOCKFILE="/run/solarsage-os-bootstrap.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "Error: another os-bootstrap instance is running." >&2
  exit 1
fi

# Named cleanup function for traps
TMP_DOCKER_KEY=""
TMP_NODESOURCE_KEY=""
TMP_DOCKER_SOURCE=""
TMP_NODESOURCE_SOURCE=""
TMP_DEARMORED_DIR=""

os_cleanup() {
  rm -f "${TMP_DOCKER_KEY:-}" "${TMP_NODESOURCE_KEY:-}" "${TMP_DOCKER_SOURCE:-}" "${TMP_NODESOURCE_SOURCE:-}" 2>/dev/null || true
  if [ -n "${TMP_DEARMORED_DIR:-}" ] && [ -d "$TMP_DEARMORED_DIR" ] && [ ! -L "$TMP_DEARMORED_DIR" ]; then
    rm -rf "$TMP_DEARMORED_DIR"
  fi
}

on_os_exit() {
  local exit_status=$?
  trap - EXIT INT TERM
  os_cleanup
  exit "$exit_status"
}

on_os_int() {
  trap - INT TERM
  exit 130
}

on_os_term() {
  trap - INT TERM
  exit 143
}

apply_os_state() {
  # Setup traps for cleanup (no business logic in traps, only signal delegation and simple exit)
  trap on_os_exit EXIT
  trap on_os_int INT
  trap on_os_term TERM

  # 1. User/group creation/verification
  if getent passwd "$APP_USER" >/dev/null; then
    # Verify existing user doesn't contradict canon
    local USER_SHELL USER_HOME PRIMARY_GROUP
    USER_SHELL=$(getent passwd "$APP_USER" | cut -d: -f7)
    USER_HOME=$(getent passwd "$APP_USER" | cut -d: -f6)
    PRIMARY_GROUP=$(id -gn "$APP_USER")
    if [ "$PRIMARY_GROUP" != "$APP_GROUP" ] || [ "$USER_SHELL" != "/bin/bash" ] || [ "$USER_HOME" != "/home/astro" ]; then
      echo "Error: Existing user '$APP_USER' violates canonical requirements (home: $USER_HOME, shell: $USER_SHELL, primary group: $PRIMARY_GROUP)" >&2
      exit 1
    fi
    if [ -e "$USER_HOME" ]; then
      if [ -L "$USER_HOME" ] || [ ! -d "$USER_HOME" ]; then
        echo "Error: Home directory $USER_HOME exists but is a symlink or not a directory." >&2
        exit 1
      fi
    fi
  else
    # Create group first if missing
    if ! getent group "$APP_GROUP" >/dev/null; then
      groupadd "$APP_GROUP"
    fi
    # Create user
    useradd -g "$APP_GROUP" -m -d "/home/astro" -s "/bin/bash" -p '!' "$APP_USER"
  fi

  # Secure home directory permissions (must be real directory, checked above)
  chmod 0750 "/home/astro"
  chown "$APP_USER:$APP_GROUP" "/home/astro"

  # Converge docker group membership: astro must never hold the root-equivalent
  # docker group. Removal is root-only and idempotent; fresh users are
  # unaffected. No Docker deploy privilege is ever granted to astro.
  if getent group docker >/dev/null && id -nG "$APP_USER" | grep -qw docker; then
    gpasswd -d "$APP_USER" docker
    echo "Removed user '$APP_USER' from the 'docker' group. Reconnect the SSH session for supplementary groups to refresh."
  fi

  # 2. Noninteractive apt update & base package install
  export DEBIAN_FRONTEND=noninteractive
  apt-get update

  # Install base packages
  apt-get install -y ca-certificates curl git gnupg openssl sudo nginx certbot python3.12 python3.12-venv python3-pip postgresql-client-16 fail2ban ufw unattended-upgrades restic openssh-client

  # 3. Docker Repository & Installation (Atomic)
  local DOCKER_OK=0
  if cmd_exists docker && docker compose version >/dev/null 2>&1; then
    DOCKER_OK=1
  fi

  if [ "$DOCKER_OK" -eq 0 ]; then
    echo "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    TMP_DOCKER_KEY=$(mktemp "/tmp/docker-key.XXXXXX")
    if curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o "$TMP_DOCKER_KEY" && [ -s "$TMP_DOCKER_KEY" ]; then
      # Docker key: canonical /etc/apt/keyrings/docker.asc, official ASCII key, root:root 0644
      install -o root -g root -m 0644 "$TMP_DOCKER_KEY" /etc/apt/keyrings/docker.asc

      TMP_DOCKER_SOURCE=$(mktemp "/tmp/docker-source.XXXXXX")
      echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > "$TMP_DOCKER_SOURCE"
      install -o root -g root -m 0644 "$TMP_DOCKER_SOURCE" /etc/apt/sources.list.d/docker.list

      apt-get update
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
      echo "Error: Failed to download Docker GPG key" >&2
      exit 1
    fi
  fi

  # 4. NodeSource Node 22 setup (Atomic dearmor fix)
  local NODE_OK=0
  if cmd_exists node && [ "$(node -v | tr -d 'v' | cut -d. -f1)" = "22" ]; then
    NODE_OK=1
  fi

  if [ "$NODE_OK" -eq 0 ]; then
    echo "Installing Node.js 22..."
    install -m 0755 -d /etc/apt/keyrings
    TMP_NODESOURCE_KEY=$(mktemp "/tmp/nodesource-key.XXXXXX")
    if curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o "$TMP_NODESOURCE_KEY" && [ -s "$TMP_NODESOURCE_KEY" ]; then
      # NodeSource key: /etc/apt/keyrings/nodesource.gpg, dearmor
      # Create root-only temp directory
      TMP_DEARMORED_DIR=$(mktemp -d "/tmp/nodesource-gpg-XXXXXX")
      chmod 0700 "$TMP_DEARMORED_DIR"

      local gpg_out="$TMP_DEARMORED_DIR/nodesource.gpg"
      if ! gpg --batch --yes --dearmor --output "$gpg_out" < "$TMP_NODESOURCE_KEY"; then
        echo "Error: failed to dearmor NodeSource GPG key" >&2
        exit 1
      fi

      # Verify non-empty regular output
      if [ ! -f "$gpg_out" ] || [ -L "$gpg_out" ] || [ ! -s "$gpg_out" ]; then
        echo "Error: dearmored NodeSource key is missing, empty, or a symlink" >&2
        exit 1
      fi

      # Install canonical key
      install -o root -g root -m 0644 "$gpg_out" /etc/apt/keyrings/nodesource.gpg

      TMP_NODESOURCE_SOURCE=$(mktemp "/tmp/nodesource-source.XXXXXX")
      echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > "$TMP_NODESOURCE_SOURCE"
      install -o root -g root -m 0644 "$TMP_NODESOURCE_SOURCE" /etc/apt/sources.list.d/nodesource.list

      apt-get update
      apt-get install -y nodejs
    else
      echo "Error: Failed to download NodeSource GPG key" >&2
      exit 1
    fi
  fi

  # 5. Corepack & exact pnpm 10.32.1
  echo "Configuring pnpm 10.32.1 via Corepack..."
  corepack enable
  corepack prepare pnpm@10.32.1 --activate

  # 6. Fail2ban jail installation
  echo "Installing Fail2ban jail configuration..."
  local JAIL_TEMPLATE="$REPO_ROOT/infra/fail2ban/jail.d/solarsage-sshd.local"
  install -o root -g root -m 0644 "$JAIL_TEMPLATE" "/etc/fail2ban/jail.d/solarsage-sshd.local"

  # Validate fail2ban config before restart
  if ! fail2ban-client -d >/dev/null 2>&1; then
    echo "Error: Fail2ban configuration validation failed" >&2
    exit 1
  fi
  systemctl restart fail2ban

  # 7. UFW rules configuration
  echo "Configuring UFW..."
  if ufw show added 2>/dev/null | grep -qE '^ufw allow 443$'; then
    ufw --force delete allow 443
  fi

  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable

  # 8. Enable and start basic units
  systemctl enable docker
  systemctl start docker
  systemctl enable nginx
  systemctl start nginx
  systemctl enable certbot.timer
  systemctl start certbot.timer
  systemctl enable unattended-upgrades
  systemctl start unattended-upgrades || true

  # Run final verification
  if verify_os_state; then
    echo "OS BOOTSTRAP APPLY SUCCESS"
    exit 0
  else
    echo "Error: OS bootstrap verification failed after apply." >&2
    exit 1
  fi
}

# Run preflight checks before any mutation
os_preflight

if [ "$MODE" = "--check" ]; then
  if verify_os_state; then
    echo "OS BOOTSTRAP CHECK PASS"
    exit 0
  else
    echo "Error: OS bootstrap verification checks failed." >&2
    exit 1
  fi
fi

if [ "$MODE" = "--apply" ]; then
  apply_os_state
fi
# END_BLOCK: OS_BOOTSTRAP
