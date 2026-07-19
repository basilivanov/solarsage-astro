#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_GITHUB_ACCESS — complete access contract matrix tests
# ROLE: Verifies argument parsing, paths, permission validation, config parsing, and readiness checks.
# ############################################################################

set -euo pipefail

# START_MODULE_CONTRACT: M-TEST-PROD-GITHUB-ACCESS
# purpose: Verify prod-github-access.sh contract matrix in isolated sandbox.
# owns:
#   - scripts/deploy/tests/test-prod-github-access.sh
# inputs: none
# outputs: exits 0 on success, non-zero on test failure.
# invariants:
#   - No mutation to actual host /home/astro, /etc/solarsage, or Git index.
#   - No network or SSH calls.
#   - Fail-closed path-aware mocks.
# END_MODULE_CONTRACT: M-TEST-PROD-GITHUB-ACCESS

# START_MODULE_MAP: M-TEST-PROD-GITHUB-ACCESS
# public_entrypoints:
#   - main
# semantic_blocks:
#   - TEST_SUITE: runs the contract matrix
# END_MODULE_MAP: M-TEST-PROD-GITHUB-ACCESS

# START_BLOCK: TEST_SUITE

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)

TEST_DIR=$(mktemp -d "/tmp/solarsage-r13-access-test.XXXXXX")
LAST_CASE_ID="unknown"
CASE_COUNT=0

cleanup_harness() {
  local exit_code=$?
  if [ "$exit_code" -ne 0 ]; then
    echo "Harness failed at Case ID: ${LAST_CASE_ID:-unknown} with exit code $exit_code" >&2
  fi
  rm -rf "$TEST_DIR"
}
trap cleanup_harness EXIT INT TERM HUP

# Setup Immutable Baseline
BASELINE_DIR="$TEST_DIR/baseline"
MOCK_HOME="$TEST_DIR/home/astro"
MOCK_ETC="$TEST_DIR/etc/solarsage"
MOCK_REPO="$TEST_DIR/opt/solarsage-astro"
MOCK_BIN="$TEST_DIR/bin"
MOCK_WRAPPER="$TEST_DIR/usr/local/sbin/solarsage-github-deploy"

mkdir -p "$BASELINE_DIR/home/astro/.ssh"
chmod 700 "$BASELINE_DIR/home/astro/.ssh"
mkdir -p "$BASELINE_DIR/etc/solarsage/keys"
mkdir -p "$BASELINE_DIR/opt/solarsage-astro/infra/ssh"
mkdir -p "$BASELINE_DIR/opt/solarsage-astro/infra/production"
mkdir -p "$BASELINE_DIR/opt/solarsage-astro/.git"
mkdir -p "$MOCK_BIN"

# Generate Baseline checkout key pair
/usr/bin/ssh-keygen -t ed25519 -N "" -f "$BASELINE_DIR/home/astro/.ssh/solarsage_prod_server_ed25519" >/dev/null
chmod 600 "$BASELINE_DIR/home/astro/.ssh/solarsage_prod_server_ed25519"
chmod 644 "$BASELINE_DIR/home/astro/.ssh/solarsage_prod_server_ed25519.pub"

# Generate Baseline Actions key pair
/usr/bin/ssh-keygen -t ed25519 -N "" -f "$TEST_DIR/actions_temp" >/dev/null
cat "$TEST_DIR/actions_temp.pub" > "$BASELINE_DIR/etc/solarsage/keys/github-actions-deploy.pub"
chmod 644 "$BASELINE_DIR/etc/solarsage/keys/github-actions-deploy.pub"
rm -f "$TEST_DIR/actions_temp" "$TEST_DIR/actions_temp.pub"

# Generate passphrase-protected key
/usr/bin/ssh-keygen -t ed25519 -N "secure_pass" -f "$TEST_DIR/passphrase_key" >/dev/null

# Copy templates to baseline (from the current checkout, never a foreign path)
cp "$REPO_ROOT/infra/production/solarsage-github-deploy" "$BASELINE_DIR/opt/solarsage-astro/infra/production/solarsage-github-deploy"
chmod 755 "$BASELINE_DIR/opt/solarsage-astro/infra/production/solarsage-github-deploy"
cp "$REPO_ROOT/infra/ssh/github.com.known_hosts" "$BASELINE_DIR/opt/solarsage-astro/infra/ssh/github.com.known_hosts"
chmod 644 "$BASELINE_DIR/opt/solarsage-astro/infra/ssh/github.com.known_hosts"

# Save safe tokens/comment/sentinels for global output scan
CHECKOUT_PUB_BASE64=$(awk '{print $2}' "$BASELINE_DIR/home/astro/.ssh/solarsage_prod_server_ed25519.pub")
ACTIONS_PUB_BASE64=$(awk '{print $2}' "$BASELINE_DIR/etc/solarsage/keys/github-actions-deploy.pub")
CREDENTIAL_SENTINEL="https://token@github.com"
API_BODY_SENTINEL_R13="API_BODY_SENTINEL_R13"
MALFORMED_REMOTE_SENTINEL_R13="MALFORMED_REMOTE_SENTINEL_R13"
ENV_SECRET_SENTINEL_R13="ENV_SECRET_SENTINEL_R13"
ACTIONS_COMMENT="solarsage-github-actions-prod"
PEM_MARKER="BEGIN OPENSSH PRIVATE KEY"

export CREDENTIAL_SENTINEL API_BODY_SENTINEL_R13 MALFORMED_REMOTE_SENTINEL_R13 ENV_SECRET_SENTINEL_R13

# -----------------------------------------------------------------------------
# Write Strict Path-Aware Mocks
# -----------------------------------------------------------------------------

# 1. Mock 'id'
cat << EOF > "$MOCK_BIN/id"
#!/usr/bin/env bash
uid="\${MOCK_UID:-1000}"
user="\${MOCK_USER:-astro}"
if [ \$# -ne 1 ]; then
  echo "id error: expected exact 1 arg, got \$#" >&2
  exit 1
fi
case "\$1" in
  -u) echo "\$uid"; exit 0 ;;
  -un) echo "\$user"; exit 0 ;;
  *) echo "id error: unexpected argument: \$1" >&2; exit 1 ;;
esac
EOF
chmod +x "$MOCK_BIN/id"

