#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_HOST_OFFSITE_ROUTING — Verify host-prepare offsite parameter routing
# ROLE: Pure static/structural verification of verify_host_state invocation and parameters.
# DEPENDENCIES: bash, grep
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-HOST-OFFSITE-ROUTING
# purpose: Verify prod-host-prepare.sh offsite verification routing logic.
# owns:
#   - scripts/deploy/tests/test-prod-host-offsite-routing.sh
# inputs: none
# outputs:
#   - exit 0 on success, non-zero on failure
# dependencies: none
# invariants: none
# failure_policy: fails non-zero on test failures.
# END_MODULE_CONTRACT: M-TEST-PROD-HOST-OFFSITE-ROUTING

# START_MODULE_MAP: M-TEST-PROD-HOST-OFFSITE-ROUTING
# public_entrypoints:
#   - main
# semantic_blocks:
#   - ROUTING_TEST: test implementation
# END_MODULE_MAP: M-TEST-PROD-HOST-OFFSITE-ROUTING

# START_BLOCK: ROUTING_TEST
set -euo pipefail
umask 027

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HOST_PREPARE="$REPO_ROOT/scripts/deploy/prod-host-prepare.sh"

if [ ! -f "$HOST_PREPARE" ]; then
  echo "Error: host-prepare script not found." >&2
  exit 1
fi

echo "Verifying structural routing contract in prod-host-prepare.sh..."

# 1. verify_host_state definition accepts two arguments and validates them
if ! grep -q "verify_host_state() {" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state definition not found" >&2
  exit 1
fi

# Check that the parameters are validated fail-closed
if ! grep -q "check_marker=" "$HOST_PREPARE" || ! grep -q "offsite_mode=" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state parameters not bound correctly" >&2
  exit 1
fi

if ! grep -q "Error: check_marker must be 0 or 1" "$HOST_PREPARE" || ! grep -q "Error: offsite_mode must be --preflight or --check" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state parameters validation missing" >&2
  exit 1
fi

# 2. Check call sites
# Site 1: --check -> verify_host_state 1 --check
if ! grep -q "verify_host_state 1 --check" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state call site in --check mode must be: verify_host_state 1 --check" >&2
  exit 1
fi

# Site 2: --apply before marker -> verify_host_state 0 --preflight
if ! grep -q "verify_host_state 0 --preflight" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state call site in --apply mode before marker must be: verify_host_state 0 --preflight" >&2
  exit 1
fi

# Site 3: --apply after marker -> verify_host_state 1 --preflight
if ! grep -q "verify_host_state 1 --preflight" "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state call site in --apply mode after marker must be: verify_host_state 1 --preflight" >&2
  exit 1
fi

# 3. The old offsite/profile integration must not be invoked from active
# preflight (the parked profile runner is never required by the active path).
if grep -q 'runuser -u "$APP_USER" -- "$run_script" backup -- "$offsite_script"' "$HOST_PREPARE"; then
  echo "FAIL: active preflight must not invoke the parked offsite check through the profile runner" >&2
  exit 1
fi
# Canonical app.env preflight replaces the parked prod-env-prepare invocation.
if grep -q 'prod-env-prepare.sh" --check' "$HOST_PREPARE"; then
  echo "FAIL: active preflight must not invoke the parked prod-env-prepare.sh --check" >&2
  exit 1
fi
if ! grep -q 'APP_ENV_FILE="/etc/solarsage/app.env"' "$HOST_PREPARE"; then
  echo "FAIL: canonical app.env preflight missing in host-prepare" >&2
  exit 1
fi
if ! grep -q '/usr/bin/docker compose --env-file /etc/solarsage/app.env -f "$APP_ROOT/infra/production/docker-compose.yml" config' "$HOST_PREPARE"; then
  echo "FAIL: DB compose config preflight must use the canonical env file directly" >&2
  exit 1
fi

# 5. Orchestrator/compose/state-directory installation and verification contract
# --apply must install byte-exact with exact ownership/modes.
if ! grep -q 'install -o root -g root -m 0755 "$APP_ROOT/scripts/deploy/prod-orchestrator.sh" "/usr/local/libexec/solarsage/prod-orchestrator"' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must install the orchestrator byte-exact root:root 0755" >&2
  exit 1
fi
if ! grep -q 'install -o root -g root -m 0644 "$APP_ROOT/infra/production/docker-compose.app.yml" "/etc/solarsage/compose/docker-compose.app.yml"' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must install the app compose byte-exact root:root 0644" >&2
  exit 1
fi
if ! grep -q 'install -d -o "$APP_USER" -g "$APP_GROUP" -m 0700 /var/lib/solarsage/orchestrator' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must prepare the astro:astro 0700 orchestrator state directory" >&2
  exit 1
