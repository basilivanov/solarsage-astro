#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_NAMESPACE_LAYOUT — Namespace and layout contract check
# ROLE: Fails if canonical deployment implementations remain outside scripts/deploy/.
# DEPENDENCIES: bash, find, grep, sort, comm
# GRACE_ANCHORS: [NAMESPACE_LAYOUT_CONTRACT]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-NAMESPACE-LAYOUT
# purpose: Enforce that deployment code/tests live only under scripts/deploy/.
# owns:
#   - scripts/deploy/tests/test-prod-namespace-layout.sh
# inputs: none
# outputs: exit 0 on contract compliance, non-zero on violation
# dependencies: bash, find, grep, sort, comm, sed, mktemp
# side_effects: Creates and removes one temporary mutation sandbox under /tmp.
# emitted_logs: none
# invariants:
#   - No canonical deployment implementation exists outside scripts/deploy/.
#   - No stale references to old implementation paths remain in active configs,
#     legacy/, or active docs (docs/*.md plus named runbooks; docs/work/** is
#     historical and excluded by design).
#   - No double-prefixed scripts/deploy/scripts/deploy paths exist.
#   - README canonical inventory (the section between "## Canonical inventory"
#     and "## Compatibility map") matches the real file list exactly: every
#     canonical file occurs exactly once, no missing, no extras, no duplicates.
#   - The compatibility map mechanically covers every canonical file either by
#     an explicit old-path row or a category row; new files are marked as new.
#   - Mutation proofs reuse the same inventory validator and must fail closed.
# failure_policy: exits 1 with a descriptive message on the first violation found.
# END_MODULE_CONTRACT: M-TEST-PROD-NAMESPACE-LAYOUT

# START_MODULE_MAP: M-TEST-PROD-NAMESPACE-LAYOUT
# public_entrypoints:
#   - main
# semantic_blocks:
#   - NO_CANONICAL_OUTSIDE_DEPLOY: forbid old prod-* locations
#   - NO_STALE_REFERENCES: forbid old path references in configs, legacy/, docs
#   - NO_DOUBLE_PREFIX: forbid scripts/deploy/scripts/deploy
#   - README_EXACT_INVENTORY: shared section parser and exact validator
#   - COMPATIBILITY_MAP_COVERAGE: mechanical per-file coverage check
#   - MUTATION_PROOFS: removal, duplication, stale legacy/docs all rejected
# END_MODULE_MAP: M-TEST-PROD-NAMESPACE-LAYOUT

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
DEPLOY_DIR="$REPO_ROOT/scripts/deploy"
README="$DEPLOY_DIR/README.md"
SELF_NAME="test-prod-namespace-layout.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

# Binary-safe grep: returns 0 if pattern found, 1 otherwise. Never prints binary matches.
grep_safe() {
  grep -rEl "$1" "$2" --exclude-dir=__pycache__ --exclude='README.md' --exclude="$SELF_NAME" 2>/dev/null | grep -q .
}

echo "=== namespace/layout contract ==="

# --- 1. No canonical deployment implementation outside scripts/deploy/ ---
forbidden_globs=(
  "$REPO_ROOT/scripts/prod-*.sh"
  "$REPO_ROOT/scripts/prod-*.py"
  "$REPO_ROOT/scripts/lib/prod-*"
  "$REPO_ROOT/scripts/tests/test-prod-*"
  "$REPO_ROOT/scripts/check_prod_guard.sh"
)

for glob in "${forbidden_globs[@]}"; do
  # shellcheck disable=SC2086
  matches=$(find $glob -maxdepth 0 2>/dev/null || true)
  if [ -n "$matches" ]; then
    fail "Canonical deployment file found outside scripts/deploy/: $matches"
  fi
done
pass "no canonical deployment implementation outside scripts/deploy/"

# --- 2. No stale references to old implementation paths ---
stale_patterns=(
  'scripts/prod-[^/]*\.sh'
  'scripts/prod-[^/]*\.py'
  'scripts/lib/prod-'
  'scripts/tests/test-prod-'
  'scripts/check_prod_guard\.sh'
  'scripts/deploy\.sh'
  'scripts/bootstrap-vds\.sh'
  'scripts/backup\.sh'
  'scripts/db-create\.sh'
  'scripts/health-check\.sh'
  'scripts/health-check-with-alert\.sh'
  'scripts/alert\.sh'
  'scripts/dashboard\.sh'
)

# 2a. Active configs: workflows, infra, scripts (including legacy/)
active_dirs=(
  "$REPO_ROOT/.github/workflows"
  "$REPO_ROOT/infra"
  "$REPO_ROOT/scripts"
)