# 2. Mock 'stat'
cat << EOF > "$MOCK_BIN/stat"
#!/usr/bin/env bash
format=""
path=""
if [ \$# -ne 3 ]; then
  echo "stat error: expected exact 3 args, got \$#" >&2
  exit 1
fi
if [ "\$1" != "-c" ]; then
  echo "stat error: expected -c, got \$1" >&2
  exit 1
fi
format="\$2"
path="\$3"

abs_path=\$(realpath -m "\$path")
if [[ "\$abs_path" != "$TEST_DIR"* ]]; then
  echo "stat error: target outside sandbox: \$abs_path" >&2
  exit 1
fi

if [ -n "\${MOCK_BAD_OWNER_PATH:-}" ] && [[ "\$abs_path" == *"\$MOCK_BAD_OWNER_PATH" ]]; then
  if [ "\$format" = "%U:%G" ]; then
    echo "baduser:badgroup"
    exit 0
  fi
fi

if [ -n "\${MOCK_BAD_MODE_PATH:-}" ] && [[ "\$abs_path" == *"\$MOCK_BAD_MODE_PATH" ]]; then
  if [ "\$format" = "%a" ]; then
    echo "777"
    exit 0
  fi
fi

if [ "\$format" = "%U:%G" ]; then
  if [[ "\$abs_path" == *"/usr/local/sbin/solarsage-github-deploy" || "\$abs_path" == *"/etc/solarsage/keys/github-actions-deploy.pub" ]]; then
    echo "root:root"
  else
    echo "astro:astro"
  fi
  exit 0
elif [ "\$format" = "%a" ]; then
  /usr/bin/stat -c "%a" "\$abs_path"
  exit 0
fi

echo "stat error: unknown format \$format" >&2
exit 1
EOF
chmod +x "$MOCK_BIN/stat"

# 3. Mock 'chown'
cat << EOF > "$MOCK_BIN/chown"
#!/usr/bin/env bash
if [ \$# -ne 2 ]; then
  echo "chown error: expected exact 2 args, got \$#" >&2
  exit 1
fi
owner="\$1"
target="\$2"
if [ "\$owner" != "astro:astro" ]; then
  echo "chown error: unexpected owner: \$owner" >&2
  exit 1
fi

abs_target=\$(realpath -m "\$target")
if [[ "\$abs_target" != "$TEST_DIR"* ]]; then
  echo "chown error: target outside sandbox: \$abs_target" >&2
  exit 1
fi

if [[ "\$abs_target" != "$MOCK_HOME/.ssh/"* ]]; then
  echo "chown error: target outside .ssh: \$abs_target" >&2
  exit 1
fi

# Target must exist and be a regular non-symlink file
if [ ! -f "\$abs_target" ] || [ -L "\$abs_target" ]; then
  echo "chown error: target must be existing regular file: \$abs_target" >&2
  exit 1
fi

base_target=\$(basename "\$abs_target")
# Must match exact mktemp output: prefix.exactly6alnum
if [[ "\$base_target" =~ ^(known_hosts\\.github|config|authorized_keys)\\.[a-zA-Z0-9]{6}\$ ]]; then
  echo "chown \${owner} \${base_target}" >> "$TEST_DIR/chown_audit.log"
else
  echo "chown error: unexpected temp target format: \$base_target" >&2
  exit 1
fi
exit 0
EOF
chmod +x "$MOCK_BIN/chown"

# 4. Mock 'mv'
cat << EOF > "$MOCK_BIN/mv"
#!/usr/bin/env bash
if [ \$# -ne 2 ]; then
  echo "mv error: expected exact 2 args, got \$#" >&2
  exit 1
fi
src="\$1"
dst="\$2"

abs_src=\$(realpath -m "\$src")
abs_dst=\$(realpath -m "\$dst")

if [[ "\$abs_src" != "$TEST_DIR"* || "\$abs_dst" != "$TEST_DIR"* ]]; then
  echo "mv error: operands outside sandbox" >&2
  exit 1
fi

if [[ "\$abs_src" != "$MOCK_HOME/.ssh/"* ]]; then
  echo "mv error: source must be inside .ssh sandbox" >&2
  exit 1
fi

# Source must exist and be a regular non-symlink file
if [ ! -f "\$abs_src" ] || [ -L "\$abs_src" ]; then
  echo "mv error: source must be existing regular file: \$abs_src" >&2
  exit 1
fi

# Verify category match with exact 6-alnum suffix
src_base=\$(basename "\$abs_src")
if [[ "\$src_base" =~ ^known_hosts\\.github\\.[a-zA-Z0-9]{6}\$ ]]; then
  if [ "\$abs_dst" != "$MOCK_HOME/.ssh/known_hosts.github" ]; then
    echo "mv error: destination mismatch for known_hosts" >&2
    exit 1
  fi
elif [[ "\$src_base" =~ ^config\\.[a-zA-Z0-9]{6}\$ ]]; then
  if [ "\$abs_dst" != "$MOCK_HOME/.ssh/config" ]; then
    echo "mv error: destination mismatch for config" >&2
    exit 1
  fi
elif [[ "\$src_base" =~ ^authorized_keys\\.[a-zA-Z0-9]{6}\$ ]]; then
  if [ "\$abs_dst" != "$MOCK_HOME/.ssh/authorized_keys" ]; then
    echo "mv error: destination mismatch for authorized_keys" >&2
    exit 1
  fi
else
  echo "mv error: unexpected source temp file format: \$src_base" >&2
  exit 1
fi

dst_base=\$(basename "\$abs_dst")
echo "mv \$dst_base" >> "$TEST_DIR/mv_audit.log"

if [ -n "\${MOCK_MV_FAIL_DEST:-}" ] && [[ "\$abs_dst" == *"\$MOCK_MV_FAIL_DEST"* ]]; then
  echo "mv mock forced failure" >&2
  exit 1
fi

/usr/bin/mv -- "\$src" "\$dst"
EOF
chmod +x "$MOCK_BIN/mv"

# 5. Mock 'git'
cat << EOF > "$MOCK_BIN/git"
#!/usr/bin/env bash
# Exact full argv check
# Check if forbidden command
for arg in "\$@"; do
  if [ "\$arg" = "fetch" ] || [ "\$arg" = "checkout" ] || [ "\$arg" = "push" ]; then
    echo "\$arg" >> "$TEST_DIR/git_forbidden.log"
    exit 1
  fi
done

if [ "\$1" = "-C" ] && [ "\$2" = "$MOCK_REPO" ] && [ "\$3" = "remote" ] && [ "\$4" = "get-url" ] && [ "\$5" = "origin" ] && [ \$# -eq 5 ]; then
  echo "git remote get-url origin" >> "$TEST_DIR/git_audit.log"
  cat "$TEST_DIR/mock_origin" 2>/dev/null || exit 1
  exit 0
elif [ "\$1" = "-C" ] && [ "\$2" = "$MOCK_REPO" ] && [ "\$3" = "remote" ] && [ "\$4" = "set-url" ] && [ "\$5" = "origin" ] && [ "\$6" = "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" ] && [ \$# -eq 6 ]; then
  echo "git remote set-url origin" >> "$TEST_DIR/git_audit.log"
  if [ "\${MOCK_GIT_SET_URL_RC:-0}" -ne 0 ]; then
    exit "\$MOCK_GIT_SET_URL_RC"
  fi
  echo "\$6" > "$TEST_DIR/mock_origin"
  exit 0
elif [ "\$1" = "-C" ] && [ "\$2" = "$MOCK_REPO" ] && [ "\$3" = "ls-remote" ] && [ "\$4" = "--exit-code" ] && [ "\$5" = "origin" ] && [ "\$6" = "refs/heads/main" ] && [ \$# -eq 6 ]; then
  echo "git ls-remote" >> "$TEST_DIR/git_audit.log"
  # Timeout simulation: if MOCK_TIMEOUT_TRIGGER is set, exit 124 (simulate timeout)
  if [ "\${MOCK_TIMEOUT_TRIGGER:-0}" -eq 1 ]; then
    exit 124
  fi
  if [ "\${MOCK_GIT_LS_REMOTE_RC:-0}" -ne 0 ]; then
    exit "\$MOCK_GIT_LS_REMOTE_RC"
  fi
  if [ -z "\${MOCK_GIT_LS_REMOTE_OUT+x}" ]; then
    echo -e "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\\trefs/heads/main"
  else
    echo -e "\$MOCK_GIT_LS_REMOTE_OUT"
  fi
  exit 0
fi

echo "git error: unexpected argv" >&2
exit 1
EOF
chmod +x "$MOCK_BIN/git"

# 6. Mock 'curl'
cat << EOF > "$MOCK_BIN/curl"
#!/usr/bin/env bash
# Exact argv shape check
expected_args=("-sS" "-o" "/dev/null" "-w" "%{http_code}" "--connect-timeout" "5" "--max-time" "10" "https://api.github.com/repos/basilivanov/solarsage-astro")
if [ \$# -ne 10 ]; then
  echo "curl error: expected exact 10 args, got \$#" >&2
  exit 1
fi
for i in {0..9}; do
  val=\${expected_args[\$i]}
  arg_idx=\$((\$i + 1))
  arg_val=\${!arg_idx}
  if [ "\$arg_val" != "\$val" ]; then
    echo "curl error: arg \$arg_idx mismatch (expected \$val, got \$arg_val)" >&2
    exit 1
  fi
done

echo "curl" >> "$TEST_DIR/curl_audit.log"
if [ -n "\${MOCK_CURL_BODY_SENTINEL:-}" ]; then
  echo "\$MOCK_CURL_BODY_SENTINEL" >&2
fi

if [ "\${MOCK_CURL_RC:-0}" -ne 0 ]; then
  exit "\$MOCK_CURL_RC"
fi
echo -n "\${MOCK_CURL_STATUS:-200}"
EOF
chmod +x "$MOCK_BIN/curl"

# 7. Mock 'timeout'
cat << EOF > "$MOCK_BIN/timeout"
#!/usr/bin/env bash
if [ \$# -ne 8 ]; then
  echo "timeout error: expected exact 8 args, got \$#" >&2
  exit 1
fi
if [ "\$1" != "15s" ] || [ "\$2" != "git" ] || [ "\$3" != "-C" ] || [ "\$4" != "$MOCK_REPO" ] || [ "\$5" != "ls-remote" ] || [ "\$6" != "--exit-code" ] || [ "\$7" != "origin" ] || [ "\$8" != "refs/heads/main" ]; then
  echo "timeout error: unexpected arguments" >&2
  exit 1
fi

echo "timeout" >> "$TEST_DIR/timeout_audit.log"
# Always delegate to sandbox mock git; MOCK_TIMEOUT_TRIGGER is handled by git mock
exec "$MOCK_BIN/git" "-C" "$MOCK_REPO" "ls-remote" "--exit-code" "origin" "refs/heads/main"
EOF
chmod +x "$MOCK_BIN/timeout"

# 8. Mock 'ssh-keygen'
cat << EOF > "$MOCK_BIN/ssh-keygen"
#!/usr/bin/env bash
# Validate shape
is_y_shape=0
is_l_shape=0
if [ \$# -eq 5 ] && [ "\$1" = "-y" ] && [ "\$2" = "-P" ] && [ "\$3" = "" ] && [ "\$4" = "-f" ]; then
  is_y_shape=1
  target="\$5"
elif [ \$# -eq 3 ] && [ "\$1" = "-l" ] && [ "\$2" = "-f" ]; then
  is_l_shape=1
  target="\$3"
else
  echo "ssh-keygen error: unexpected argv shape" >&2
  exit 1
fi

abs_target=\$(realpath -m "\$target")
if [[ "\$abs_target" != "$TEST_DIR"* ]]; then
  echo "ssh-keygen error: target outside sandbox: \$abs_target" >&2
  exit 1
fi

# Exact fixture paths only
CHECKOUT_PRIV="$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
ACTIONS_PUB_PATH="$MOCK_ETC/keys/github-actions-deploy.pub"

if [ "\$is_y_shape" -eq 1 ]; then
  # -y only allowed for checkout private fixture
  if [ "\$abs_target" != "\$CHECKOUT_PRIV" ]; then
    echo "ssh-keygen error: -y only allowed for checkout private fixture" >&2
    exit 1
  fi
elif [ "\$is_l_shape" -eq 1 ]; then
  # -l allowed for checkout private or Actions public fixture
  if [ "\$abs_target" != "\$CHECKOUT_PRIV" ] && [ "\$abs_target" != "\$ACTIONS_PUB_PATH" ]; then
    echo "ssh-keygen error: -l only allowed for checkout private or Actions public fixture" >&2
    exit 1
  fi
fi

echo "ssh-keygen" >> "$TEST_DIR/ssh_keygen_audit.log"
/usr/bin/ssh-keygen "\$@"
EOF
chmod +x "$MOCK_BIN/ssh-keygen"

# 9. Mock 'mktemp'
cat << EOF > "$MOCK_BIN/mktemp"
#!/usr/bin/env bash
# Template or no-arg
if [ \$# -eq 0 ]; then
  # No arg creates validation inside sandbox
  /usr/bin/mktemp "$TEST_DIR/validation.XXXXXX"
  exit 0
elif [ \$# -eq 1 ]; then
  prefix="\$1"
  # Must match exactly one of three template strings
  if [ "\$prefix" != "$MOCK_HOME/.ssh/known_hosts.github.XXXXXX" ] && \\
     [ "\$prefix" != "$MOCK_HOME/.ssh/config.XXXXXX" ] && \\
     [ "\$prefix" != "$MOCK_HOME/.ssh/authorized_keys.XXXXXX" ]; then
    echo "mktemp error: unexpected template: \$prefix" >&2
    exit 1
  fi
  # Configurable failure by prefix
  if [ -n "\${MOCK_MKTEMP_FAIL_PREFIX:-}" ] && [[ "\$prefix" == *"\$MOCK_MKTEMP_FAIL_PREFIX"* ]]; then
    echo "mktemp mock forced failure" >&2
    exit 1
  fi
  /usr/bin/mktemp "\$@"
  exit 0
else
  echo "mktemp error: unexpected argc: \$#" >&2
  exit 1
fi
EOF
chmod +x "$MOCK_BIN/mktemp"

# 10. Mock 'python3.12'
cat << PYEOF > "$MOCK_BIN/python3.12"
#!/usr/bin/env bash
# Determine operation by argc
# \$1=-c, \$2=inline script, \$3.. are real positional args
# Mock uses expanded sandbox paths; no runtime production-variable substitution.

# Helper: verify target exists, regular non-symlink, basename matches pattern
verify_regfile_basename() {
  local path="\$1"
  local pattern="\$2"
  if [ ! -f "\$path" ] || [ -L "\$path" ]; then
    echo "python error: target must be existing regular file: \$path" >&2
    exit 1
  fi
  local base
  base=\$(basename "\$path")
  if [[ ! "\$base" =~ \$pattern ]]; then
    echo "python error: unexpected basename format: \$base" >&2
    exit 1
  fi
}

if [ \$# -eq 3 ] && [ "\$1" = "-c" ]; then
  # host-parse shape: -c SCRIPT temp_config_no_block
  target_cfg="\$3"
  abs_cfg=\$(realpath -m "\$target_cfg")
  if [[ "\$abs_cfg" != "$TEST_DIR"* ]]; then
    echo "python error: host-parse target outside sandbox" >&2
    exit 1
  fi
  verify_regfile_basename "\$abs_cfg" '^validation\\.[a-zA-Z0-9]{6}\$'
  echo "python host-parse" >> "$TEST_DIR/python_audit.log"
  if [ "\${MOCK_PYTHON_FAIL_OP:-}" = "host-parse" ]; then
    exit 1
  fi
  /usr/bin/python3.12 "\$@"
  exit \$?
elif [ \$# -eq 5 ] && [ "\$1" = "-c" ]; then
  # config-write shape: -c SCRIPT SSH_CONFIG tmp_cfg config_block
  # After reset_fixture substitution: SSH_CONFIG is expanded sandbox path
  if [ "\$3" != "$MOCK_HOME/.ssh/config" ]; then
    echo "python error: config-write unexpected target: \$3" >&2
    exit 1
  fi
  target_tmp="\$4"
  abs_tmp=\$(realpath -m "\$target_tmp")
  if [[ "\$abs_tmp" != "$TEST_DIR"* ]]; then
    echo "python error: config-write temp outside sandbox" >&2
    exit 1
  fi
  verify_regfile_basename "\$abs_tmp" '^config\\.[a-zA-Z0-9]{6}\$'
  echo "python config-write" >> "$TEST_DIR/python_audit.log"
  if [ "\${MOCK_PYTHON_FAIL_OP:-}" = "config-write" ]; then
    exit 1
  fi
  /usr/bin/python3.12 "\$@"
  exit \$?
elif [ \$# -eq 6 ] && [ "\$1" = "-c" ]; then
  # authorized-write shape: -c SCRIPT AUTHORIZED_KEYS tmp_ak key_base64 ak_block
  # After reset_fixture substitution: AUTHORIZED_KEYS is expanded sandbox path
  if [ "\$3" != "$MOCK_HOME/.ssh/authorized_keys" ]; then
    echo "python error: authorized-write unexpected target: \$3" >&2
    exit 1
  fi
  target_tmp="\$4"
  abs_tmp=\$(realpath -m "\$target_tmp")
  if [[ "\$abs_tmp" != "$TEST_DIR"* ]]; then
    echo "python error: authorized-write temp outside sandbox" >&2
    exit 1
  fi
  verify_regfile_basename "\$abs_tmp" '^authorized_keys\\.[a-zA-Z0-9]{6}\$'
  echo "python authorized-write" >> "$TEST_DIR/python_audit.log"
  if [ "\${MOCK_PYTHON_FAIL_OP:-}" = "authorized-write" ]; then
    exit 1
  fi
  /usr/bin/python3.12 "\$@"
  exit \$?
fi

echo "python error: unexpected argv shape: \$# args" >&2
exit 1
PYEOF
chmod +x "$MOCK_BIN/python3.12"

# -----------------------------------------------------------------------------
# Verify Mock Contracts (Self-proof)
# -----------------------------------------------------------------------------
verify_mock_contracts() {
  set +e
  # stat checks
  "$MOCK_BIN/stat" -c %U:%G /etc/shadow >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: stat mock allowed outside path" >&2; exit 1; fi
  "$MOCK_BIN/stat" -x "$MOCK_HOME/.ssh" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: stat mock allowed invalid format" >&2; exit 1; fi

  # chown: reject root:root even on valid sandbox temp
  test_chown_temp=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/known_hosts.github.XXXXXX")
  "$MOCK_BIN/chown" root:root "$test_chown_temp" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: chown mock allowed root:root" >&2; exit 1; fi
  "$MOCK_BIN/chown" astro:astro /etc/shadow >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: chown mock allowed outside path" >&2; exit 1; fi
  rm -f "$test_chown_temp"

  # mv: reject nonexistent source, symlink source, wrong category
  "$MOCK_BIN/mv" "$MOCK_HOME/.ssh/nonexistent.abcdef" "$MOCK_HOME/.ssh/config" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mv mock allowed nonexistent source" >&2; exit 1; fi
  test_mv_src=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/known_hosts.github.XXXXXX")
  rm -f "$test_mv_src"
  ln -sf /dev/null "$test_mv_src"
  "$MOCK_BIN/mv" "$test_mv_src" "$MOCK_HOME/.ssh/known_hosts.github" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mv mock allowed symlink source" >&2; exit 1; fi
  rm -f "$test_mv_src"
  test_wrong_cat=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/unknown.XXXXXX")
  "$MOCK_BIN/mv" "$test_wrong_cat" "$MOCK_HOME/.ssh/config" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mv mock allowed wrong category" >&2; exit 1; fi
  rm -f "$test_wrong_cat"
  "$MOCK_BIN/mv" "$MOCK_HOME/.ssh/config" /etc/shadow >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mv mock allowed outside destination" >&2; exit 1; fi

  # git checks
  "$MOCK_BIN/git" -C "$MOCK_REPO" remote get-url origin extra >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: git mock allowed extra arguments" >&2; exit 1; fi

  # curl checks
  "$MOCK_BIN/curl" -sS -o /dev/null -w %{http_code} https://api.github.com/repos/basilivanov/solarsage-astro >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: curl mock allowed missing arguments" >&2; exit 1; fi

  # timeout checks
  "$MOCK_BIN/timeout" 10s git >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: timeout mock allowed invalid args" >&2; exit 1; fi

  # ssh-keygen: reject arbitrary sandbox file
  test_skg_temp=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/arbitrary.XXXXXX")
  "$MOCK_BIN/ssh-keygen" -l -f "$test_skg_temp" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: ssh-keygen mock allowed arbitrary file" >&2; exit 1; fi
  rm -f "$test_skg_temp"
  "$MOCK_BIN/ssh-keygen" -y -f /etc/shadow >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: ssh-keygen mock allowed outside path" >&2; exit 1; fi

  # mktemp: reject arbitrary template
  "$MOCK_BIN/mktemp" "$MOCK_HOME/.ssh/arbitrary.XXXXXX" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mktemp mock allowed arbitrary template" >&2; exit 1; fi
  "$MOCK_BIN/mktemp" /etc/shadow.XXXXXX >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: mktemp mock allowed outside path" >&2; exit 1; fi

  # python3.12 checks
  "$MOCK_BIN/python3.12" -c "import os" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed unexpected shape" >&2; exit 1; fi
  "$MOCK_BIN/python3.12" -c "print(1)" /etc/shadow >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed outside path host-parse" >&2; exit 1; fi
  "$MOCK_BIN/python3.12" -c "print(1)" "$MOCK_HOME/.ssh/not-config" "$TEST_DIR/tmp" "block" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed wrong config-write target" >&2; exit 1; fi
  "$MOCK_BIN/python3.12" -c "print(1)" "$MOCK_HOME/.ssh/config" "/etc/shadow" "block" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed outside temp in config-write" >&2; exit 1; fi
  "$MOCK_BIN/python3.12" -c "print(1)" "$MOCK_HOME/.ssh/not-ak" "$TEST_DIR/tmp" "key" "line" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed wrong authorized-write target" >&2; exit 1; fi
  # Python host-parse on arbitrary sandbox file (wrong basename)
  test_py_temp=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/arbitrary.XXXXXX")
  "$MOCK_BIN/python3.12" -c "print(1)" "$test_py_temp" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed arbitrary host-parse target" >&2; exit 1; fi
  rm -f "$test_py_temp"
  # Python config-write temp with wrong basename
  test_py_cfg=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/not_config_suffix.XXXXXX")
  "$MOCK_BIN/python3.12" -c "print(1)" "$MOCK_HOME/.ssh/config" "$test_py_cfg" "block" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed config-write wrong basename" >&2; exit 1; fi
  rm -f "$test_py_cfg"
  # Python authorized-write temp with wrong basename
  test_py_ak=$(/usr/bin/mktemp "$MOCK_HOME/.ssh/not_ak_suffix.XXXXXX")
  "$MOCK_BIN/python3.12" -c "print(1)" "$MOCK_HOME/.ssh/authorized_keys" "$test_py_ak" "key" "line" >/dev/null 2>&1
  if [ $? -eq 0 ]; then echo "FAIL: python mock allowed authorized-write wrong basename" >&2; exit 1; fi
  rm -f "$test_py_ak"
  set -e
}
# Ensure MOCK_HOME/.ssh exists for verify_mock_contracts temp file tests
mkdir -p "$MOCK_HOME/.ssh"
verify_mock_contracts

# -----------------------------------------------------------------------------
# Test Helper Functions
# -----------------------------------------------------------------------------

reset_fixture() {
  # Clean mutable trees
  rm -rf "$MOCK_HOME" "$MOCK_ETC" "$MOCK_REPO" "$TEST_DIR/usr"
  # Restore from baseline
  mkdir -p "$MOCK_HOME" "$MOCK_ETC" "$MOCK_REPO" "$TEST_DIR/usr/local/sbin"
  cp -a "$BASELINE_DIR/home/astro" "$TEST_DIR/home"
  cp -a "$BASELINE_DIR/etc/solarsage" "$TEST_DIR/etc"
  cp -a "$BASELINE_DIR/opt/solarsage-astro" "$TEST_DIR/opt"

  # Wrapper path
  cp "$BASELINE_DIR/opt/solarsage-astro/infra/production/solarsage-github-deploy" "$MOCK_WRAPPER"
  chmod 755 "$MOCK_WRAPPER"

  # Setup live path substitutions
  TEST_SCRIPT="$TEST_DIR/prod-github-access.sh"
  # We copy first, then substitute paths
  cp "$REPO_ROOT/scripts/deploy/prod-github-access.sh" "$TEST_SCRIPT"
  sed -i \
    -e "s|^SSH_DIR=\"/home/astro/\.ssh\"$|SSH_DIR=\"$MOCK_HOME/.ssh\"|" \
    -e "s|^ACTIONS_PUB=\"/etc/solarsage/keys/github-actions-deploy.pub\"$|ACTIONS_PUB=\"$MOCK_ETC/keys/github-actions-deploy.pub\"|" \
    -e "s|^FORCED_WRAPPER=\"/usr/local/sbin/solarsage-github-deploy\"$|FORCED_WRAPPER=\"$MOCK_WRAPPER\"|" \
    -e "s|^REPO_DIR=\"/opt/solarsage-astro\"$|REPO_DIR=\"$MOCK_REPO\"|" \
    "$TEST_SCRIPT"

  # Fail-fast sanity check
  if ! grep -Fxq "SSH_DIR=\"$MOCK_HOME/.ssh\"" "$TEST_SCRIPT" || \
     ! grep -Fxq "REPO_DIR=\"$MOCK_REPO\"" "$TEST_SCRIPT" || \
     ! grep -Fxq "FORCED_WRAPPER=\"$MOCK_WRAPPER\"" "$TEST_SCRIPT" || \
     grep -Fq "$TEST_DIR$TEST_DIR" "$TEST_SCRIPT" || \
     grep -Fq 'MOCK_REPO_PLACEHOLDER' "$TEST_SCRIPT"; then
    echo "FAIL: Setup sanity check failed" >&2
    exit 1
  fi
  chmod +x "$TEST_SCRIPT"

  # Setup mock git origin state
  rm -f "$TEST_DIR/mock_origin"
  echo "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"

  # Reset variables
  export MOCK_UID=0
  export MOCK_USER=root
  export MOCK_STAT_OWNER=""
  export MOCK_BAD_OWNER_PATH=""
  export MOCK_BAD_MODE_PATH=""
  export MOCK_MV_FAIL_DEST=""
  export MOCK_CURL_STATUS="404"
  export MOCK_CURL_RC=0
  export MOCK_CURL_BODY_SENTINEL=""
  export MOCK_GIT_LS_REMOTE_RC=0
  unset MOCK_GIT_LS_REMOTE_OUT
  export MOCK_TIMEOUT_TRIGGER=0
  export MOCK_MKTEMP_FAIL_PREFIX=""
  export MOCK_PYTHON_FAIL_OP=""
  export MOCK_GIT_SET_URL_RC=0
  reset_audits
  return 0
}

reset_audits() {
  rm -f "$TEST_DIR/chown_audit.log" "$TEST_DIR/mv_audit.log" "$TEST_DIR/git_audit.log" "$TEST_DIR/curl_audit.log" "$TEST_DIR/ssh_keygen_audit.log" "$TEST_DIR/timeout_audit.log" "$TEST_DIR/git_forbidden.log" "$TEST_DIR/python_audit.log"
  rm -f "$TEST_DIR/case_stdout.log" "$TEST_DIR/case_stderr.log"
  return 0
}

prepare_installed_state() {
  local setup_label="$1"
  reset_fixture
  # Run apply silently
  set +e
  PATH="$MOCK_BIN:$PATH" "$TEST_SCRIPT" --apply > "$TEST_DIR/prep_stdout.log" 2> "$TEST_DIR/prep_stderr.log"
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    echo "FAIL: prepare_installed_state failed for $setup_label (got RC $rc)" >&2
    echo "PREP STDOUT saved at: $TEST_DIR/prep_stdout.log" >&2
    echo "PREP STDERR saved at: $TEST_DIR/prep_stderr.log" >&2
    exit 1
  fi
  reset_audits
  rm -f "$TEST_DIR/prep_stdout.log" "$TEST_DIR/prep_stderr.log"
  return 0
}

snapshot_mutable_state() {
  # Take state snapshot (hash + mode + existence) of config, authorized_keys, known_hosts.github, and origin
  rm -rf "$TEST_DIR/snapshot"
  mkdir -p "$TEST_DIR/snapshot"

  for item in config authorized_keys known_hosts.github; do
    local path="$MOCK_HOME/.ssh/$item"
    if [ -L "$path" ]; then
      echo "symlink" > "$TEST_DIR/snapshot/${item}.type"
      readlink "$path" > "$TEST_DIR/snapshot/${item}.target"
    elif [ -f "$path" ]; then
      echo "file" > "$TEST_DIR/snapshot/${item}.type"
      sha256sum "$path" | awk '{print $1}' > "$TEST_DIR/snapshot/${item}.hash"
      /usr/bin/stat -c "%a" "$path" > "$TEST_DIR/snapshot/${item}.mode"
    else
      echo "absent" > "$TEST_DIR/snapshot/${item}.type"
    fi
  done

  if [ -f "$TEST_DIR/mock_origin" ]; then
    echo "file" > "$TEST_DIR/snapshot/origin.type"
    cat "$TEST_DIR/mock_origin" > "$TEST_DIR/snapshot/origin.content"
  else
    echo "absent" > "$TEST_DIR/snapshot/origin.type"
  fi
  return 0
}

assert_mutable_state_unchanged() {
  # Verify files didn't change from snapshot (type, content, perms)
  for item in config authorized_keys known_hosts.github; do
    local path="$MOCK_HOME/.ssh/$item"
    local expected_type
    expected_type=$(cat "$TEST_DIR/snapshot/${item}.type")

    if [ "$expected_type" = "symlink" ]; then
      [ -L "$path" ] || { echo "FAIL: type of $item changed (expected symlink)" >&2; exit 1; }
      local expected_target
      expected_target=$(cat "$TEST_DIR/snapshot/${item}.target")
      [ "$(readlink "$path")" = "$expected_target" ] || { echo "FAIL: symlink target of $item changed" >&2; exit 1; }
    elif [ "$expected_type" = "file" ]; then
      [ -f "$path" ] && [ ! -L "$path" ] || { echo "FAIL: type of $item changed (expected file)" >&2; exit 1; }
      local expected_hash
      expected_hash=$(cat "$TEST_DIR/snapshot/${item}.hash")
      [ "$(sha256sum "$path" | awk '{print $1}')" = "$expected_hash" ] || { echo "FAIL: content of $item changed" >&2; exit 1; }
      local expected_mode
      expected_mode=$(cat "$TEST_DIR/snapshot/${item}.mode")
      [ "$(/usr/bin/stat -c "%a" "$path")" = "$expected_mode" ] || { echo "FAIL: mode of $item changed" >&2; exit 1; }
    else
      [ ! -e "$path" ] || { echo "FAIL: $item exists unexpectedly" >&2; exit 1; }
    fi
  done

  local expected_origin_type
  expected_origin_type=$(cat "$TEST_DIR/snapshot/origin.type")
  if [ "$expected_origin_type" = "file" ]; then
    [ -f "$TEST_DIR/mock_origin" ] || { echo "FAIL: origin type changed" >&2; exit 1; }
    local expected_origin_content
    expected_origin_content=$(cat "$TEST_DIR/snapshot/origin.content")
    [ "$(cat "$TEST_DIR/mock_origin")" = "$expected_origin_content" ] || { echo "FAIL: origin content changed" >&2; exit 1; }
  else
    [ ! -f "$TEST_DIR/mock_origin" ] || { echo "FAIL: origin created unexpectedly" >&2; exit 1; }
  fi
  return 0
}

assert_no_mutation_audit() {
  if [ -f "$TEST_DIR/chown_audit.log" ]; then
    echo "FAIL: chown mutation occurred unexpectedly" >&2
    exit 1
  fi
  if [ -f "$TEST_DIR/mv_audit.log" ]; then
    echo "FAIL: mv mutation occurred unexpectedly" >&2
    exit 1
  fi
  if [ -f "$TEST_DIR/git_audit.log" ]; then
    ! grep -q "set-url" "$TEST_DIR/git_audit.log" || { echo "FAIL: git origin mutation occurred unexpectedly" >&2; exit 1; }
  fi
  return 0
}

assert_no_forbidden_git() {
  if [ -f "$TEST_DIR/git_forbidden.log" ]; then
    echo "FAIL: forbidden git subcommand invoked" >&2
    exit 1
  fi
  return 0
}

# Verify exact read-only net call counts for NET cases
# remote_expected=1: ls-remote and timeout are called; 0: not called
assert_net_audit() {
  local remote_expected="$1"
  local curl_count=0
  local git_lines=0
  local get_url_count=0
  local set_url_count=0
  local ls_remote_count=0
  local timeout_count=0

  if [ -f "$TEST_DIR/curl_audit.log" ]; then
    curl_count=$(wc -l < "$TEST_DIR/curl_audit.log")
    if [ "$curl_count" -ne 1 ]; then
      echo "FAIL: assert_net_audit expected 1 curl call, got $curl_count" >&2
      exit 1
    fi
    if [ "$(head -1 "$TEST_DIR/curl_audit.log")" != "curl" ]; then
      echo "FAIL: assert_net_audit unexpected curl content" >&2
      exit 1
    fi
  else
    echo "FAIL: assert_net_audit curl_audit.log missing" >&2
    exit 1
  fi

  if [ -f "$TEST_DIR/git_audit.log" ]; then
    git_lines=$(wc -l < "$TEST_DIR/git_audit.log")
    get_url_count=$(grep -c "get-url" "$TEST_DIR/git_audit.log" || true)
    set_url_count=$(grep -c "set-url" "$TEST_DIR/git_audit.log" || true)
    ls_remote_count=$(grep -c "ls-remote" "$TEST_DIR/git_audit.log" || true)
  fi

  if [ "$get_url_count" -ne 1 ]; then
    echo "FAIL: assert_net_audit expected 1 git get-url call, got $get_url_count" >&2
    exit 1
  fi
  if [ "$set_url_count" -ne 0 ]; then
    echo "FAIL: assert_net_audit unexpected git set-url call" >&2
    exit 1
  fi
  if [ "$ls_remote_count" -ne "$remote_expected" ]; then
    echo "FAIL: assert_net_audit expected $remote_expected ls-remote, got $ls_remote_count" >&2
    exit 1
  fi

  # Expected total git lines: 1 get-url + remote_expected ls-remote
  local expected_git_lines=$((1 + remote_expected))
  if [ "$git_lines" -ne "$expected_git_lines" ]; then
    echo "FAIL: assert_net_audit expected $expected_git_lines total git lines, got $git_lines" >&2
    exit 1
  fi

  if [ -f "$TEST_DIR/timeout_audit.log" ]; then
    timeout_count=$(wc -l < "$TEST_DIR/timeout_audit.log")
  fi
  if [ "$timeout_count" -ne "$remote_expected" ]; then
    echo "FAIL: assert_net_audit expected $remote_expected timeout calls, got $timeout_count" >&2
    exit 1
  fi
  if [ "$remote_expected" -eq 1 ] && [ -f "$TEST_DIR/timeout_audit.log" ]; then
    if [ "$(head -1 "$TEST_DIR/timeout_audit.log")" != "timeout" ]; then
      echo "FAIL: assert_net_audit unexpected timeout content" >&2
      exit 1
    fi
  fi

  assert_no_forbidden_git
  return 0
}

assert_no_temp_files() {
  # Verify no temp files left in $TEST_DIR
  local temp_left
  temp_left=$(find "$TEST_DIR" \( -name "validation.??????" -o -name "known_hosts.github.??????" -o -name "config.??????" -o -name "authorized_keys.??????" \) -print -quit)
  if [ -n "$temp_left" ]; then
    echo "FAIL: temp files left in sandbox: $temp_left" >&2
    exit 1
  fi
  return 0
}

assert_output_safe() {
  local out_file="$TEST_DIR/outputs/$LAST_CASE_ID.stdout"
  local err_file="$TEST_DIR/outputs/$LAST_CASE_ID.stderr"

  for f in "$out_file" "$err_file"; do
    if [ -f "$f" ]; then
      # We check for key material or credential leaks.
      if grep -Fq "$CREDENTIAL_SENTINEL" "$f"; then
        echo "FAIL: credentials leaked in logs: $f" >&2
        exit 1
      fi
      if grep -Fq "$API_BODY_SENTINEL_R13" "$f"; then
        echo "FAIL: API body leaked in logs: $f" >&2
        exit 1
      fi
      if grep -Fq "$MALFORMED_REMOTE_SENTINEL_R13" "$f"; then
        echo "FAIL: malformed remote output leaked in logs: $f" >&2
        exit 1
      fi
      if grep -Fq "$ENV_SECRET_SENTINEL_R13" "$f"; then
        echo "FAIL: env secrets leaked in logs: $f" >&2
        exit 1
      fi
    fi
  done
  return 0
}

run_case() {
  local expected_rc="$1"
  local case_id="$2"
  local label="$3"
  shift 3

  # Regex ID verification
  if [[ ! "$case_id" =~ ^[A-Z0-9_-]+$ ]]; then
    echo "FAIL: Invalid Case ID format: $case_id" >&2
    exit 1
  fi

  # Duplicate check
  if grep -Fxq "$case_id" "$TEST_DIR/case_ids" 2>/dev/null; then
    echo "FAIL: Duplicate Case ID detected: $case_id" >&2
    exit 1
  fi
  echo "$case_id" >> "$TEST_DIR/case_ids"

  CASE_COUNT=$((CASE_COUNT + 1))
  export LAST_CASE_ID="$case_id"
  mkdir -p "$TEST_DIR/outputs"

  # Run the target command using child PATH prioritization
  set +e
  PATH="$MOCK_BIN:$PATH" "$@" > "$TEST_DIR/outputs/$case_id.stdout" 2> "$TEST_DIR/outputs/$case_id.stderr"
  local rc=$?
  set -e

  if [ "$rc" -ne "$expected_rc" ]; then
    echo "FAIL: $case_id $label (expected RC $expected_rc, got $rc)" >&2
    # Do not print raw files directly to avoid leakage
    echo "Diagnostics output files saved at outputs/$case_id.stdout|stderr" >&2
    exit 1
  fi

  assert_output_safe
  echo "PASS: $case_id $label"
}

# -----------------------------------------------------------------------------
# Canonical expected state reference (built once, not counted in CASE_COUNT)
# -----------------------------------------------------------------------------
CANON_DIR="$TEST_DIR/canonical"
build_canonical_state_ref() {
  rm -rf "$CANON_DIR"
  mkdir -p "$CANON_DIR"
  reset_fixture
  set +e
  PATH="$MOCK_BIN:$PATH" "$TEST_SCRIPT" --apply > "$TEST_DIR/canon_build_stdout.log" 2> "$TEST_DIR/canon_build_stderr.log"
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    echo "FAIL: canonical state build failed (rc $rc)" >&2
    echo "STDOUT saved: $TEST_DIR/canon_build_stdout.log" >&2
    echo "STDERR saved: $TEST_DIR/canon_build_stderr.log" >&2
    exit 1
  fi
  # Save canonical bytes, mode, and non-symlink status for each destination
  for item in known_hosts.github config authorized_keys; do
    local path="$MOCK_HOME/.ssh/$item"
    if [ -f "$path" ] && [ ! -L "$path" ]; then
      cp "$path" "$CANON_DIR/$item.bytes"
      /usr/bin/stat -c "%a" "$path" > "$CANON_DIR/$item.mode"
    else
      echo "FAIL: canonical $item is not a regular file" >&2
      exit 1
    fi
  done
  # Save canonical origin
  if [ -f "$TEST_DIR/mock_origin" ]; then
    cat "$TEST_DIR/mock_origin" > "$CANON_DIR/origin.content"
  else
    echo "FAIL: canonical origin missing" >&2
    exit 1
  fi
  rm -f "$TEST_DIR/canon_build_stdout.log" "$TEST_DIR/canon_build_stderr.log"
}

# Assert no "Successfully applied" message in FAIL case outputs
assert_fail_no_success() {
  local out_file="$TEST_DIR/outputs/$LAST_CASE_ID.stdout"
  local err_file="$TEST_DIR/outputs/$LAST_CASE_ID.stderr"
  for f in "$out_file" "$err_file"; do
    if [ -f "$f" ] && grep -Fq "Successfully applied" "$f"; then
      echo "FAIL: FAIL case $LAST_CASE_ID contains success message" >&2
      exit 1
    fi
  done
}

# Assert destination contract for FAIL cases: each destination is either canonical
# full bytes+mode+regular-non-symlink OR equal to old snapshot (absent or old bytes/mode)
assert_fail_dest_contract() {
  for item in known_hosts.github config authorized_keys; do
    local path="$MOCK_HOME/.ssh/$item"
    local snap_type=""
    local snap_hash=""
    local snap_mode=""
    if [ -f "$TEST_DIR/snapshot/${item}.type" ]; then
      snap_type=$(cat "$TEST_DIR/snapshot/${item}.type")
    fi
    if [ -f "$TEST_DIR/snapshot/${item}.hash" ]; then
      snap_hash=$(cat "$TEST_DIR/snapshot/${item}.hash")
    fi
    if [ -f "$TEST_DIR/snapshot/${item}.mode" ]; then
      snap_mode=$(cat "$TEST_DIR/snapshot/${item}.mode")
    fi

    # Current state
    if [ -L "$path" ]; then
      echo "FAIL: FAIL case $LAST_CASE_ID destination $item is symlink" >&2
      exit 1
    fi
    if [ ! -f "$path" ] && [ "$snap_type" = "absent" ]; then
      # Both absent — OK
      continue
    fi
    if [ -f "$path" ] && [ ! -L "$path" ]; then
      local cur_hash
      cur_hash=$(sha256sum "$path" | awk '{print $1}')
      local cur_mode
      cur_mode=$(/usr/bin/stat -c "%a" "$path")
      # Check if matches canonical
      if [ -f "$CANON_DIR/$item.bytes" ]; then
        local canon_hash
        canon_hash=$(sha256sum "$CANON_DIR/$item.bytes" | awk '{print $1}')
        local canon_mode
        canon_mode=$(cat "$CANON_DIR/$item.mode")
        if [ "$cur_hash" = "$canon_hash" ] && [ "$cur_mode" = "$canon_mode" ]; then
          # Canonical state — OK
          continue
        fi
      fi
      # Check if matches old snapshot
      if [ "$snap_type" = "file" ] && [ "$cur_hash" = "$snap_hash" ] && [ "$cur_mode" = "$snap_mode" ]; then
        # Unchanged from old state — OK
        continue
      fi
      echo "FAIL: FAIL case $LAST_CASE_ID destination $item does not match canonical or old state" >&2
      exit 1
    fi
    # File exists but was absent in snapshot — must match canonical
    if [ -f "$path" ] && [ "$snap_type" = "absent" ]; then
      local cur_hash
      cur_hash=$(sha256sum "$path" | awk '{print $1}')
      local canon_hash
      canon_hash=$(sha256sum "$CANON_DIR/$item.bytes" | awk '{print $1}')
      if [ "$cur_hash" != "$canon_hash" ]; then
        echo "FAIL: FAIL case $LAST_CASE_ID destination $item created but not canonical" >&2
        exit 1
      fi
      continue
    fi
    # File absent but was present — must have been deliberately removed
    if [ ! -f "$path" ] && [ "$snap_type" = "file" ]; then
      echo "FAIL: FAIL case $LAST_CASE_ID destination $item deleted unexpectedly" >&2
      exit 1
    fi
  done
}

# Assert origin contract for FAIL cases
assert_fail_origin_contract() {
  local allow_canonical="${1:-0}"
  local snap_origin_type
  snap_origin_type=$(cat "$TEST_DIR/snapshot/origin.type" 2>/dev/null || echo "absent")
  local cur_origin=""
  if [ -f "$TEST_DIR/mock_origin" ]; then
    cur_origin=$(cat "$TEST_DIR/mock_origin")
  fi
  if [ "$snap_origin_type" = "absent" ] && [ -z "$cur_origin" ]; then
    return 0  # Both absent
  fi
  if [ -z "$cur_origin" ] && [ "$snap_origin_type" = "file" ]; then
    echo "FAIL: FAIL case $LAST_CASE_ID origin deleted unexpectedly" >&2
    exit 1
  fi
  local canon_origin
  canon_origin=$(cat "$CANON_DIR/origin.content" 2>/dev/null || echo "")
  if [ "$cur_origin" = "$canon_origin" ]; then
    return 0  # Canonical origin
  fi
  local snap_origin
  snap_origin=$(cat "$TEST_DIR/snapshot/origin.content" 2>/dev/null || echo "")
  if [ "$cur_origin" = "$snap_origin" ]; then
    return 0  # Old origin
  fi
  echo "FAIL: FAIL case $LAST_CASE_ID origin changed unexpectedly" >&2
  exit 1
}

# Assert audit for FAIL cases: only allowable attempts
assert_fail_audit() {
  if [ -f "$TEST_DIR/git_forbidden.log" ]; then
    echo "FAIL: FAIL case $LAST_CASE_ID has forbidden git" >&2
    exit 1
  fi
}

# Assert full canonical installed state after _REC
assert_rec_full_state() {
  for item in known_hosts.github config authorized_keys; do
    local path="$MOCK_HOME/.ssh/$item"
    if [ ! -f "$path" ] || [ -L "$path" ]; then
      echo "FAIL: REC case $LAST_CASE_ID $item not a regular file" >&2
      exit 1
    fi
    local cur_hash
    cur_hash=$(sha256sum "$path" | awk '{print $1}')
    local canon_hash
    canon_hash=$(sha256sum "$CANON_DIR/$item.bytes" | awk '{print $1}')
    if [ "$cur_hash" != "$canon_hash" ]; then
      echo "FAIL: REC case $LAST_CASE_ID $item bytes mismatch" >&2
      exit 1
    fi
    local cur_mode
    cur_mode=$(/usr/bin/stat -c "%a" "$path")
    local canon_mode
    canon_mode=$(cat "$CANON_DIR/$item.mode")
    if [ "$cur_mode" != "$canon_mode" ]; then
      echo "FAIL: REC case $LAST_CASE_ID $item mode $cur_mode != expected $canon_mode" >&2
      exit 1
    fi
  done
  local canon_origin
  canon_origin=$(cat "$CANON_DIR/origin.content" 2>/dev/null || echo "")
  local cur_origin
  cur_origin=$(cat "$TEST_DIR/mock_origin" 2>/dev/null || echo "")
  if [ "$cur_origin" != "$canon_origin" ]; then
    echo "FAIL: REC case $LAST_CASE_ID origin mismatch" >&2
    exit 1
  fi
}

# -----------------------------------------------------------------------------
# Execute Cases
# -----------------------------------------------------------------------------

# CLI / user boundary
reset_fixture
snapshot_mutable_state
run_case 2 "CLI01" "no args" "$TEST_SCRIPT"
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI02" "unknown flag" "$TEST_SCRIPT" --unknown
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI03" "apply + preflight" "$TEST_SCRIPT" --apply --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI04" "preflight + check" "$TEST_SCRIPT" --preflight --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI05" "duplicate same action" "$TEST_SCRIPT" --apply --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI06" "expected-sha missing value" "$TEST_SCRIPT" --check --expected-sha
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI07" "expected-sha without check" "$TEST_SCRIPT" --apply --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI08" "duplicate expected-sha" "$TEST_SCRIPT" --check --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2 --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI09" "short SHA" "$TEST_SCRIPT" --check --expected-sha a1b2
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI10" "long SHA" "$TEST_SCRIPT" --check --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI11" "uppercase SHA" "$TEST_SCRIPT" --check --expected-sha A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 2 "CLI12" "non-hex SHA" "$TEST_SCRIPT" --check --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1bZ
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 1 "CLI13" "non-root apply" env MOCK_UID=1000 MOCK_USER=astro "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 1 "CLI14" "preflight wrong user" env MOCK_UID=0 MOCK_USER=root "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
run_case 1 "CLI15" "check wrong user" env MOCK_UID=0 MOCK_USER=root "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - .ssh
reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_HOME/.ssh"
run_case 1 "PATH01" ".ssh missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_HOME/.ssh"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh"
run_case 1 "PATH02" ".ssh symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_HOME/.ssh"
touch "$MOCK_HOME/.ssh"
run_case 1 "PATH03" ".ssh regular file" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="home/astro/.ssh"
run_case 1 "PATH04" ".ssh wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="home/astro/.ssh"
run_case 1 "PATH05" ".ssh wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - checkout private key
reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
run_case 1 "PATH06" "checkout private missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
run_case 1 "PATH07" "checkout private symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
mkfifo "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
run_case 1 "PATH08" "checkout private FIFO" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
mkdir "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
run_case 1 "PATH09" "checkout private directory" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="solarsage_prod_server_ed25519"
run_case 1 "PATH10" "checkout private wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="solarsage_prod_server_ed25519"
run_case 1 "PATH11" "checkout private wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - checkout public key
reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "PATH12" "checkout public missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "PATH13" "checkout public symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
mkfifo "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "PATH14" "checkout public FIFO" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
mkdir "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "PATH15" "checkout public directory" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="solarsage_prod_server_ed25519.pub"
run_case 1 "PATH16" "checkout public wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="solarsage_prod_server_ed25519.pub"
run_case 1 "PATH17" "checkout public wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - Actions public key
reset_fixture
snapshot_mutable_state
rm -f "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "PATH18" "Actions public missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_ETC/keys/github-actions-deploy.pub"
ln -s "$TEST_DIR" "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "PATH19" "Actions public symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_ETC/keys/github-actions-deploy.pub"
mkfifo "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "PATH20" "Actions public FIFO" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_ETC/keys/github-actions-deploy.pub"
mkdir "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "PATH21" "Actions public directory" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="github-actions-deploy.pub"
run_case 1 "PATH22" "Actions public wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="github-actions-deploy.pub"
run_case 1 "PATH23" "Actions public wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - Wrapper
reset_fixture
snapshot_mutable_state
rm -f "$MOCK_WRAPPER"
run_case 1 "PATH24" "Wrapper missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_WRAPPER"
ln -s "$TEST_DIR" "$MOCK_WRAPPER"
run_case 1 "PATH25" "Wrapper symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_WRAPPER"
mkdir "$MOCK_WRAPPER"
run_case 1 "PATH26" "Wrapper directory" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="solarsage-github-deploy"
run_case 1 "PATH27" "Wrapper wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="solarsage-github-deploy"
run_case 1 "PATH28" "Wrapper wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "mismatch" > "$MOCK_WRAPPER"
run_case 1 "PATH29" "Wrapper byte mismatch" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - Known-hosts template
reset_fixture
snapshot_mutable_state
rm -f "$MOCK_REPO/infra/ssh/github.com.known_hosts"
run_case 1 "PATH30" "Known-hosts template missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_REPO/infra/ssh/github.com.known_hosts"
ln -s "$TEST_DIR" "$MOCK_REPO/infra/ssh/github.com.known_hosts"
run_case 1 "PATH31" "Known-hosts template symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -f "$MOCK_REPO/infra/ssh/github.com.known_hosts"
mkdir "$MOCK_REPO/infra/ssh/github.com.known_hosts"
run_case 1 "PATH32" "Known-hosts template directory" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_MODE_PATH="github.com.known_hosts"
run_case 1 "PATH33" "Known-hosts template wrong mode" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
export MOCK_BAD_OWNER_PATH="github.com.known_hosts"
run_case 1 "PATH34" "Known-hosts template wrong owner" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "mismatch" > "$MOCK_REPO/infra/ssh/github.com.known_hosts"
run_case 1 "PATH35" "Known-hosts template changed bytes" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Path/type/mode/owner boundary - Repo
reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_REPO"
run_case 1 "PATH36" "Repo directory missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_REPO"
ln -s "$TEST_DIR" "$MOCK_REPO"
run_case 1 "PATH37" "Repo directory symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_REPO/.git"
run_case 1 "PATH38" ".git missing" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
rm -rf "$MOCK_REPO/.git"
ln -s "$TEST_DIR" "$MOCK_REPO/.git"
run_case 1 "PATH39" ".git symlink" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Installed state checks
prepare_installed_state "PATH40 prep"
snapshot_mutable_state
echo "mismatch" > "$MOCK_HOME/.ssh/known_hosts.github"
snapshot_mutable_state # Update snapshot to corrupted state
run_case 1 "PATH40" "Installed known-hosts changed" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Nine separate installed state checks (R13 B3 R2 requirement)
prepare_installed_state "PATH41_SYMLINK prep"
rm -f "$MOCK_HOME/.ssh/known_hosts.github"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh/known_hosts.github"
snapshot_mutable_state
run_case 1 "PATH41_SYMLINK" "Installed known-hosts symlink" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

prepare_installed_state "PATH41_MODE prep"
export MOCK_BAD_MODE_PATH="known_hosts.github"
snapshot_mutable_state
run_case 1 "PATH41_MODE" "Installed known-hosts wrong mode" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_MODE_PATH=""

prepare_installed_state "PATH41_OWNER prep"
export MOCK_BAD_OWNER_PATH="known_hosts.github"
snapshot_mutable_state
run_case 1 "PATH41_OWNER" "Installed known-hosts wrong owner" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_OWNER_PATH=""

prepare_installed_state "PATH42_SYMLINK prep"
rm -f "$MOCK_HOME/.ssh/config"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "PATH42_SYMLINK" "Installed config symlink" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

prepare_installed_state "PATH42_MODE prep"
export MOCK_BAD_MODE_PATH="config"
snapshot_mutable_state
run_case 1 "PATH42_MODE" "Installed config wrong mode" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_MODE_PATH=""

prepare_installed_state "PATH42_OWNER prep"
export MOCK_BAD_OWNER_PATH="config"
snapshot_mutable_state
run_case 1 "PATH42_OWNER" "Installed config wrong owner" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_OWNER_PATH=""

prepare_installed_state "PATH43_SYMLINK prep"
rm -f "$MOCK_HOME/.ssh/authorized_keys"
ln -s "$TEST_DIR" "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "PATH43_SYMLINK" "Installed authorized_keys symlink" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

prepare_installed_state "PATH43_MODE prep"
export MOCK_BAD_MODE_PATH="authorized_keys"
snapshot_mutable_state
run_case 1 "PATH43_MODE" "Installed authorized_keys wrong mode" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_MODE_PATH=""

prepare_installed_state "PATH43_OWNER prep"
export MOCK_BAD_OWNER_PATH="authorized_keys"
snapshot_mutable_state
run_case 1 "PATH43_OWNER" "Installed authorized_keys wrong owner" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_BAD_OWNER_PATH=""

# Key validation
reset_fixture
snapshot_mutable_state
run_case 0 "KEY01" "Matching checkout pair passes" "$TEST_SCRIPT" --apply

reset_fixture
snapshot_mutable_state
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINOMATCH" > "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "KEY02" "Checkout public mismatch fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
cp "$TEST_DIR/passphrase_key" "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
cp "$TEST_DIR/passphrase_key.pub" "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "KEY03" "Passphrase private key fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "malformed" > "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519"
run_case 1 "KEY04" "Malformed private fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "malformed" > "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "KEY05" "Malformed public fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo -e "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI" > "$MOCK_HOME/.ssh/solarsage_prod_server_ed25519.pub"
run_case 1 "KEY06" "Checkout public two lines fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Actions public key variants
reset_fixture
snapshot_mutable_state
run_case 0 "KEY07" "Exact valid Actions key LF passes" "$TEST_SCRIPT" --apply

reset_fixture
snapshot_mutable_state
echo -n "" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY08" "Actions key: empty" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo -e "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI\n" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY09" "Actions key: extra blank line" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo -e "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI\r" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY10" "Actions key: CRLF" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo -e "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY11" "Actions key: two lines" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY12" "Actions key: options prefix" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "ssh-rsa AAAAB3NzaC1yc2E..." > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY13" "Actions key: wrong key type" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "ssh-ed25519 invalidbase64!" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY14" "Actions key: invalid base64" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo "--- BEGIN OPENSSH PRIVATE KEY ---" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY15" "Actions key: PEM material" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
snapshot_mutable_state
echo -n "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI" > "$MOCK_ETC/keys/github-actions-deploy.pub"
run_case 1 "KEY16" "Actions key: no final LF" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# Config contract
reset_fixture
snapshot_mutable_state
run_case 0 "CFG01" "Config absent -> first apply" "$TEST_SCRIPT" --apply

reset_fixture
echo "Host unrelated" > "$MOCK_HOME/.ssh/config"
echo "  HostName 1.1.1.1" >> "$MOCK_HOME/.ssh/config"
echo "Host unrelated-suffix" >> "$MOCK_HOME/.ssh/config"
echo "  HostName 2.2.2.2" >> "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
# Capture config before apply
cp "$MOCK_HOME/.ssh/config" "$TEST_DIR/cfg02_expected"
run_case 0 "CFG02" "Config unrelated bytes preserved" "$TEST_SCRIPT" --apply
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
# Production script appends canonical block at end (no existing markers)
echo "$expected_block" >> "$TEST_DIR/cfg02_expected"
if ! cmp -s "$MOCK_HOME/.ssh/config" "$TEST_DIR/cfg02_expected"; then
  echo "FAIL: CFG02 config bytes mismatch" >&2
  exit 1
fi

prepare_installed_state "CFG03 prep"
snapshot_mutable_state
run_case 0 "CFG03" "Second apply byte-identical" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged

reset_fixture
echo -e "# BEGIN SOLARSAGE-PROD-GITHUB\n# BEGIN SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG04" "Config duplicate BEGIN" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "# END SOLARSAGE-PROD-GITHUB\n# END SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG05" "Config duplicate END" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "# BEGIN SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG06" "Config unmatched BEGIN" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "# END SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG07" "Config unmatched END" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "# END SOLARSAGE-PROD-GITHUB\n# BEGIN SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG08" "Config END before BEGIN" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "Host github.com-solarsage-prod" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG09" "Config alias outside managed block" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "host github.com-solarsage-prod" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG10" "Config lowercase alias outside block" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "Host github.com github.com-solarsage-prod github.com-other" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG11" "Config alias among multiple Host patterns" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "# BEGIN SOLARSAGE-PROD-GITHUB\nHost github.com-solarsage-prod\n  HostName modified.com\n# END SOLARSAGE-PROD-GITHUB" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG12" "Config modified managed block" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -n "Host unrelated" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 1 "CFG13" "Config non-empty without final LF" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "# Comment containing github.com-solarsage-prod alias" > "$MOCK_HOME/.ssh/config"
chmod 600 "$MOCK_HOME/.ssh/config"
snapshot_mutable_state
run_case 0 "CFG14" "Config comment containing alias" "$TEST_SCRIPT" --apply

# CFG15 - python parser crash handling
prepare_installed_state "CFG15 prep"
snapshot_mutable_state
export MOCK_PYTHON_FAIL_OP="host-parse"
run_case 1 "CFG15" "python host-parse crash fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git
export MOCK_PYTHON_FAIL_OP=""

# authorized_keys contract
reset_fixture
snapshot_mutable_state
run_case 0 "AK01" "authorized_keys absent -> first apply" "$TEST_SCRIPT" --apply

reset_fixture
echo "ssh-rsa AAAAB3NzaC1yc2E... otherkey" > "$MOCK_HOME/.ssh/authorized_keys"
echo "ssh-rsa AAAAB3NzaC1yc2E... otherkey-suffix" >> "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
cp "$MOCK_HOME/.ssh/authorized_keys" "$TEST_DIR/ak02_expected"
run_case 0 "AK02" "authorized_keys unrelated preserved" "$TEST_SCRIPT" --apply
actions_type=$(awk '{print $1}' "$MOCK_ETC/keys/github-actions-deploy.pub")
actions_base64=$(awk '{print $2}' "$MOCK_ETC/keys/github-actions-deploy.pub")
expected_forced_line="restrict,command=\"$MOCK_WRAPPER\" $actions_type $actions_base64 solarsage-github-actions-prod"
echo "$expected_forced_line" >> "$TEST_DIR/ak02_expected"
if ! cmp -s "$MOCK_HOME/.ssh/authorized_keys" "$TEST_DIR/ak02_expected"; then
  echo "FAIL: AK02 authorized_keys bytes mismatch" >&2
  exit 1
fi

prepare_installed_state "AK03 prep"
snapshot_mutable_state
run_case 0 "AK03" "Second apply byte-identical keys" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged

reset_fixture
# We write the expected canonical line manually
actions_type=$(awk '{print $1}' "$MOCK_ETC/keys/github-actions-deploy.pub")
actions_base64=$(awk '{print $2}' "$MOCK_ETC/keys/github-actions-deploy.pub")
expected_forced_line="restrict,command=\"$MOCK_WRAPPER\" $actions_type $actions_base64 solarsage-github-actions-prod"
echo "$expected_forced_line" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 0 "AK04" "One canonical forced line passes" "$TEST_SCRIPT" --apply

reset_fixture
echo "restrict,command=$MOCK_WRAPPER $actions_type $actions_base64 solarsage-github-actions-prod" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK05" "Unquoted command variant fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "$actions_type $actions_base64 solarsage-github-actions-prod" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK06" "Same key unrestricted fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "$expected_forced_line\n$expected_forced_line" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK07" "Duplicate exact canonical line fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -e "$expected_forced_line\n$actions_type $actions_base64 other-comment" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK08" "Same key in two forms fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "restrict,command=\"$MOCK_WRAPPER\" $actions_type DIFFERENTBASE64 solarsage-github-actions-prod" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK09" "Canonical comment with different key fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo -n "ssh-rsa AAAAB3NzaC1yc2E... otherkey" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
run_case 1 "AK10" "authorized_keys non-empty no-final-LF fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
# Hostile comment with glob expansion
echo "ssh-rsa AAAAB3NzaC1yc2E... *.*" > "$MOCK_HOME/.ssh/authorized_keys"
chmod 600 "$MOCK_HOME/.ssh/authorized_keys"
snapshot_mutable_state
cp "$MOCK_HOME/.ssh/authorized_keys" "$TEST_DIR/ak11_expected"
run_case 0 "AK11" "Hostile comment glob chars do not expand" "$TEST_SCRIPT" --apply
actions_type=$(awk '{print $1}' "$MOCK_ETC/keys/github-actions-deploy.pub")
actions_base64=$(awk '{print $2}' "$MOCK_ETC/keys/github-actions-deploy.pub")
expected_forced_line="restrict,command=\"$MOCK_WRAPPER\" $actions_type $actions_base64 solarsage-github-actions-prod"
echo "$expected_forced_line" >> "$TEST_DIR/ak11_expected"
if ! cmp -s "$MOCK_HOME/.ssh/authorized_keys" "$TEST_DIR/ak11_expected"; then
  echo "FAIL: AK11 authorized_keys bytes mismatch" >&2
  exit 1
fi

# Origin contract
reset_fixture
echo "https://github.com/basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 0 "ORIGIN01" "HTTPS origin normalizes once" "$TEST_SCRIPT" --apply
if [ "$(cat "$TEST_DIR/mock_origin")" != "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" ]; then
  echo "FAIL: ORIGIN01 normalization mismatch" >&2
  exit 1
fi
# Verify exact count = 1 set-url
set_url_count=$(grep -c "set-url" "$TEST_DIR/git_audit.log" || true)
if [ "$set_url_count" -ne 1 ]; then
  echo "FAIL: ORIGIN01 git set-url count is $set_url_count, expected 1" >&2
  exit 1
fi

reset_fixture
echo "git@github.com:basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 0 "ORIGIN02" "Old SSH origin normalizes once" "$TEST_SCRIPT" --apply
if [ "$(cat "$TEST_DIR/mock_origin")" != "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" ]; then
  echo "FAIL: ORIGIN02 normalization mismatch" >&2
  exit 1
fi
set_url_count=$(grep -c "set-url" "$TEST_DIR/git_audit.log" || true)
if [ "$set_url_count" -ne 1 ]; then
  echo "FAIL: ORIGIN02 git set-url count is $set_url_count, expected 1" >&2
  exit 1
fi

reset_fixture
echo "git@github.com-solarsage-prod:basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 0 "ORIGIN03" "Already normalized origin remains exact" "$TEST_SCRIPT" --apply
set_url_count=$(grep -c "set-url" "$TEST_DIR/git_audit.log" || true)
# Normalized form: redundancy zero or exactly one
if [ "$set_url_count" -gt 1 ]; then
  echo "FAIL: ORIGIN03 redundant set-url call" >&2
  exit 1
fi

reset_fixture
echo "git@github.com-solarsage-prod:wrongowner/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 1 "ORIGIN04" "Wrong owner fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "git@github.com-solarsage-prod:basilivanov/wrongrepo.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 1 "ORIGIN05" "Wrong repo fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "https://token@github.com/basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 1 "ORIGIN06" "Credential URL fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
echo "ftp://github.com/basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 1 "ORIGIN07" "Unknown host/scheme fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

reset_fixture
rm -f "$TEST_DIR/mock_origin"
snapshot_mutable_state
run_case 1 "ORIGIN08" "Missing origin fails" "$TEST_SCRIPT" --apply
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_no_forbidden_git

# NET exact read-only cases
prepare_installed_state "NET prep"
export MOCK_UID=1000
export MOCK_USER=astro

# NET01
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="200"
run_case 0 "NET01" "preflight API 200 warning" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1

# NET02
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="404"
run_case 0 "NET02" "preflight API 404 private succeeds" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1

# NET03
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="403"
run_case 1 "NET03" "preflight API 403 fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0

# NET04
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="429"
run_case 1 "NET04" "preflight API 429 fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0

# NET05
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="500"
run_case 1 "NET05" "preflight API 500 fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0

# NET06
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="503"
run_case 1 "NET06" "preflight API 503 fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0

# NET07
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="invalid"
run_case 1 "NET07" "preflight invalid status fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0

# NET08_NONZERO
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="404"
export MOCK_CURL_RC=1
run_case 1 "NET08_NONZERO" "preflight curl nonzero fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_RC=0

# NET08_TIMEOUT
reset_audits
snapshot_mutable_state
export MOCK_CURL_RC=28
run_case 1 "NET08_TIMEOUT" "preflight curl timeout fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_RC=0

# NET09
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_RC=1
run_case 1 "NET09" "preflight ls-remote nonzero fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
export MOCK_GIT_LS_REMOTE_RC=0

# NET10 — timeout simulation: MOCK_TIMEOUT_TRIGGER handled by git mock (exit 124)
reset_audits
snapshot_mutable_state
export MOCK_TIMEOUT_TRIGGER=1
run_case 1 "NET10" "preflight ls-remote timeout fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
export MOCK_TIMEOUT_TRIGGER=0

# NET11
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=""
run_case 1 "NET11" "preflight empty output fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET12
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\trefs/heads/main\na1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\trefs/heads/main'
run_case 1 "NET12" "preflight two output lines fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET13 — include MALFORMED_REMOTE_SENTINEL in git ls-remote output
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\trefs/heads/other\n'"$MALFORMED_REMOTE_SENTINEL_R13"$'\trefs/heads/main'
run_case 1 "NET13" "preflight wrong ref fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET14
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2   refs/heads/main"
run_case 1 "NET14" "preflight spaces instead of TAB fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET15
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2\trefs/heads/main'
run_case 1 "NET15" "preflight uppercase SHA fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET16
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'a1b2\trefs/heads/main'
run_case 1 "NET16" "preflight short SHA fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET17
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4\trefs/heads/main'
run_case 1 "NET17" "preflight long SHA fails" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET18
reset_audits
snapshot_mutable_state
export MOCK_GIT_LS_REMOTE_OUT=$'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\trefs/heads/main'
run_case 0 "NET18" "preflight exact remote line passes" "$TEST_SCRIPT" --preflight
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1
unset MOCK_GIT_LS_REMOTE_OUT

# NET19
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="200"
run_case 1 "NET19" "check API 200 fails" "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_STATUS="404"

# NET20
reset_audits
snapshot_mutable_state
run_case 0 "NET20" "check API 404 + remote passes" "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1

# NET21 invalid checks — explicit cases (underscore, not dash, to match handoff)
for s in 403 429 500 503; do
  reset_audits
  snapshot_mutable_state
  export MOCK_CURL_STATUS="$s"
  run_case 1 "NET21_$s" "check API $s fails" "$TEST_SCRIPT" --check
  assert_mutable_state_unchanged
  assert_no_mutation_audit
  assert_net_audit 0
done
export MOCK_CURL_STATUS="404"

# NET21_INVALID
reset_audits
snapshot_mutable_state
export MOCK_CURL_STATUS="invalid"
run_case 1 "NET21_INVALID" "check invalid HTTP status fails" "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_STATUS="404"

# NET21_CURL
reset_audits
snapshot_mutable_state
export MOCK_CURL_RC=1
run_case 1 "NET21_CURL" "check curl nonzero fails" "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_RC=0

# NET21_TIMEOUT — include API_BODY sentinel in curl stderr (via MOCK_CURL_BODY_SENTINEL)
reset_audits
snapshot_mutable_state
export MOCK_CURL_RC=28
export MOCK_CURL_BODY_SENTINEL="$API_BODY_SENTINEL_R13"
run_case 1 "NET21_TIMEOUT" "check curl timeout fails" "$TEST_SCRIPT" --check
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 0
export MOCK_CURL_RC=0
export MOCK_CURL_BODY_SENTINEL=""

# NET22
reset_audits
snapshot_mutable_state
run_case 0 "NET22" "check expected SHA match passes" "$TEST_SCRIPT" --check --expected-sha a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1

# NET23
reset_audits
snapshot_mutable_state
run_case 1 "NET23" "check expected SHA mismatch fails" "$TEST_SCRIPT" --check --expected-sha ffffffffffffffffffffffffffffffffffffffff
assert_mutable_state_unchanged
assert_no_mutation_audit
assert_net_audit 1

# Restore UID/USER to root for mutation checks
export MOCK_UID=0
export MOCK_USER=root

# Build canonical expected state reference once for all FAIL/REC contract checks
build_canonical_state_ref

# Failure injection / recovery
reset_fixture
snapshot_mutable_state
export MOCK_MKTEMP_FAIL_PREFIX="known_hosts"
run_case 1 "FAIL01" "mktemp failure known_hosts" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
# Verify recovery: remove failure and apply successfully — full canonical state
export MOCK_MKTEMP_FAIL_PREFIX=""
run_case 0 "FAIL01_REC" "recovery known_hosts" "$TEST_SCRIPT" --apply
assert_rec_full_state

reset_fixture
snapshot_mutable_state
export MOCK_MKTEMP_FAIL_PREFIX="config"
run_case 1 "FAIL02" "mktemp failure config" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_MKTEMP_FAIL_PREFIX=""
run_case 0 "FAIL02_REC" "recovery config" "$TEST_SCRIPT" --apply
assert_rec_full_state

reset_fixture
snapshot_mutable_state
export MOCK_MKTEMP_FAIL_PREFIX="authorized_keys"
run_case 1 "FAIL03" "mktemp failure authorized_keys" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_MKTEMP_FAIL_PREFIX=""
run_case 0 "FAIL03_REC" "recovery authorized_keys" "$TEST_SCRIPT" --apply
assert_rec_full_state

# FAIL04 - config helper/write failure (Python injection)
reset_fixture
snapshot_mutable_state
export MOCK_PYTHON_FAIL_OP="config-write"
run_case 1 "FAIL04" "config helper write failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_PYTHON_FAIL_OP=""
run_case 0 "FAIL04_REC" "recovery config helper write" "$TEST_SCRIPT" --apply
assert_rec_full_state

# FAIL05 - authorized_keys helper/write failure (Python injection)
reset_fixture
snapshot_mutable_state
export MOCK_PYTHON_FAIL_OP="authorized-write"
run_case 1 "FAIL05" "authorized_keys helper write failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_PYTHON_FAIL_OP=""
run_case 0 "FAIL05_REC" "recovery authorized_keys helper write" "$TEST_SCRIPT" --apply
assert_rec_full_state

reset_fixture
snapshot_mutable_state
export MOCK_MV_FAIL_DEST="known_hosts.github"
run_case 1 "FAIL06" "mv known_hosts failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_MV_FAIL_DEST=""
run_case 0 "FAIL06_REC" "recovery mv known_hosts" "$TEST_SCRIPT" --apply
assert_rec_full_state

reset_fixture
snapshot_mutable_state
export MOCK_MV_FAIL_DEST="config"
run_case 1 "FAIL07" "mv config failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_MV_FAIL_DEST=""
run_case 0 "FAIL07_REC" "recovery mv config" "$TEST_SCRIPT" --apply
assert_rec_full_state

reset_fixture
snapshot_mutable_state
export MOCK_MV_FAIL_DEST="authorized_keys"
run_case 1 "FAIL08" "mv authorized_keys failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
assert_fail_origin_contract
assert_fail_audit
export MOCK_MV_FAIL_DEST=""
run_case 0 "FAIL08_REC" "recovery mv authorized_keys" "$TEST_SCRIPT" --apply
assert_rec_full_state

# FAIL09 - git remote set-url failure
reset_fixture
# Set initial origin to HTTPS form — MUST remain unchanged after failure
echo "https://github.com/basilivanov/solarsage-astro.git" > "$TEST_DIR/mock_origin"
snapshot_mutable_state
export MOCK_GIT_SET_URL_RC=1
run_case 1 "FAIL09" "git remote set-url failure" "$TEST_SCRIPT" --apply
assert_fail_no_success
assert_no_temp_files
assert_fail_dest_contract
# FAIL09 origin must remain old HTTPS (not canonical)
fail09_origin=$(cat "$TEST_DIR/mock_origin" 2>/dev/null || echo "")
if [ "$fail09_origin" != "https://github.com/basilivanov/solarsage-astro.git" ]; then
  echo "FAIL: FAIL09 origin mutated unexpectedly to: $fail09_origin" >&2
  exit 1
fi
assert_fail_audit
export MOCK_GIT_SET_URL_RC=0
run_case 0 "FAIL09_REC" "recovery git remote set-url" "$TEST_SCRIPT" --apply
assert_rec_full_state

# -----------------------------------------------------------------------------
# ID manifest verification — exact sorted manifest, not just count
# -----------------------------------------------------------------------------
cat > "$TEST_DIR/expected_case_ids" << 'MANIFEST_EOF'
AK01
AK02
AK03
AK04
AK05
AK06
AK07
AK08
AK09
AK10
AK11
CFG01
CFG02
CFG03
CFG04
CFG05
CFG06
CFG07
CFG08
CFG09
CFG10
CFG11
CFG12
CFG13
CFG14
CFG15
CLI01
CLI02
CLI03
CLI04
CLI05
CLI06
CLI07
CLI08
CLI09
CLI10
CLI11
CLI12
CLI13
CLI14
CLI15
FAIL01
FAIL01_REC
FAIL02
FAIL02_REC
FAIL03
FAIL03_REC
FAIL04
FAIL04_REC
FAIL05
FAIL05_REC
FAIL06
FAIL06_REC
FAIL07
FAIL07_REC
FAIL08
FAIL08_REC
FAIL09
FAIL09_REC
KEY01
KEY02
KEY03
KEY04
KEY05
KEY06
KEY07
KEY08
KEY09
KEY10
KEY11
KEY12
KEY13
KEY14
KEY15
KEY16
NET01
NET02
NET03
NET04
NET05
NET06
NET07
NET08_NONZERO
NET08_TIMEOUT
NET09
NET10
NET11
NET12
NET13
NET14
NET15
NET16
NET17
NET18
NET19
NET20
NET21_403
NET21_429
NET21_500
NET21_503
NET21_CURL
NET21_INVALID
NET21_TIMEOUT
NET22
NET23
ORIGIN01
ORIGIN02
ORIGIN03
ORIGIN04
ORIGIN05
ORIGIN06
ORIGIN07
ORIGIN08
PATH01
PATH02
PATH03
PATH04
PATH05
PATH06
PATH07
PATH08
PATH09
PATH10
PATH11
PATH12
PATH13
PATH14
PATH15
PATH16
PATH17
PATH18
PATH19
PATH20
PATH21
PATH22
PATH23
PATH24
PATH25
PATH26
PATH27
PATH28
PATH29
PATH30
PATH31
PATH32
PATH33
PATH34
PATH35
PATH36
PATH37
PATH38
PATH39
PATH40
PATH41_MODE
PATH41_OWNER
PATH41_SYMLINK
PATH42_MODE
PATH42_OWNER
PATH42_SYMLINK
PATH43_MODE
PATH43_OWNER
PATH43_SYMLINK
MANIFEST_EOF

sort "$TEST_DIR/expected_case_ids" > "$TEST_DIR/expected_sorted"
sort "$TEST_DIR/case_ids" > "$TEST_DIR/actual_sorted"

EXPECTED_LINES=$(wc -l < "$TEST_DIR/expected_sorted")
ACTUAL_LINES=$(wc -l < "$TEST_DIR/actual_sorted")

if [ "$EXPECTED_LINES" -ne 162 ]; then
  echo "FAIL: Manifest expected line count is $EXPECTED_LINES, expected 162" >&2
  exit 1
fi
if [ "$ACTUAL_LINES" -ne "$EXPECTED_LINES" ]; then
  echo "FAIL: Actual case count mismatch. Expected $EXPECTED_LINES, got $ACTUAL_LINES" >&2
  echo "Missing IDs (diff expected vs actual):" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^<' || true
  echo "Extra IDs (diff actual vs expected):" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^>' || true
  exit 1
fi

if ! cmp -s "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted"; then
  echo "FAIL: Case ID manifest mismatch" >&2
  echo "Missing IDs:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^<' || true
  echo "Extra IDs:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^>' || true
  exit 1
fi

CASE_COUNT=$ACTUAL_LINES

# -----------------------------------------------------------------------------
# Global output scan
# -----------------------------------------------------------------------------
forbidden_found=0
for f in "$TEST_DIR"/outputs/*.stdout "$TEST_DIR"/outputs/*.stderr; do
  if [ -f "$f" ]; then
    if grep -q "BEGIN.*PRIVATE KEY" "$f"; then
      echo "FAIL: Global scan detected PEM private key in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$CHECKOUT_PUB_BASE64" "$f"; then
      echo "FAIL: Global scan detected Checkout public key base64 in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$ACTIONS_PUB_BASE64" "$f"; then
      echo "FAIL: Global scan detected Actions public key base64 in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$CREDENTIAL_SENTINEL" "$f"; then
      echo "FAIL: Global scan detected credentials in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$API_BODY_SENTINEL_R13" "$f"; then
      echo "FAIL: Global scan detected API body in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$MALFORMED_REMOTE_SENTINEL_R13" "$f"; then
      echo "FAIL: Global scan detected malformed remote output in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$ENV_SECRET_SENTINEL_R13" "$f"; then
      echo "FAIL: Global scan detected env secrets in $(basename "$f")" >&2
      forbidden_found=1
    fi
    if grep -Fq "$ACTIONS_COMMENT" "$f"; then
      echo "FAIL: Global scan detected Actions comment in $(basename "$f")" >&2
      forbidden_found=1
    fi
  fi
done

if [ "$forbidden_found" -ne 0 ]; then
  exit 1
fi

echo "All $CASE_COUNT test-prod-github-access matrix cases passed!"
exit 0
# END_BLOCK: TEST_SUITE
