# ############################################################################
# AI_HEADER: PROD_PATH_TRANSACTION — Shared Nginx/system configuration transactional rollback library
# ROLE: Provides safe path capture, two-phase rollback, and cleanup utilities for system files.
# DEPENDENCIES: bash (5.2), mktemp, stat, cmp, rm, mv, ln, chown, chmod, cat, dirname, readlink, rmdir, mkdir
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-PATH-TRANSACTION
# purpose: Transactional rollback helper for system configurations.
# owns:
#   - scripts/deploy/lib/prod-path-transaction.sh
# inputs: none (sourced only)
# outputs: none
# dependencies: none
# invariants:
#   - Sourced only, does not execute commands or set traps on source.
#   - Namespaced variables and functions under prod_tx_ / PROD_TX_.
# failure_policy: Returns non-zero on snapshot or validation failures.
# END_MODULE_CONTRACT: M-PROD-PATH-TRANSACTION

# START_MODULE_MAP: M-PROD-PATH-TRANSACTION
# public_entrypoints:
#   - prod_tx_capture
#   - prod_tx_rollback
#   - prod_tx_cleanup
# semantic_blocks:
#   - TRANSACTION_LIB: state capture, restore, cleanup
# END_MODULE_MAP: M-PROD-PATH-TRANSACTION

# START_BLOCK: TRANSACTION_LIB

# Namespaced state arrays/variables
declare -A PROD_TX_TYPES
declare -A PROD_TX_OWNER
declare -A PROD_TX_GROUP
declare -A PROD_TX_MODE
declare -A PROD_TX_TARGET
declare -A PROD_TX_BACKUP_FILES
declare -A PROD_TX_PATHS
PROD_TX_TEMP_DIR=""

# Capture state of registered paths.
# Arguments:
#   1: temp_base_dir (optional, defaults to /run)
prod_tx_capture() {
  local temp_base="${1:-/run}"

  # If transaction is already active, fail
  if [ -n "${PROD_TX_TEMP_DIR:-}" ]; then
    echo "Error: transaction already active" >&2
    return 1
  fi

  # Ensure the temp base is a valid directory and not a symlink
  if [ ! -d "$temp_base" ] || [ -L "$temp_base" ]; then
    echo "Error: transaction temp base '$temp_base' is not a directory or is a symlink" >&2
    return 1
  fi

  # Create a transaction-specific subdirectory
  local tx_temp_dir
  if ! tx_temp_dir=$(mktemp -d "$temp_base/solarsage-tx-XXXXXX"); then
    echo "Error: failed to create transaction temp directory" >&2
    return 1
  fi
  chmod 0700 "$tx_temp_dir"
  PROD_TX_TEMP_DIR="$tx_temp_dir"

  for key in "${!PROD_TX_PATHS[@]}"; do
    local path="${PROD_TX_PATHS[$key]}"
    if [ -L "$path" ]; then
      PROD_TX_TYPES[$key]="symlink"
      PROD_TX_TARGET[$key]=$(readlink "$path")
      PROD_TX_OWNER[$key]=$(stat -c "%u" "$path")
      PROD_TX_GROUP[$key]=$(stat -c "%g" "$path")
    elif [ -f "$path" ]; then
      PROD_TX_TYPES[$key]="regular"
      PROD_TX_OWNER[$key]=$(stat -c "%u" "$path")
      PROD_TX_GROUP[$key]=$(stat -c "%g" "$path")
      PROD_TX_MODE[$key]=$(stat -c "%a" "$path")

      # Backup file content atomically into our tx temp dir
      local backup_file="$tx_temp_dir/$key.backup"
      if ! cat "$path" > "$backup_file"; then
        echo "Error: failed to back up path '$path'" >&2
        prod_tx_cleanup
        return 1
      fi
      PROD_TX_BACKUP_FILES[$key]="$backup_file"
    elif [ -e "$path" ]; then
      # Path exists but is not regular file or symlink (e.g. directory, socket, fifo)
      echo "Error: Path '$path' exists but is not a regular file or symlink (unsupported type)" >&2
      prod_tx_cleanup
      return 1
    else
      PROD_TX_TYPES[$key]="missing"
    fi
  done
  return 0
}