for dir in "${active_dirs[@]}"; do
  [ -d "$dir" ] || continue
  for pat in "${stale_patterns[@]}"; do
    if grep_safe "$pat" "$dir"; then
      fail "Stale reference to old deployment path '$pat' found under $dir"
    fi
  done
done
pass "no stale references in active configs (workflows, infra, scripts)"

# 2b. Active docs: top-level docs/*.md plus explicitly listed runbooks.
# docs/work/** is historical review/TZ material and is excluded by design.
active_docs=(
  "$REPO_ROOT/docs/PRODUCTION_RUNBOOK.md"
  "$REPO_ROOT/docs/DEPLOYMENT.md"
  "$REPO_ROOT/docs/monitoring-setup.md"
)
while IFS= read -r -d '' f; do
  active_docs+=("$f")
done < <(find "$REPO_ROOT/docs" -maxdepth 1 -name '*.md' -print0)

for doc in "${active_docs[@]}"; do
  [ -f "$doc" ] || continue
  for pat in "${stale_patterns[@]}"; do
    if grep_safe "$pat" "$doc"; then
      fail "Stale reference to old deployment path '$pat' found in active doc $doc"
    fi
  done
done
pass "no stale references in active docs (docs/*.md and runbooks; docs/work/** excluded as historical)"

# --- 3. No double-prefixed paths ---
if grep -r 'scripts/deploy/scripts/deploy' \
  "$REPO_ROOT/.github/workflows" "$REPO_ROOT/infra" "$REPO_ROOT/scripts" "$REPO_ROOT/docs" \
  --exclude-dir=__pycache__ --exclude="$SELF_NAME" 2>/dev/null | grep -q .; then
  fail "Double-prefixed scripts/deploy/scripts/deploy path found"
fi
pass "no double-prefixed deployment paths"

# START_BLOCK: README_EXACT_INVENTORY
# Shared parser: extract canonical inventory rows from the section between
# "## Canonical inventory" and "## Compatibility map". Only exact backtick-quoted
# file paths ending in .sh or .py are accepted; wildcards and directories excluded.
# Output order is document order; NO sort -u is applied, so duplicates survive.
parse_readme_inventory() {
  sed -n '/^## Canonical inventory/,/^## Compatibility map/p' "$1" \
    | grep -oE '`scripts/deploy/[^`]+`' \
    | tr -d '`' \
    | grep -E '\.(sh|py)$' \
    | grep -v '\*'
}

# Real canonical file list (find never yields duplicates; sorted for comm).
build_canonical_list() {
  find "$DEPLOY_DIR" -type f \
    ! -name 'README.md' \
    ! -path '*/__pycache__/*' \
    ! -name '*.pyc' \
    | sed "s|^$REPO_ROOT/||" | sort
}

# Shared validator: $1 = README path. Returns 0 iff the inventory section exactly
# matches the canonical list: no missing, no extras/non-existent, no duplicates.
# Diagnostics go to stderr. Reused for the live README and all mutation fixtures.
validate_readme_inventory() {
  local readme="$1"
  local canonical readme_rows rc=0
  canonical=$(mktemp); readme_rows=$(mktemp)
  build_canonical_list > "$canonical"
  parse_readme_inventory "$readme" > "$readme_rows"

  local missing extra dup
  missing=$(comm -23 "$canonical" <(sort "$readme_rows"))
  extra=$(comm -13 "$canonical" <(sort "$readme_rows"))
  # Duplicate detection sorts a COPY for adjacency but never unique-filters the source.
  dup=$(sort "$readme_rows" | uniq -d)

  if [ -n "$missing" ]; then
    echo "inventory missing canonical files: $missing" >&2
    rc=1
  fi
  if [ -n "$extra" ]; then
    echo "inventory lists non-existent or non-canonical paths: $extra" >&2
    rc=1
  fi
  if [ -n "$dup" ]; then
    echo "inventory contains duplicate rows: $dup" >&2
    rc=1
  fi
  rm -f "$canonical" "$readme_rows"
  return $rc
}
# END_BLOCK: README_EXACT_INVENTORY

# --- 4. README exact inventory (live) ---
[ -s "$README" ] || fail "README.md is missing or empty"
if ! validate_readme_inventory "$README"; then
  fail "README canonical inventory does not exactly match the canonical file list"
fi
# The contract test itself must be inventoried.
parse_readme_inventory "$README" | grep -qx "scripts/deploy/tests/$SELF_NAME" \
  || fail "README inventory does not list the contract test itself: scripts/deploy/tests/$SELF_NAME"
pass "README exact inventory matches canonical files (exactly once each, no duplicates)"

# START_BLOCK: COMPATIBILITY_MAP_COVERAGE
# --- 5. Compatibility map: mechanical per-file coverage ---
# Every canonical file must be covered by an explicit old-path row or a category
# row in the section between "## Compatibility map" and "## Unmoved".
compat_section() {
  sed -n '/^## Compatibility map/,/^## Unmoved/p' "$README"
}

