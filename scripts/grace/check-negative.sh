#!/usr/bin/env bash
# GRACE W-2.0 negative tests. Each case mutates a TEMP COPY of the pilot file
# (or creates a synthetic file) and asserts that the corresponding gate
# (markers gate or eslint) FAILS. The repo working tree is never modified.
#
# Cases:
#   NEG-MARK-1: AI_HEADER removed         -> check-markers.sh must fail
#   NEG-MARK-2: END_BLOCK removed         -> check-markers.sh must fail
#   NEG-LINT-1: foreign import of payload -> eslint must fail
#   NEG-LINT-2: local redeclare of type   -> eslint must fail

set -u
shopt -s globstar nullglob

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 2

PILOT="app/(grace)/today/page.tsx"
PATHS_FILE="grace/frontend.paths"

if [[ ! -f "$PILOT" ]]; then
  echo "[grace-negative] pilot $PILOT missing" >&2
  exit 2
fi

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

cp "$PILOT"                                  "$WORK/$PILOT"
cp lib/grace/log.ts                          "$WORK/lib/grace/log.ts"
cp packages/contracts/index.ts               "$WORK/packages/contracts/index.ts"
cp packages/contracts/_generated.ts          "$WORK/packages/contracts/_generated.ts"
cp scripts/grace/check-markers.sh            "$WORK/scripts/grace/check-markers.sh"
cp "$PATHS_FILE"                             "$WORK/$PATHS_FILE"
cp eslint.config.mjs                         "$WORK/eslint.config.mjs"
cp eslint-rules/grace-plugin.mjs             "$WORK/eslint-rules/grace-plugin.mjs"
cp tsconfig.json                             "$WORK/tsconfig.json" 2>/dev/null || true
# Reuse the real node_modules via symlink so we don't reinstall.
ln -s "$ROOT/node_modules" "$WORK/node_modules"
# package.json is needed for ESM resolution of the plugin.
cp package.json                              "$WORK/package.json"

chmod +x "$WORK/scripts/grace/check-markers.sh"

pass=0
fail=0
report() {
  local name="$1" expected_fail_cmd="$2"
  if eval "$expected_fail_cmd" > /tmp/grace_neg.out 2>&1; then
    echo "[grace-negative] $name: UNEXPECTED PASS — gate did not catch the violation"
    fail=$((fail + 1))
  else
    echo "[grace-negative] $name: ok (gate failed as expected)"
    pass=$((pass + 1))
  fi
}

# ---------- NEG-MARK-1: AI_HEADER removed ----------
cp "$PILOT" "$WORK/$PILOT"
sed -i.bak '/AI_HEADER:/d' "$WORK/$PILOT"
report "NEG-MARK-1 (AI_HEADER removed)" \
  "( cd '$WORK' && bash scripts/grace/check-markers.sh )"

# ---------- NEG-MARK-2: an END_BLOCK removed ----------
cp "$PILOT" "$WORK/$PILOT"
sed -i.bak '0,/END_BLOCK: TODAY_FETCH/{/END_BLOCK: TODAY_FETCH/d;}' "$WORK/$PILOT"
report "NEG-MARK-2 (END_BLOCK removed)" \
  "( cd '$WORK' && bash scripts/grace/check-markers.sh )"

# Restore the pilot inside WORK before running ESLint cases.
cp "$PILOT" "$WORK/$PILOT"

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
report "NEG-LINT-1 (foreign import of TodayPayload)" \
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
report "NEG-LINT-2 (local redeclare of TodayPayload)" \
  "( cd '$WORK' && pnpm exec eslint lib/api/local-redeclare.ts )"
rm -f "$NEG2"

echo "[grace-negative] pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
