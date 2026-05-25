#!/usr/bin/env bash
# GRACE W-2.0 marker gate (variant C, bash half).
# Verifies that every file matched by grace/frontend.paths carries the
# canonical markers: AI_HEADER, paired START/END_MODULE_CONTRACT, paired
# START/END_MODULE_MAP, and paired START_BLOCK/END_BLOCK for each block name.
#
# Exits 0 only if every enforced file passes every check. The set of enforced
# globs lives in grace/frontend.paths so that ESLint and this gate share one
# source of truth.

set -u
shopt -s globstar nullglob extglob

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PATHS_FILE="$ROOT/grace/frontend.paths"

if [[ ! -f "$PATHS_FILE" ]]; then
  echo "[grace-markers] missing $PATHS_FILE" >&2
  exit 2
fi

cd "$ROOT" || exit 2

declare -a FILES=()
while IFS= read -r line; do
  # Strip comments and blanks.
  line="${line%%#*}"
  line="${line//[$'\t\r ']/}"
  [[ -z "$line" ]] && continue
  # Expand glob from repo root.
  for f in $line; do
    [[ -f "$f" ]] && FILES+=("$f")
  done
done < "$PATHS_FILE"

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "[grace-markers] no files matched grace/frontend.paths — at least the pilot must exist"
  exit 1
fi

errors=0
checked=0

check_file() {
  local f="$1"
  local body
  body="$(cat "$f")"
  local file_errors=0

  # --- AI header ---
  if ! grep -q "AI_HEADER:" <<< "$body"; then
    echo "[grace-markers] $f: missing AI_HEADER:"
    file_errors=$((file_errors + 1))
  fi

  # --- Module contract pairing ---
  local mc_start mc_end
  mc_start=$(grep -c "START_MODULE_CONTRACT:" <<< "$body" || true)
  mc_end=$(grep -c "END_MODULE_CONTRACT:" <<< "$body" || true)
  if [[ "$mc_start" -ne "$mc_end" || "$mc_start" -eq 0 ]]; then
    echo "[grace-markers] $f: START_MODULE_CONTRACT/END_MODULE_CONTRACT mismatch (start=$mc_start end=$mc_end)"
    file_errors=$((file_errors + 1))
  fi

  # --- Module map pairing ---
  local mm_start mm_end
  mm_start=$(grep -c "START_MODULE_MAP:" <<< "$body" || true)
  mm_end=$(grep -c "END_MODULE_MAP:" <<< "$body" || true)
  if [[ "$mm_start" -ne "$mm_end" || "$mm_start" -eq 0 ]]; then
    echo "[grace-markers] $f: START_MODULE_MAP/END_MODULE_MAP mismatch (start=$mm_start end=$mm_end)"
    file_errors=$((file_errors + 1))
  fi

  # --- Block pairing by name ---
  # For every "START_BLOCK: NAME" we require exactly one matching
  # "END_BLOCK: NAME" elsewhere in the file.
  local starts ends
  starts=$(grep -oE "START_BLOCK:[[:space:]]+[A-Z][A-Z0-9_]*" <<< "$body" \
           | awk '{print $2}' | sort)
  ends=$(grep -oE "END_BLOCK:[[:space:]]+[A-Z][A-Z0-9_]*" <<< "$body" \
         | awk '{print $2}' | sort)

  if [[ "$starts" != "$ends" ]]; then
    echo "[grace-markers] $f: START_BLOCK/END_BLOCK names do not match"
    echo "    starts: $(echo "$starts" | tr '\n' ' ')"
    echo "    ends:   $(echo "$ends" | tr '\n' ' ')"
    file_errors=$((file_errors + 1))
  fi

  checked=$((checked + 1))
  errors=$((errors + file_errors))
}

for f in "${FILES[@]}"; do
  check_file "$f"
done

echo "[grace-markers] checked=$checked files, errors=$errors"
[[ "$errors" -eq 0 ]]
