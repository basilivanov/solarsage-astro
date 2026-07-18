#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_GITHUB_ACCESS — Hardened GitHub Transport and Source Readiness
# ROLE: Manages server-side private repository SSH access and performs fail-closed checks.
# DEPENDENCIES: git, ssh-keygen, curl, stat, mktemp, rm, python3.12, timeout, wc, tail, od, sha256sum
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-GITHUB-ACCESS
# purpose: Secure private GitHub transport config and validation without deploy.
# owns:
#   - scripts/deploy/prod-github-access.sh
# inputs:
#   - --apply: Installs SSH config, host keys, and forced commands (root-only).
#   - --preflight: Safe read-only validation of paths, files, and HTTPS connectivity (astro).
#   - --check: Safe final source-readiness verification, failing if repository is public (astro).
#   - --expected-sha <sha>: With --check, compares remote refs/heads/main.
# outputs:
#   - exit 0 on success, non-zero on failure or public repository status.
# dependencies: none
# invariants:
#   - Safe output: never prints keys, tokens, or credential URLs.
#   - Reject symlinks/FIFO/directories/duplicates and unsafe modes.
#   - Atomicity: uses temp files in same directory with 0600 modes before rename.
#   - fail-closed: PUBLIC repo is an explicit warning/failure.
# failure_policy: fails non-zero on any verification, access, or status mismatch.
# END_MODULE_CONTRACT: M-PROD-GITHUB-ACCESS

# START_MODULE_MAP: M-PROD-GITHUB-ACCESS
# public_entrypoints:
#   - main
# semantic_blocks:
#   - PARSE_ARGS: validate command-line arguments
#   - COMMON_VALIDATION: check paths, types, permissions, and derive fingerprint
#   - APPLY: root-only installation of SSH config, host keys, and forced commands
#   - PREFLIGHT: safe validation of git access and HTTPS connectivity
#   - CHECK: final readiness validation against API and expected SHA
# END_MODULE_MAP: M-PROD-GITHUB-ACCESS

set -euo pipefail
umask 077

# Canonical paths
SSH_DIR="/home/astro/.ssh"
CHECKOUT_KEY="$SSH_DIR/solarsage_prod_server_ed25519"
CHECKOUT_PUB="$SSH_DIR/solarsage_prod_server_ed25519.pub"
KNOWN_HOSTS_GH="$SSH_DIR/known_hosts.github"
SSH_CONFIG="$SSH_DIR/config"
ACTIONS_PUB="/etc/solarsage/keys/github-actions-deploy.pub"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"
FORCED_WRAPPER="/usr/local/sbin/solarsage-github-deploy"
REPO_DIR="/opt/solarsage-astro"
TEMPLATE_KNOWN_HOSTS="$REPO_DIR/infra/ssh/github.com.known_hosts"

# Helper: Print usage error and exit with 2
usage_err() {
  echo "Usage: $0 {--apply|--preflight|--check} [--expected-sha <40-char-lowercase-hex>]" >&2
  exit 2
}

# Helper: Print runtime error and exit with 1
err() {
  echo "Error: $1" >&2
  exit 1
}

# Helper: Check file exists, is regular file, not a symlink, and has exact owner and mode
validate_file_security() {
  local path="$1"
  local expected_owner="$2"
  local expected_mode="$3"
  local label="$4"

  if [ ! -e "$path" ]; then
    err "$label '$path' does not exist."
  fi
  if [ -L "$path" ]; then
    err "$label '$path' is a symlink (forbidden)."
  fi
  if [ ! -f "$path" ]; then
    err "$label '$path' is not a regular file."
  fi

  local actual_owner
  actual_owner=$(stat -c "%U:%G" "$path")
  if [ "$actual_owner" != "$expected_owner" ]; then
    err "$label '$path' owner is $actual_owner, expected $expected_owner."
  fi

  local actual_mode
  actual_mode=$(stat -c "%a" "$path")
  local normalized_actual_mode="${actual_mode#0}"
  local normalized_expected_mode="${expected_mode#0}"
  if [ "$normalized_actual_mode" != "$normalized_expected_mode" ]; then
    err "$label '$path' mode is $actual_mode, expected $expected_mode."
  fi
}