fi
if ! grep -q 'install -d -o root -g root -m 0755 /etc/solarsage/compose' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must prepare the root:root 0755 compose directory" >&2
  exit 1
fi
if ! grep -q 'install -d -o root -g root -m 0755 /usr/local/libexec/solarsage' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must prepare the root:root 0755 libexec directory" >&2
  exit 1
fi

# verify_host_state must prove bytes/owner/group/mode for the installed files and directories.
if ! grep -q 'cmp -s "$APP_ROOT/scripts/deploy/prod-orchestrator.sh" "$orch_path"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must byte-compare the installed orchestrator" >&2
  exit 1
fi
if ! grep -q 'cmp -s "$APP_ROOT/infra/production/docker-compose.app.yml" "$compose_path"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must byte-compare the installed app compose" >&2
  exit 1
fi
if ! grep -q 'verify_dir_perms "/etc/solarsage/compose" "root:root" "755"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must prove the compose directory metadata" >&2
  exit 1
fi
if ! grep -q 'verify_dir_perms "/usr/local/libexec/solarsage" "root:root" "755"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must prove the libexec directory metadata" >&2
  exit 1
fi
if ! grep -q 'verify_dir_perms "/var/lib/solarsage/orchestrator" "astro:astro" "700"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must prove the orchestrator state directory metadata" >&2
  exit 1
fi

# 6. Compose port ownership convergence contract: --apply must never enable the
# app systemd units and must converge them to stopped+disabled every run.
if grep -qE 'for unit in "\$\{APP_UNITS\[@\]\}"' "$HOST_PREPARE"; then
  if ! grep -q 'local APP_UNITS=(' "$HOST_PREPARE"; then
    echo "FAIL: APP_UNITS list missing" >&2
    exit 1
  fi
  app_units_block=$(sed -n '/local APP_UNITS=(/,/^ *)/p' "$HOST_PREPARE")
  for forbidden in solarsage-sidecar.service solarsage-api.service solarsage-frontend.service; do
    if printf '%s' "$app_units_block" | grep -q "$forbidden"; then
      echo "FAIL: APP_UNITS enable list must not contain $forbidden (Compose owns app ports)" >&2
      exit 1
    fi
  done
fi
if ! grep -q 'COMPOSE_OWNED_UNITS=(' "$HOST_PREPARE"; then
  echo "FAIL: COMPOSE_OWNED_UNITS convergence list missing" >&2
  exit 1
fi
converge_block=$(sed -n '/COMPOSE_OWNED_UNITS=(/,/^    done/p' "$HOST_PREPARE")
for required in solarsage-sidecar.service solarsage-api.service solarsage-frontend.service; do
  if ! printf '%s' "$converge_block" | grep -q "$required"; then
    echo "FAIL: convergence list must contain $required" >&2
    exit 1
  fi
done
if printf '%s' "$converge_block" | grep -q 'systemctl stop "\$unit"'; then
  echo "FAIL: convergence must never stop app units (stop is the owner's manual cutover step)" >&2
  exit 1
fi
if printf '%s' "$converge_block" | grep -q 'systemctl restart "\$unit"'; then
  echo "FAIL: convergence must never restart app units" >&2
  exit 1
fi
if printf '%s' "$converge_block" | grep -q -- '--now'; then
  echo "FAIL: convergence disable must not use --now (metadata-only, no downtime)" >&2
  exit 1
fi
if ! printf '%s' "$converge_block" | grep -q 'systemctl disable "\$unit"'; then
  echo "FAIL: convergence must disable pre-existing app units without --now" >&2
  exit 1
fi

# 7. Tmpfiles maintenance lock contract: install byte-exact, create on apply,
# verify bytes and lock metadata.
if ! grep -q 'install -o root -g root -m 0644 "$APP_ROOT/infra/production/tmpfiles.d/solarsage.conf" "/etc/tmpfiles.d/solarsage.conf"' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must install the tmpfiles declaration byte-exact root:root 0644" >&2
  exit 1
fi
if ! grep -q 'systemd-tmpfiles --create /etc/tmpfiles.d/solarsage.conf' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must run systemd-tmpfiles --create on apply" >&2
  exit 1
fi
if ! grep -q 'cmp -s "$APP_ROOT/infra/production/tmpfiles.d/solarsage.conf" "$tmpfiles_path"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must byte-compare the tmpfiles declaration" >&2
  exit 1
fi
if ! grep -q '"$l_info" != "root:astro:660"' "$HOST_PREPARE"; then
  echo "FAIL: verify_host_state must prove the maintenance lock root:astro 0660 metadata" >&2
  exit 1
fi