compat_fail=0
compat_report() {
  echo "FAIL: compatibility map does not cover $1" >&2
  compat_fail=1
}

while IFS= read -r rel; do
  case "$rel" in
    scripts/deploy/check_prod_guard.sh)
      compat_section | grep -qF '`scripts/check_prod_guard.sh`' || compat_report "$rel" ;;
    scripts/deploy/prod-*.sh)
      compat_section | grep -qF 'scripts/prod-<name>.sh' || compat_report "$rel" ;;
    scripts/deploy/lib/prod-*)
      compat_section | grep -qF 'scripts/lib/prod-<name>' || compat_report "$rel" ;;
    scripts/deploy/tests/test-prod-namespace-layout.sh|\
    scripts/deploy/tests/test-prod-orchestrator.sh)
      # New files after the namespace refactor: must be marked as new, not
      # mapped from old paths.
      compat_section | sed -n '/^### New files/,$p' | grep -qF "$rel" || compat_report "$rel (not marked new)" ;;
    scripts/deploy/tests/test-prod-*.sh)
      compat_section | grep -qF 'scripts/tests/test-prod-<name>.sh' || compat_report "$rel" ;;
    *)
      compat_report "$rel (uncategorized)" ;;
  esac
done < <(build_canonical_list)
[ "$compat_fail" -eq 0 ] || fail "compatibility map coverage incomplete or untruthful"
pass "compatibility map mechanically covers every canonical file (new files marked new)"
# END_BLOCK: COMPATIBILITY_MAP_COVERAGE

# START_BLOCK: MUTATION_PROOFS
# --- 6. Mutation proofs (same validator, fail closed) ---
MUT_SBOX=$(mktemp -d "/tmp/solarsage-ns-mut-XXXXXX")
trap 'rm -rf "$MUT_SBOX"' EXIT

# Mutation A: remove one inventory row -> validator must reject (missing).
mkdir -p "$MUT_SBOX/a"
cp "$README" "$MUT_SBOX/a/README.md"
first_file=$(build_canonical_list | head -n 1)
sed -i "\|^\s*- \`$first_file\`|d" "$MUT_SBOX/a/README.md"
if parse_readme_inventory "$MUT_SBOX/a/README.md" | grep -qx "$first_file"; then
  fail "mutation A setup: could not remove inventory row for $first_file"
fi
if validate_readme_inventory "$MUT_SBOX/a/README.md" 2>/dev/null; then
  fail "mutation A: inventory with a removed row was NOT rejected"
fi
pass "mutation A: removed inventory row is rejected"

# Mutation B: duplicate one inventory row -> validator must reject (duplicate).
mkdir -p "$MUT_SBOX/b"
cp "$README" "$MUT_SBOX/b/README.md"
# Append a second exact row for the same canonical file inside the inventory section.
sed -i "/^## Compatibility map/i\\  - \`$first_file\`" "$MUT_SBOX/b/README.md"
if [ "$(parse_readme_inventory "$MUT_SBOX/b/README.md" | grep -xc "$first_file")" -ne 2 ]; then
  fail "mutation B setup: could not inject duplicate inventory row for $first_file"
fi
if validate_readme_inventory "$MUT_SBOX/b/README.md" 2>/dev/null; then
  fail "mutation B: inventory with a duplicated row was NOT rejected"
fi
pass "mutation B: duplicated inventory row is rejected"

# Mutation C: inject a stale legacy path into a temporary docs copy.
mkdir -p "$MUT_SBOX/c"
cat > "$MUT_SBOX/c/stale.md" << 'EOF'
# Stale doc
Run /opt/solarsage-astro/scripts/backup.sh manually.
EOF
if grep_safe 'scripts/backup\.sh' "$MUT_SBOX/c"; then
  pass "mutation C: stale legacy path in docs is detected"
else
  fail "mutation C: stale legacy path in docs was NOT detected"
fi

# Mutation D: inject a stale old deployment path into a temporary scripts copy.
mkdir -p "$MUT_SBOX/d"
cat > "$MUT_SBOX/d/stale.sh" << 'EOF'
#!/bin/bash
# owns: scripts/prod-backup.sh
EOF
if grep_safe 'scripts/prod-[^/]*\.sh' "$MUT_SBOX/d"; then
  pass "mutation D: stale old deployment path in scripts is detected"
else
  fail "mutation D: stale old deployment path in scripts was NOT detected"
fi

pass "all mutation proofs fail closed"
# END_BLOCK: MUTATION_PROOFS

echo "All namespace/layout contract checks passed!"