# Helper: Check directory exists, not a symlink, exact owner and mode
validate_dir_security() {
  local path="$1"
  local expected_owner="$2"
  local expected_mode="$3"
  local label="$4"

  if [ ! -e "$path" ]; then
    err "$label '$path' does not exist."
  fi
  if [ -L "$path" ]; then
    err "$label '$path' is a symlink (forbidden)."
  fi
  if [ ! -d "$path" ]; then
    err "$label '$path' is not a directory."
  fi

  local actual_owner
  actual_owner=$(stat -c "%U:%G" "$path")
  if [ "$actual_owner" != "$expected_owner" ]; then
    err "$label '$path' owner is $actual_owner, expected $expected_owner."
  fi

  local actual_mode
  actual_mode=$(stat -c "%a" "$path")
  local normalized_actual_mode="${actual_mode#0}"
  local normalized_expected_mode="${expected_mode#0}"
  if [ "$normalized_actual_mode" != "$normalized_expected_mode" ]; then
    err "$label '$path' mode is $actual_mode, expected $expected_mode."
  fi
}

# Helper: Verify exact one physical line key contract
validate_exact_one_line_file() {
  local path="$1"
  local label="$2"

  local line_count
  line_count=$(wc -l < "$path" || err "Failed to read line count of '$path'.")
  if [ "$line_count" -ne 1 ]; then
    err "$label '$path' must contain exactly one physical line (has $line_count lines)."
  fi

  # Check that it ends with exactly one LF, no CR
  if [ -s "$path" ]; then
    local last_char
    last_char=$(tail -c 1 "$path" | od -An -t x1 | xargs)
    if [ "$last_char" != "0a" ]; then
      err "$label '$path' must end with a single line feed (LF)."
    fi
    if grep -q $'\r' "$path"; then
      err "$label '$path' contains carriage return (CR) characters (forbidden)."
    fi
  fi
}

# Helper: Fetch repository visibility using anonymous API
get_github_visibility_status() {
  local http_status
  local curl_rc=0
  set +e
  http_status=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 https://api.github.com/repos/basilivanov/solarsage-astro 2>/dev/null)
  curl_rc=$?
  set -e

  if [ "$curl_rc" -ne 0 ]; then
    err "GitHub API HTTPS request failed with exit code $curl_rc."
  fi

  if [[ ! "$http_status" =~ ^[0-9]{3}$ ]]; then
    err "GitHub API returned invalid HTTP status: '$http_status'."
  fi

  echo "$http_status"
}

# Helper: Run ls-remote and check for exact match of refs/heads/main
verify_ls_remote_main() {
  local remote_out
  local ls_rc=0
  set +e
  remote_out=$(timeout 15s git -C "$REPO_DIR" ls-remote --exit-code origin refs/heads/main 2>/dev/null)
  ls_rc=$?
  set -e

  if [ "$ls_rc" -ne 0 ]; then
    err "git ls-remote via SSH transport failed with exit code $ls_rc."
  fi

  # Read lines into array
  local lines=()
  while IFS= read -r line || [ -n "$line" ]; do
    if [ -n "$line" ]; then
      lines+=("$line")
    fi
  done <<< "$remote_out"

  if [ "${#lines[@]}" -ne 1 ]; then
    err "git ls-remote output has incorrect format (multiple or zero lines)."
  fi

  local single_line="${lines[0]}"
  # Must match: <40 lowercase hex><TAB>refs/heads/main
  if [[ ! "$single_line" =~ ^[0-9a-f]{40}$'\t'refs/heads/main$ ]]; then
    err "git ls-remote output has incorrect format (shape mismatch)."
  fi

  local remote_sha
  remote_sha=$(echo "$single_line" | awk '{print $1}')
  echo "$remote_sha"
}