# 8. Enabled/disabled verification contract: app units and the parked old
# backup path must be required DISABLED; only DB and the canonical backup
# timer are required enabled.
enabled_block=$(sed -n '/local ENABLED_UNITS=(/,/^ *)/p' "$HOST_PREPARE")
for forbidden in solarsage-sidecar.service solarsage-api.service solarsage-frontend.service solarsage-backup-maintenance.timer; do
  if printf '%s' "$enabled_block" | grep -q "$forbidden"; then
    echo "FAIL: ENABLED_UNITS must not contain $forbidden" >&2
    exit 1
  fi
done
disabled_block=$(sed -n '/local DISABLED_UNITS=(/,/^ *)/p' "$HOST_PREPARE")
for required in solarsage-sidecar.service solarsage-api.service solarsage-frontend.service solarsage-backup-maintenance.timer; do
  if ! printf '%s' "$disabled_block" | grep -q "$required"; then
    echo "FAIL: DISABLED_UNITS must contain $required" >&2
    exit 1
  fi
done
# Static oneshot services must not be treated as enabled: the check must compare
# the is-enabled output, not its exit code alone.
if ! grep -q 'unit_state=$(systemctl is-enabled "$unit"' "$HOST_PREPARE"; then
  echo "FAIL: disabled-state check must capture is-enabled output (static-aware)" >&2
  exit 1
fi
if ! grep -q '"$unit_state" = "enabled"' "$HOST_PREPARE"; then
  echo "FAIL: disabled-state check must error only on enabled/enabled-runtime" >&2
  exit 1
fi
parked_inactive_block=$(sed -n '/local PARKED_INACTIVE_UNITS=(/,/^ *)/p' "$HOST_PREPARE")
for required in solarsage-backup-maintenance.timer solarsage-backup-maintenance.service; do
  if ! printf '%s' "$parked_inactive_block" | grep -q "$required"; then
    echo "FAIL: PARKED_INACTIVE_UNITS must contain $required" >&2
    exit 1
  fi
done
if grep -q 'systemctl start solarsage-backup-maintenance.timer' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must not start the parked backup-maintenance timer" >&2
  exit 1
fi
if grep -q 'systemctl enable solarsage-backup-maintenance.timer' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must not enable the parked backup-maintenance timer" >&2
  exit 1
fi
if ! grep -q 'systemctl enable solarsage-backup.timer' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must enable the canonical daily backup timer" >&2
  exit 1
fi
if ! grep -q 'systemctl start solarsage-backup.timer' "$HOST_PREPARE"; then
  echo "FAIL: host-prepare must start the canonical daily backup timer" >&2
  exit 1
fi

# 9. Sudoers exact whole-argument regex contract: the only capabilities must be
# the installed orchestrator with the anchored ^deploy <40hex> --manual-confirm$
# and ^migrate <40hex> --manual-confirm$ whole-argument regexes; no
# wildcard/literal argument forms.
SUDOERS_SRC="$REPO_ROOT/infra/production/solarsage-deploy.sudoers"
if ! grep -qxF 'astro ALL=(root) NOPASSWD: /usr/local/libexec/solarsage/prod-orchestrator ^deploy [0-9a-f]{40} --manual-confirm$' "$SUDOERS_SRC"; then
  echo "FAIL: sudoers must allow exactly the orchestrator with ^deploy [0-9a-f]{40} --manual-confirm$ whole-argument regex" >&2
  exit 1
fi
if ! grep -qxF 'astro ALL=(root) NOPASSWD: /usr/local/libexec/solarsage/prod-orchestrator ^migrate [0-9a-f]{40} --manual-confirm$' "$SUDOERS_SRC"; then
  echo "FAIL: sudoers must allow exactly the orchestrator with ^migrate [0-9a-f]{40} --manual-confirm$ whole-argument regex" >&2
  exit 1
fi
if [ "$(grep -cE '^astro ALL=\(root\)' "$SUDOERS_SRC")" -ne 2 ]; then
  echo "FAIL: sudoers must contain exactly the deploy and migrate capabilities and nothing else" >&2
  exit 1
fi
if grep -vE '^\s*#' "$SUDOERS_SRC" | grep -qE 'systemctl restart|release-authority|Cmnd_Alias|ALL[[:space:]]'; then
  echo "FAIL: sudoers must not contain restart aliases, release-authority or wildcard aliases" >&2
  exit 1
fi

# 4. Check no old `if [ "$check_marker" -eq 1 ]` wraps the entire offsite check block
# Let's verify that "if cmd_exists runuser" is the only wrapper.
# In the script, we replaced `if [ "$check_marker" -eq 1 ] && cmd_exists runuser` with `if cmd_exists runuser`
if grep -q 'if \[ "\$check_marker" -eq 1 \] && cmd_exists runuser' "$HOST_PREPARE"; then
  echo "FAIL: old check_marker wrapper still exists around offsite block" >&2
  exit 1
fi

echo "SUCCESS: test-prod-host-offsite-routing.sh passed!"
exit 0
# END_BLOCK: ROUTING_TEST