# Two-phase rollback: Phase 1 validates all paths, Phase 2 restores them.
prod_tx_rollback() {
  echo "Executing path transaction rollback..." >&2

  # Phase 1: Validation
  for key in "${!PROD_TX_PATHS[@]}"; do
    local path="${PROD_TX_PATHS[$key]}"
    local type="${PROD_TX_TYPES[$key]:-missing}"

    # Check key format
    if [[ ! "$key" =~ ^[A-Za-z0-9_.-]+$ ]]; then
      echo "Error: Invalid key format '$key'" >&2
      return 1
    fi

    # Verify captured metadata/backup exists for regular files
    if [ "$type" = "regular" ]; then
      local backup_file="${PROD_TX_BACKUP_FILES[$key]:-}"
      if [ -z "$backup_file" ] || [ ! -f "$backup_file" ] || [ ! -r "$backup_file" ]; then
        echo "Error: Captured backup file for key '$key' is missing or unreadable" >&2
        return 1
      fi
    fi

    # Verify current candidate state on disk
    if [ -e "$path" ] || [ -L "$path" ]; then
      # Only regular files and symlinks are allowed candidates
      if [ ! -f "$path" ] && [ ! -L "$path" ]; then
        echo "Error: Rollback candidate '$path' is of unexpected type (not regular file or symlink)" >&2
        return 1
      fi
    fi

    # Verify parent directory exists, is a real directory and not a symlink
    local parent_dir
    parent_dir=$(dirname "$path")
    if [ ! -d "$parent_dir" ] || [ -L "$parent_dir" ]; then
      echo "Error: Parent directory '$parent_dir' for path '$path' is missing or is a symlink" >&2
      return 1
    fi
  done

  # Phase 2: Execution
  for key in "${!PROD_TX_PATHS[@]}"; do
    local path="${PROD_TX_PATHS[$key]}"
    local type="${PROD_TX_TYPES[$key]:-missing}"

    # Remove candidate path securely (only regular/symlink, directory was checked and failed in Phase 1)
    rm -f "$path" 2>/dev/null || true

    if [ "$type" = "symlink" ]; then
      local target="${PROD_TX_TARGET[$key]}"
      local owner="${PROD_TX_OWNER[$key]}"
      local group="${PROD_TX_GROUP[$key]}"

      local parent_dir
      parent_dir=$(dirname "$path")

      # For atomic symlink restore, create mode-0700 temp directory in target parent
      local tmp_dir
      if ! tmp_dir=$(mktemp -d "$parent_dir/solarsage-tx-sym-XXXXXX"); then
        echo "Error: failed to create temp directory for atomic symlink restore" >&2
        return 1
      fi
      chmod 0700 "$tmp_dir"

      local tmp_symlink="$tmp_dir/symlink"
      if ! ln -sf "$target" "$tmp_symlink"; then
        echo "Error: failed to create temp symlink" >&2
        rm -rf "$tmp_dir"
        return 1
      fi

      if ! chown -h "$owner:$group" "$tmp_symlink"; then
        echo "Error: failed to set ownership for symlink" >&2
        rm -rf "$tmp_dir"
        return 1
      fi

      if ! mv -Tf "$tmp_symlink" "$path"; then
        echo "Error: failed to move symlink to destination" >&2
        rm -rf "$tmp_dir"
        return 1
      fi

      rmdir "$tmp_dir"
    elif [ "$type" = "regular" ]; then
      local backup_file="${PROD_TX_BACKUP_FILES[$key]}"
      local owner="${PROD_TX_OWNER[$key]}"
      local group="${PROD_TX_GROUP[$key]}"
      local mode="${PROD_TX_MODE[$key]}"

      local parent_dir
      parent_dir=$(dirname "$path")
      local tmp_restore
      if ! tmp_restore=$(mktemp "$parent_dir/solarsage-tx-restore.XXXXXX"); then
        echo "Error: failed to create temp restore file in '$parent_dir'" >&2
        return 1
      fi

      if ! cat "$backup_file" > "$tmp_restore"; then
        echo "Error: failed to copy backup content to temp restore file" >&2
        rm -f "$tmp_restore"
        return 1
      fi

      if ! chown "$owner:$group" "$tmp_restore"; then
        echo "Error: failed to set ownership for regular file" >&2
        rm -f "$tmp_restore"
        return 1
      fi

      if ! chmod "$mode" "$tmp_restore"; then
        echo "Error: failed to set permissions for regular file" >&2
        rm -f "$tmp_restore"
        return 1
      fi

      if ! mv -fT "$tmp_restore" "$path"; then
        echo "Error: failed to move regular file to destination" >&2
        rm -f "$tmp_restore"
        return 1
      fi
    fi
  done
  return 0
}

# Clean up temporary backup directories and snapshots.
prod_tx_cleanup() {
  if [ -n "${PROD_TX_TEMP_DIR:-}" ] && [ -d "$PROD_TX_TEMP_DIR" ] && [ ! -L "$PROD_TX_TEMP_DIR" ]; then
    rm -rf "$PROD_TX_TEMP_DIR"
  fi
  # Reset variables/arrays
  PROD_TX_TYPES=()
  PROD_TX_OWNER=()
  PROD_TX_GROUP=()
  PROD_TX_MODE=()
  PROD_TX_TARGET=()
  PROD_TX_BACKUP_FILES=()
  PROD_TX_TEMP_DIR=""
  PROD_TX_PATHS=()
}

# END_BLOCK: TRANSACTION_LIB