# START_BLOCK: COMMON_VALIDATION
validate_installed_state() {
  local is_pre_apply="$1"

  # 1. SSH directory validation
  validate_dir_security "$SSH_DIR" "astro:astro" "700" ".ssh directory"

  # 2. Private checkout key validation
  validate_file_security "$CHECKOUT_KEY" "astro:astro" "600" "Private checkout key"

  # 3. Public checkout key validation
  validate_file_security "$CHECKOUT_PUB" "astro:astro" "644" "Public checkout key"
  validate_exact_one_line_file "$CHECKOUT_PUB" "Public checkout key"

  # 4. Derive public key and compare
  local derived_pub
  if ! derived_pub=$(ssh-keygen -y -P '' -f "$CHECKOUT_KEY" 2>/dev/null); then
    err "Private checkout key at '$CHECKOUT_KEY' is invalid or requires a passphrase."
  fi

  local actual_normalized
  actual_normalized=$(echo "$derived_pub" | awk '{print $1, $2}')
  local expected_normalized
  expected_normalized=$(cat "$CHECKOUT_PUB" | awk '{print $1, $2}')

  if [ "$actual_normalized" != "$expected_normalized" ]; then
    err "Derived public key from '$CHECKOUT_KEY' does not match '$CHECKOUT_PUB'."
  fi

  # Print fingerprint safely
  local fingerprint
  fingerprint=$(ssh-keygen -l -f "$CHECKOUT_KEY" | awk '{print $2}')
  echo "Verified checkout key fingerprint: $fingerprint"

  # 5. Actions public key validation
  validate_file_security "$ACTIONS_PUB" "root:root" "644" "Actions public key"
  validate_exact_one_line_file "$ACTIONS_PUB" "Actions public key"

  local actions_key_line
  if ! IFS= read -r actions_key_line < "$ACTIONS_PUB"; then
    err "Failed to read Actions public key line."
  fi
  if [[ ! "$actions_key_line" =~ ^ssh-ed25519[[:space:]]+[A-Za-z0-9+/=]+([[:space:]]+.*)?$ ]]; then
    err "Actions public key must be exactly one valid ssh-ed25519 line."
  fi

  if ! ssh-keygen -l -f "$ACTIONS_PUB" >/dev/null 2>&1; then
    err "Actions public key '$ACTIONS_PUB' failed ssh-keygen validation."
  fi

  # 6. Forced wrapper validation
  validate_file_security "$FORCED_WRAPPER" "root:root" "755" "Forced wrapper"
  if ! cmp -s "$FORCED_WRAPPER" "$REPO_DIR/infra/production/solarsage-github-deploy"; then
    err "Installed wrapper '$FORCED_WRAPPER' does not match '$REPO_DIR/infra/production/solarsage-github-deploy'."
  fi

  # 7. Template known hosts validation
  validate_file_security "$TEMPLATE_KNOWN_HOSTS" "astro:astro" "644" "Template known hosts"
  local template_sha
  template_sha=$(sha256sum "$TEMPLATE_KNOWN_HOSTS" | awk '{print $1}')
  if [ "$template_sha" != "b6f76c2776447c3c23678e7ba4d2474836282c7bfa4ccc294b120ce68cd5261e" ] 2>/dev/null; then
    err "Template known hosts '$TEMPLATE_KNOWN_HOSTS' SHA-256 mismatch (got $template_sha)."
  fi

  # 8. Installed known hosts validation
  if [ -f "$KNOWN_HOSTS_GH" ] || [ -L "$KNOWN_HOSTS_GH" ]; then
    validate_file_security "$KNOWN_HOSTS_GH" "astro:astro" "600" "GitHub known hosts"
    if ! cmp -s "$KNOWN_HOSTS_GH" "$TEMPLATE_KNOWN_HOSTS"; then
      err "Installed known hosts '$KNOWN_HOSTS_GH' does not match template '$TEMPLATE_KNOWN_HOSTS'."
    fi
  elif [ "$is_pre_apply" -eq 0 ]; then
    err "GitHub known hosts file '$KNOWN_HOSTS_GH' is missing."
  fi

  # 9. SSH config validation
  if [ -f "$SSH_CONFIG" ] || [ -L "$SSH_CONFIG" ]; then
    validate_file_security "$SSH_CONFIG" "astro:astro" "600" "SSH config"

    local begin_count
    begin_count=$(grep -c "^# BEGIN SOLARSAGE-PROD-GITHUB" "$SSH_CONFIG" || true)
    local end_count
    end_count=$(grep -c "^# END SOLARSAGE-PROD-GITHUB" "$SSH_CONFIG" || true)

    if [ "$begin_count" -gt 1 ] || [ "$end_count" -gt 1 ]; then
      err "Multiple managed blocks or markers found in '$SSH_CONFIG'."
    fi
    if [ "$begin_count" -ne "$end_count" ]; then
      err "Unmatched managed block markers in '$SSH_CONFIG'."
    fi

    local begin_line
    begin_line=$(grep -n "^# BEGIN SOLARSAGE-PROD-GITHUB" "$SSH_CONFIG" | cut -d: -f1 || true)
    local end_line
    end_line=$(grep -n "^# END SOLARSAGE-PROD-GITHUB" "$SSH_CONFIG" | cut -d: -f1 || true)
    if [ -n "$begin_line" ] && [ -n "$end_line" ]; then
      if [ "$begin_line" -ge "$end_line" ]; then
        err "Managed SSH block markers are out of order in '$SSH_CONFIG'."
      fi
    fi

    local temp_config_no_block
    temp_config_no_block=$(mktemp)
    trap 'rm -f "$temp_config_no_block"' EXIT INT TERM HUP
    awk '
      /^# BEGIN SOLARSAGE-PROD-GITHUB/ {in_block=1; next}
      /^# END SOLARSAGE-PROD-GITHUB/ {in_block=0; next}
      !in_block {print}
    ' "$SSH_CONFIG" > "$temp_config_no_block"

    # Check case-insensitive Host pattern outside managed block (including multiple hosts and case-insensitivity)
    local host_parse_status=0
    # Use python to parse hosts safely without comments.
    # Exit code 0: no alias found
    # Exit code 10: alias found
    # Exit code 1: parse/runtime error
    set +e
    python3.12 -c '
import sys
try:
    content = open(sys.argv[1], "r").read()
    # Strip comments
    lines = [line.split("#")[0].strip() for line in content.splitlines()]
    for line in lines:
        if not line:
            continue
        parts = line.split()
        if parts and parts[0].lower() == "host":
            for pattern in parts[1:]:
                if pattern.lower() == "github.com-solarsage-prod":
                    sys.exit(10)
    sys.exit(0)
except Exception as e:
    sys.exit(1)
' "$temp_config_no_block" 2>/dev/null
    host_parse_status=$?
    set -e

    if [ "$host_parse_status" -eq 10 ]; then
      rm -f "$temp_config_no_block"
      trap - EXIT INT TERM HUP
      err "Host 'github.com-solarsage-prod' defined outside managed block in '$SSH_CONFIG'."
    elif [ "$host_parse_status" -ne 0 ]; then
      rm -f "$temp_config_no_block"
      trap - EXIT INT TERM HUP
      err "Parser error: failed to parse Host alias configuration in '$SSH_CONFIG'."
    fi
    rm -f "$temp_config_no_block"
    trap - EXIT INT TERM HUP

    # Also check if the managed block is present but has been modified/tampered with
    if [ "$begin_count" -eq 1 ]; then
      local extracted_block
      extracted_block=$(awk '
        /^# BEGIN SOLARSAGE-PROD-GITHUB/ {in_block=1; print; next}
        /^# END SOLARSAGE-PROD-GITHUB/ {in_block=0; print; next}
        in_block {print}
      ' "$SSH_CONFIG")

      local expected_block
      expected_block=$(cat <<'EOF'
# BEGIN SOLARSAGE-PROD-GITHUB
Host github.com-solarsage-prod
  HostName github.com
  User git
  IdentityFile ~/.ssh/solarsage_prod_server_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile ~/.ssh/known_hosts.github
  StrictHostKeyChecking yes
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  BatchMode yes
# END SOLARSAGE-PROD-GITHUB
EOF
)
      if [ "$extracted_block" != "$expected_block" ]; then
        err "Managed SSH block in '$SSH_CONFIG' does not match the canonical contract."
      fi
    fi

    if [ "$is_pre_apply" -eq 0 ]; then
      if [ "$begin_count" -ne 1 ]; then
        err "Managed SSH block is missing in '$SSH_CONFIG'."
      fi
    fi
  elif [ "$is_pre_apply" -eq 0 ]; then
    err "SSH config file '$SSH_CONFIG' is missing."
  fi

  # 10. Authorized keys validation
  local actions_type
  local actions_base64
  actions_type=$(awk '{print $1}' "$ACTIONS_PUB")
  actions_base64=$(awk '{print $2}' "$ACTIONS_PUB")
  local actions_pub_key_content="$actions_type $actions_base64"
  local expected_forced_line="restrict,command=\"$FORCED_WRAPPER\" $actions_pub_key_content solarsage-github-actions-prod"

  if [ -f "$AUTHORIZED_KEYS" ] || [ -L "$AUTHORIZED_KEYS" ]; then
    validate_file_security "$AUTHORIZED_KEYS" "astro:astro" "600" "Authorized keys"

    local match_count=0
    local exact_match_count=0
    while IFS= read -r line || [ -n "$line" ]; do
      if [ -z "$line" ]; then
        continue
      fi

      # Search for base64 token in fields (field 2 is typically the base64, but options prefix shifts it)
      local is_actions_key=0
      local fields=()
      read -r -a fields <<< "$line"
      for field in "${fields[@]}"; do
        if [ "$field" = "$actions_base64" ]; then
          is_actions_key=1
          break
        fi
      done

      if [ "$is_actions_key" -eq 1 ]; then
        match_count=$((match_count + 1))
        if [ "$line" = "$expected_forced_line" ]; then
          exact_match_count=$((exact_match_count + 1))
        fi
      fi

      if [[ "$line" == *"solarsage-github-actions-prod"* ]]; then
        if [ "$is_actions_key" -eq 0 ]; then
          # Do not print raw key comments or content in logs
          err "Unexpected key with Actions comment found in authorized keys."
        fi
      fi
    done < "$AUTHORIZED_KEYS"

    if [ "$match_count" -gt 0 ]; then
      if [ "$match_count" -ne "$exact_match_count" ]; then
        err "Actions key exists in '$AUTHORIZED_KEYS' without the exact forced command prefix."
      fi
      if [ "$exact_match_count" -gt 1 ]; then
        err "Duplicate Actions keys found in '$AUTHORIZED_KEYS'."
      fi
    fi

    if [ "$is_pre_apply" -eq 0 ]; then
      if [ "$exact_match_count" -ne 1 ]; then
        err "Actions key with forced command is missing in '$AUTHORIZED_KEYS'."
      fi
    fi
  elif [ "$is_pre_apply" -eq 0 ]; then
    err "Authorized keys file '$AUTHORIZED_KEYS' is missing."
  fi

  # 11. Repo checkout and .git validation
  if [ ! -d "$REPO_DIR" ] || [ -L "$REPO_DIR" ]; then
    err "Repository directory '$REPO_DIR' is missing or is a symlink."
  fi
  if [ ! -d "$REPO_DIR/.git" ] || [ -L "$REPO_DIR/.git" ]; then
    err "Repository .git directory is missing or is a symlink."
  fi

  local current_origin
  if ! current_origin=$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null); then
    err "Failed to get git remote origin URL."
  fi

  if [ "$is_pre_apply" -eq 1 ]; then
    if [[ ! "$current_origin" =~ ^(git@github\.com:|https://github\.com/|git@github\.com-solarsage-prod:)basilivanov/solarsage-astro(\.git)?$ ]]; then
      # Do not log raw potentially credential-bearing origin URL
      err "Current git origin does not match the expected owner/repo 'basilivanov/solarsage-astro'."
    fi
  else
    if [ "$current_origin" != "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" ]; then
      err "Current git origin is not normalized to 'git@github.com-solarsage-prod:basilivanov/solarsage-astro.git'."
    fi
  fi
}
# END_BLOCK: COMMON_VALIDATION

# START_BLOCK: APPLY
apply_action() {
  if [ "$(id -u)" -ne 0 ]; then
    err "Action --apply must be run as root."
  fi

  # Phase A: Validation phase (Read-only validation before any mutation)
  validate_installed_state 1

  # Reject malformed no-final-LF for config/authorized_keys if they exist
  if [ -f "$SSH_CONFIG" ]; then
    local last_char_cfg
    last_char_cfg=$(tail -c 1 "$SSH_CONFIG" | od -An -t x1 | xargs)
    if [ -n "$last_char_cfg" ] && [ "$last_char_cfg" != "0a" ]; then
      err "Existing SSH config '$SSH_CONFIG' does not end with a final newline (LF). Prevalidation reject."
    fi
  fi
  if [ -f "$AUTHORIZED_KEYS" ]; then
    local last_char_ak
    last_char_ak=$(tail -c 1 "$AUTHORIZED_KEYS" | od -An -t x1 | xargs)
    if [ -n "$last_char_ak" ] && [ "$last_char_ak" != "0a" ]; then
      err "Existing authorized keys '$AUTHORIZED_KEYS' does not end with a final newline (LF). Prevalidation reject."
    fi
  fi

  # Phase B: Mutation phase
  # Initialize variables to avoid unbound variable errors in cleanup_temps
  tmp_kh=""
  tmp_cfg=""
  tmp_ak=""

  cleanup_temps() {
    [ -n "${tmp_kh:-}" ] && [ -f "${tmp_kh:-}" ] && rm -f "${tmp_kh:-}"
    [ -n "${tmp_cfg:-}" ] && [ -f "${tmp_cfg:-}" ] && rm -f "${tmp_cfg:-}"
    [ -n "${tmp_ak:-}" ] && [ -f "${tmp_ak:-}" ] && rm -f "${tmp_ak:-}"
  }
  trap cleanup_temps EXIT INT TERM HUP

  # 1. Prepare GitHub known hosts
  tmp_kh=$(mktemp "$SSH_DIR/known_hosts.github.XXXXXX")
  chmod 0600 "$tmp_kh"
  chown astro:astro "$tmp_kh"
  cat "$TEMPLATE_KNOWN_HOSTS" > "$tmp_kh"

  # 2. Prepare SSH config
  tmp_cfg=$(mktemp "$SSH_DIR/config.XXXXXX")
  chmod 0600 "$tmp_cfg"
  chown astro:astro "$tmp_cfg"

  local config_block
  config_block=$(cat <<'EOF'
# BEGIN SOLARSAGE-PROD-GITHUB
Host github.com-solarsage-prod
  HostName github.com
  User git
  IdentityFile ~/.ssh/solarsage_prod_server_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile ~/.ssh/known_hosts.github
  StrictHostKeyChecking yes
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  BatchMode yes
# END SOLARSAGE-PROD-GITHUB
EOF
)

  python3.12 -c '
import sys, os

config_path = sys.argv[1]
tmp_cfg_path = sys.argv[2]
block = sys.argv[3].encode("utf-8")

content = b""
if os.path.exists(config_path):
    with open(config_path, "rb") as f:
        content = f.read()

begin = b"# BEGIN SOLARSAGE-PROD-GITHUB"
end = b"# END SOLARSAGE-PROD-GITHUB"

if begin in content and end in content:
    idx_begin = content.index(begin)
    idx_end = content.index(end) + len(end)
    if idx_end < len(content) and content[idx_end:idx_end+1] == b"\n":
        idx_end += 1
    elif idx_end < len(content) and content[idx_end:idx_end+2] == b"\r\n":
        idx_end += 2
    new_content = content[:idx_begin] + block + b"\n" + content[idx_end:]
else:
    if content and not content.endswith(b"\n") and not content.endswith(b"\r"):
        new_content = content + b"\n" + block + b"\n"
    else:
        new_content = content + block + b"\n"

with open(tmp_cfg_path, "wb") as f:
    f.write(new_content)
' "$SSH_CONFIG" "$tmp_cfg" "$config_block"

  # 3. Prepare authorized_keys
  tmp_ak=$(mktemp "$SSH_DIR/authorized_keys.XXXXXX")
  chmod 0600 "$tmp_ak"
  chown astro:astro "$tmp_ak"

  local actions_type
  local actions_base64
  actions_type=$(awk '{print $1}' "$ACTIONS_PUB")
  actions_base64=$(awk '{print $2}' "$ACTIONS_PUB")
  local actions_pub_key_content="$actions_type $actions_base64"
  local forced_line="restrict,command=\"$FORCED_WRAPPER\" $actions_pub_key_content solarsage-github-actions-prod"

  python3.12 -c '
import sys, os

ak_path = sys.argv[1]
tmp_ak_path = sys.argv[2]
key_base64 = sys.argv[3].encode("utf-8")
forced_line = sys.argv[4].encode("utf-8")

content = b""
if os.path.exists(ak_path):
    with open(ak_path, "rb") as f:
        content = f.read()

lines = content.splitlines(keepends=True)
new_lines = []
replaced = False
for line in lines:
    # Check for exact token presence in fields of the line
    fields = line.strip().split()
    if key_base64 in fields:
        new_lines.append(forced_line + b"\n")
        replaced = True
    else:
        new_lines.append(line)

if not replaced:
    if new_lines and not new_lines[-1].endswith(b"\n") and not new_lines[-1].endswith(b"\r"):
        new_lines[-1] = new_lines[-1] + b"\n"
    new_lines.append(forced_line + b"\n")

with open(tmp_ak_path, "wb") as f:
    f.write(b"".join(new_lines))
' "$AUTHORIZED_KEYS" "$tmp_ak" "$actions_base64" "$forced_line"

  # Atomic rename
  mv "$tmp_kh" "$KNOWN_HOSTS_GH"
  mv "$tmp_cfg" "$SSH_CONFIG"
  mv "$tmp_ak" "$AUTHORIZED_KEYS"

  # Reset trap
  trap - EXIT INT TERM HUP

  # 4. Normalize origin last
  echo "Normalizing git origin..."
  if ! git -C "$REPO_DIR" remote set-url origin "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git"; then
    err "Failed to normalize git origin to git@github.com-solarsage-prod:basilivanov/solarsage-astro.git. Deployment readiness not confirmed."
  fi

  # Run post-apply validation
  validate_installed_state 0

  echo "Successfully applied GitHub transport configuration."
  exit 0
}
# END_BLOCK: APPLY

# START_BLOCK: PREFLIGHT
preflight_action() {
  if [ "$(id -un)" != "astro" ]; then
    err "Action --preflight must be run as the 'astro' user."
  fi

  validate_installed_state 0

  # HTTPS reachability check
  echo "Checking GitHub HTTPS connectivity..."
  local http_status
  http_status=$(get_github_visibility_status)

  # Visiblity check: 200 (public warning, but preflight ok), 404 (private indication, preflight ok), other (fail)
  if [ "$http_status" = "200" ]; then
    echo "WARNING: Repository is currently PUBLIC. This is not production-ready."
  elif [ "$http_status" = "404" ]; then
    echo "Repository is not publicly visible (private/not found)."
  else
    err "GitHub API visibility check returned unexpected status: $http_status"
  fi

  # Bounded git ls-remote origin check
  echo "Testing SSH transport connectivity..."
  local remote_sha
  remote_sha=$(verify_ls_remote_main)

  echo "Preflight check completed successfully. Remote SHA: $remote_sha"
  exit 0
}
# END_BLOCK: PREFLIGHT

# START_BLOCK: CHECK
check_action() {
  if [ "$(id -un)" != "astro" ]; then
    err "Action --check must be run as the 'astro' user."
  fi

  validate_installed_state 0

  # 1. Query anonymous API
  local api_status
  api_status=$(get_github_visibility_status)

  if [ "$api_status" = "200" ]; then
    err "Source readiness check failed: repository is public."
  fi

  if [ "$api_status" != "404" ]; then
    err "Source readiness check failed: GitHub API returned unexpected status $api_status."
  fi

  # 404 + successful SSH ls-remote -> private proof
  local remote_sha
  remote_sha=$(verify_ls_remote_main)

  # 2. --expected-sha compares exactly to remote refs/heads/main
  if [ -n "$EXPECTED_SHA" ]; then
    if [ "$remote_sha" != "$EXPECTED_SHA" ]; then
      err "Source readiness check failed: remote SHA ($remote_sha) does not match expected SHA ($EXPECTED_SHA)."
    fi
  fi

  echo "Source readiness verified: repository is private, SSH transport works."
  echo "Remote SHA: $remote_sha"
  exit 0
}
# END_BLOCK: CHECK

# START_BLOCK: PARSE_ARGS
ACTION=""
EXPECTED_SHA=""
EXPECTED_SHA_SEEN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      if [ -n "$ACTION" ]; then usage_err; fi
      ACTION="apply"
      shift
      ;;
    --preflight)
      if [ -n "$ACTION" ]; then usage_err; fi
      ACTION="preflight"
      shift
      ;;
    --check)
      if [ -n "$ACTION" ]; then usage_err; fi
      ACTION="check"
      shift
      ;;
    --expected-sha)
      if [ "$EXPECTED_SHA_SEEN" -eq 1 ]; then usage_err; fi
      if [ $# -lt 2 ]; then usage_err; fi
      EXPECTED_SHA="$2"
      EXPECTED_SHA_SEEN=1
      if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
        usage_err
      fi
      shift 2
      ;;
    *)
      usage_err
      ;;
  esac
done

if [ -z "$ACTION" ]; then
  usage_err
fi

if [ "$ACTION" != "check" ] && [ -n "$EXPECTED_SHA" ]; then
  usage_err
fi
# END_BLOCK: PARSE_ARGS

# Action dispatch
if [ "$ACTION" = "apply" ]; then
  apply_action
elif [ "$ACTION" = "preflight" ]; then
  preflight_action
elif [ "$ACTION" = "check" ]; then
  check_action
fi
