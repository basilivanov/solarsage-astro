#!/usr/bin/env bash
# GRACE W-2.0 negative tests. Each case mutates a TEMP COPY of the pilot file
# (or creates a synthetic file) and asserts that the corresponding gate
# (markers gate or eslint) FAILS. The repo working tree is never modified.
#
# Cases:
#   NEG-MARK-1: AI_HEADER removed         -> check-markers.sh must fail
#   NEG-MARK-2: END_BLOCK removed         -> check-markers.sh must fail
#   NEG-MARK-3: file over 1000 lines      -> check-markers.sh must fail
#   NEG-MARK-4: function over 4000 tokens -> check-markers.sh must fail
#   NEG-LINT-1: foreign import of payload -> eslint must fail
#   NEG-LINT-2: local redeclare of type   -> eslint must fail

set -u
shopt -s globstar nullglob

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 2

PILOT="app/(grace)/today/page.tsx"
PATHS_FILE="grace/frontend.paths"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Mirror the repo into $WORK (lightweight: just copy the directories the gates
# touch). Both gates resolve paths from their own ROOT, so we run them with
# WORK as their cwd.
mkdir -p "$WORK/app/(grace)/today" \
         "$WORK/components/grace" \
         "$WORK/lib/grace" \
         "$WORK/lib/api" \
         "$WORK/packages/contracts" \
         "$WORK/scripts/grace" \
         "$WORK/grace" \
         "$WORK/eslint-rules"

cp lib/grace/log.ts                          "$WORK/lib/grace/log.ts"
cp packages/contracts/index.ts               "$WORK/packages/contracts/index.ts"
cp packages/contracts/_generated.ts          "$WORK/packages/contracts/_generated.ts"
cp scripts/grace/check-markers.sh            "$WORK/scripts/grace/check-markers.sh"
cp scripts/grace_front_lint.py               "$WORK/scripts/grace_front_lint.py"
cp "$PATHS_FILE"                             "$WORK/$PATHS_FILE"
cp eslint.config.mjs                         "$WORK/eslint.config.mjs"
cp eslint-rules/grace-plugin.mjs             "$WORK/eslint-rules/grace-plugin.mjs"
cp tsconfig.json                             "$WORK/tsconfig.json" 2>/dev/null || true
# Reuse the real node_modules via symlink so we don't reinstall.
ln -s "$ROOT/node_modules" "$WORK/node_modules"
# package.json is needed for ESM resolution of the plugin.
cp package.json                              "$WORK/package.json"

chmod +x "$WORK/scripts/grace/check-markers.sh"

# Isolate marker-negative cases from the current product active-slice state.
printf '%s\n' "$PILOT" > "$WORK/$PATHS_FILE"

PILOT_BASE="$WORK/pilot.base.tsx"
cat > "$PILOT_BASE" <<'EOF'
// ############################################################################
// AI_HEADER: NEGATIVE_MARKER_PILOT — self-contained clean fixture.
// ROLE: Temporary GRACE negative-test input; never imported by product code.
// ############################################################################

// START_MODULE_CONTRACT: M-NEGATIVE-MARKER-PILOT
// purpose: Provide one known-clean module with one paired block.
// owns:
//   - app/(grace)/today/page.tsx (temporary workspace only)
// inputs: none.
// outputs: one inert exported value.
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Baseline passes the frontend GRACE marker gate.
// failure_policy: none.
// END_MODULE_CONTRACT: M-NEGATIVE-MARKER-PILOT

// START_MODULE_MAP: M-NEGATIVE-MARKER-PILOT
// public_entrypoints:
//   - negativeMarkerPilot
// semantic_blocks:
//   - NEGATIVE_TEST_BLOCK: paired block mutated by NEG-MARK-2.
// owned_tests:
//   - scripts/grace/check-negative.sh
// END_MODULE_MAP: M-NEGATIVE-MARKER-PILOT

// START_BLOCK: NEGATIVE_TEST_BLOCK
export const negativeMarkerPilot = 1
// END_BLOCK: NEGATIVE_TEST_BLOCK
EOF

pass=0
fail=0
report_eslint() {
  local name="$1" expected_rule="$2" expected_fail_cmd="$3"
  local output="$WORK/eslint-negative-$((pass + fail + 1)).out"
  local rc

  eval "$expected_fail_cmd" > "$output" 2>&1
  rc=$?

  if [[ "$rc" -eq 0 ]]; then
    echo "[grace-negative] $name: UNEXPECTED PASS — expected $expected_rule"
    fail=$((fail + 1))
  elif [[ "$rc" -ne 1 ]]; then
    echo "[grace-negative] $name: wrong failure reason — expected ESLint exit 1 for $expected_rule, got $rc"
    sed 's/^/[grace-negative]   /' "$output"
    fail=$((fail + 1))
  elif grep -Fq 'Parsing error' "$output"; then
    echo "[grace-negative] $name: wrong failure reason — Parsing error rejected"
    sed 's/^/[grace-negative]   /' "$output"
    fail=$((fail + 1))
  elif grep -Fq "$expected_rule" "$output"; then
    echo "[grace-negative] $name: ok (caught by $expected_rule)"
    pass=$((pass + 1))
  else
    echo "[grace-negative] $name: wrong failure reason — expected $expected_rule"
    sed 's/^/[grace-negative]   /' "$output"
    fail=$((fail + 1))
  fi
}

report_marker() {
  local name="$1" expected_code="$2" expected_fail_cmd="$3"
  local output="$WORK/marker-negative-$expected_code.out"
  if eval "$expected_fail_cmd" > "$output" 2>&1; then
    echo "[grace-negative] $name: UNEXPECTED PASS — expected $expected_code"
    fail=$((fail + 1))
  elif grep -Eq "(^|[^[:alnum:]_])$expected_code([^[:alnum:]_]|$)" "$output"; then
    echo "[grace-negative] $name: ok (caught by $expected_code)"
    pass=$((pass + 1))
  else
    echo "[grace-negative] $name: wrong failure reason — expected $expected_code"
    sed 's/^/[grace-negative]   /' "$output"
    fail=$((fail + 1))
  fi
}

line_count() {
  grep -Fxc "$1" "$2" || true
}

# A negative mutation is meaningful only when its clean synthetic baseline
# passes every marker rule first.
cp "$PILOT_BASE" "$WORK/$PILOT"
BASELINE_OUTPUT="$WORK/clean-marker-baseline.out"
if (cd "$WORK" && bash scripts/grace/check-markers.sh) > "$BASELINE_OUTPUT" 2>&1; then
  echo "[grace-negative] clean marker baseline PASS"
else
  echo "[grace-negative] clean marker baseline failed" >&2
  sed 's/^/[grace-negative]   /' "$BASELINE_OUTPUT" >&2
  exit 2
fi

# ---------- NEG-MARK-1: AI_HEADER removed ----------
cp "$PILOT_BASE" "$WORK/$PILOT"
sed -i.bak '/AI_HEADER:/d' "$WORK/$PILOT"
if grep -q 'AI_HEADER:' "$WORK/$PILOT"; then
  echo "[grace-negative] NEG-MARK-1 (AI_HEADER removed): mutation assertion failed"
  fail=$((fail + 1))
else
  report_marker "NEG-MARK-1 (AI_HEADER removed)" "GRC001" \
    "( cd '$WORK' && bash scripts/grace/check-markers.sh )"
fi

# ---------- NEG-MARK-2: an END_BLOCK removed ----------
cp "$PILOT_BASE" "$WORK/$PILOT"
end_count="$(line_count '// END_BLOCK: NEGATIVE_TEST_BLOCK' "$WORK/$PILOT")"
if [[ "$end_count" -ne 1 ]]; then
  echo "[grace-negative] NEG-MARK-2 (END_BLOCK removed): pre-mutation assertion failed"
  fail=$((fail + 1))
else
  sed -i.bak '\|^// END_BLOCK: NEGATIVE_TEST_BLOCK$|d' "$WORK/$PILOT"
  start_count="$(line_count '// START_BLOCK: NEGATIVE_TEST_BLOCK' "$WORK/$PILOT")"
  end_count="$(line_count '// END_BLOCK: NEGATIVE_TEST_BLOCK' "$WORK/$PILOT")"
  if [[ "$start_count" -eq 1 && "$end_count" -eq 0 ]]; then
    report_marker "NEG-MARK-2 (END_BLOCK removed)" "GRC004" \
      "( cd '$WORK' && bash scripts/grace/check-markers.sh )"
  else
    echo "[grace-negative] NEG-MARK-2 (END_BLOCK removed): post-mutation assertion failed"
    fail=$((fail + 1))
  fi
fi

# ---------- NEG-MARK-3: GRC030 file too long ----------
cp "$PILOT_BASE" "$WORK/$PILOT"
# pad it with 1050 lines
for i in {1..1050}; do echo "" >> "$WORK/$PILOT"; done
report_marker "NEG-MARK-3 (file over 1000 lines fails GRC030)" "GRC030" \
  "( cd '$WORK' && bash scripts/grace/check-markers.sh )"

# ---------- NEG-MARK-4: GRC031 function too large ----------
cp "$PILOT_BASE" "$WORK/$PILOT"
cat >> "$WORK/$PILOT" <<'EOF'
export const LargeComponent = () => {
EOF
for i in {1..1500}; do echo "  let x = 1;" >> "$WORK/$PILOT"; done
cat >> "$WORK/$PILOT" <<'EOF'
}
EOF
report_marker "NEG-MARK-4 (function over 4000 tokens fails GRC031)" "GRC031" \
  "( cd '$WORK' && bash scripts/grace/check-markers.sh )"

# Restore the pilot inside WORK before running ESLint cases.
cp "$PILOT_BASE" "$WORK/$PILOT"

# ---------- NEG-LINT-1: foreign import of payload type ----------
NEG1="$WORK/lib/api/foreign-import.ts"
cat > "$NEG1" <<'EOF'
// AI_HEADER: NEG_FOREIGN_IMPORT
// START_MODULE_CONTRACT: M-NEG.foreign
// END_MODULE_CONTRACT: M-NEG.foreign
// START_MODULE_MAP: M-NEG.foreign
// END_MODULE_MAP: M-NEG.foreign
import type { TodayPayload } from "@/lib/types/today";
export const _x: TodayPayload | null = null;
EOF
report_eslint "NEG-LINT-1 (foreign import of TodayPayload)" \
  "grace/contracts-only-import" \
  "( cd '$WORK' && pnpm exec eslint lib/api/foreign-import.ts )"
rm -f "$NEG1"

# ---------- NEG-LINT-2: local redeclare of contract type ----------
NEG2="$WORK/lib/api/local-redeclare.ts"
cat > "$NEG2" <<'EOF'
// AI_HEADER: NEG_LOCAL_REDECLARE
// START_MODULE_CONTRACT: M-NEG.redeclare
// END_MODULE_CONTRACT: M-NEG.redeclare
// START_MODULE_MAP: M-NEG.redeclare
// END_MODULE_MAP: M-NEG.redeclare
export interface TodayPayload {
  whatever: string;
}
EOF
report_eslint "NEG-LINT-2 (local redeclare of TodayPayload)" \
  "grace/no-redeclare-contract-types" \
  "( cd '$WORK' && pnpm exec eslint lib/api/local-redeclare.ts )"
rm -f "$NEG2"

echo "[grace-negative] pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
