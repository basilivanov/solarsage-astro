# Stage 2.W2C-1 R1 — self-contained GRACE negative harness

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`
Parents:

- `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`;
- `142_STAGE_2_W2C1_APP_PAGES_TRUTHFUL_GRACE_PREAMBLES_TZ.md`.

Статус: **AUTHORIZED TOOLING CORRECTION + W2C-1 GATE CONTINUATION — NO COMMIT/PUSH**

## 1. Accepted W2C-1 state

Architect accepts and freezes the current 14-page implementation:

```text
tracked app scope               exact 14 paths from 142
authorized-path GRACE lint      PASS_14
comment-only equivalence        PASS
GRACE linter self-tests         11 PASS
ESLint                          PASS_ZERO
typecheck                       PASS
index                           empty
```

Do not edit any of the 14 app pages in this R1. Their current hashes and diffs
are the accepted implementation under review.

## 2. Root cause

`scripts/grace/check-negative.sh` currently copies the product path:

```text
app/(grace)/today/page.tsx
```

and NEG-MARK-2 removes this stale literal:

```text
END_BLOCK: TODAY_FETCH
```

That marker is absent both before and after W2C-1, so the mutation is a no-op
and the gate correctly passes unexpectedly.

The design has a broader false-positive risk: marker-negative tests depend on
the current product pilot already passing every unrelated marker rule. A dirty
product pilot can make every negative case “fail as expected” for the wrong
reason.

The correct harness owns a synthetic clean marker fixture in its temporary
workspace, proves that fixture passes first, then validates each mutation by
its exact expected violation code.

## 3. Exact edit scope

Edit only:

```text
scripts/grace/check-negative.sh
```

Current 14 app diffs remain byte-identical. Docs 141–143 remain unchanged and
untracked. No linter, path manifest, ESLint config, product source or test file
edit. No commit/push.

Final tracked scope for combined W2C-1 review becomes exact 15 paths:

```text
14 accepted app pages
scripts/grace/check-negative.sh
```

## 4. Mandatory preflight

Before editing the script:

1. read 141, 142 and 143 completely;
2. prove branch/local/tracking/remote/main invariants from 142 still hold;
3. prove the 14 app diffs and their hashes equal the accepted callback state;
4. prove index empty and no other tracked diff;
5. reproduce `bash scripts/grace/check-negative.sh` as
   `pass=5 fail=1`, with only NEG-MARK-2 unexpected-pass;
6. copy the current script to `/tmp/stage2-w2c1-negative-before.sh` and hash it;
7. prove runtime/services/ports unchanged.

Stop on any mismatch. Never reset/rebase/force.

## 5. Synthetic clean marker fixture

Keep `PILOT` as the path inside the temporary tree, but remove the dependency
on the repository product file:

```bash
PILOT="app/(grace)/today/page.tsx"
```

Delete the repository `[[ ! -f "$PILOT" ]]` requirement and do not copy the
product pilot into `$WORK`.

After creating `$WORK` directories and copying gate tooling, write a synthetic
clean fixture to a baseline file outside the frontend globs, for example:

```bash
PILOT_BASE="$WORK/pilot.base.tsx"
```

Its exact semantic content must be:

```ts
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
```

Write `$WORK/$PILOT` by copying `PILOT_BASE` before each marker case.

For marker-gate cases, replace the copied repository frontend manifest in the
temporary workspace with exactly:

```text
app/(grace)/today/page.tsx
```

This isolates marker tests from product active-slice cleanliness. The ESLint
negative cases do not depend on this manifest and continue to use their
temporary `lib/api/*.ts` paths.

## 6. Mandatory positive baseline

Before running any negative marker mutation:

1. copy `PILOT_BASE` to `$WORK/$PILOT`;
2. run `(cd "$WORK" && bash scripts/grace/check-markers.sh)`;
3. require exit zero;
4. on failure, print the captured output and exit 2 with a clear
   `[grace-negative] clean marker baseline failed` message.

Negative tests are invalid unless the clean baseline passes.

## 7. Exact failure-code assertions

Introduce a marker-specific report helper that accepts:

```text
case name
expected GRC code
command
```

It must:

- fail the case if the command exits zero;
- pass only if the command exits non-zero and captured output contains the
  exact expected code;
- fail with “wrong failure reason” if the command exits non-zero for another
  reason;
- increment the same pass/fail counters;
- use a temp output under `$WORK`, not a shared fixed `/tmp/grace_neg.out`.

Use it for:

```text
NEG-MARK-1 expected GRC001
NEG-MARK-2 expected GRC004
NEG-MARK-3 expected GRC030
NEG-MARK-4 expected GRC031
```

The existing generic report helper may remain for ESLint cases, but its output
file must also live under `$WORK` to avoid cross-process collisions.

## 8. Exact marker mutations

Before each case copy `PILOT_BASE` to `$WORK/$PILOT`.

### NEG-MARK-1

Delete the one `AI_HEADER:` line. Assert after mutation that the header is
absent. Expected `GRC001`.

### NEG-MARK-2

Delete exactly:

```text
// END_BLOCK: NEGATIVE_TEST_BLOCK
```

Assert before mutation that the exact line exists once; assert after mutation
that START remains and END is absent. Expected `GRC004`.

Never refer to `TODAY_FETCH` or any product block name again.

### NEG-MARK-3

Pad the clean synthetic file beyond 1000 lines. Expected `GRC030`.

### NEG-MARK-4

Append the existing oversized arrow-function body to the clean synthetic file.
Expected `GRC031`.

Restore the clean pilot after marker cases before the ESLint negative cases.

## 9. Preserve ESLint negative semantics

Keep both existing cases and expected total case count:

```text
NEG-LINT-1 foreign TodayPayload import
NEG-LINT-2 local TodayPayload redeclaration
total pass target = 6
```

Do not weaken GRACE ESLint rules or change their temporary violation sources.
Fix comment syntax in those temp TypeScript fixtures only if current ESLint
output proves marker parsing interferes; otherwise preserve them.

## 10. Required continuation gates

First require:

```bash
bash -n scripts/grace/check-negative.sh
bash scripts/grace/check-negative.sh
```

Expected:

```text
clean marker baseline PASS
NEG-MARK-1 caught by GRC001
NEG-MARK-2 caught by GRC004
NEG-MARK-3 caught by GRC030
NEG-MARK-4 caught by GRC031
NEG-LINT-1 caught by its GRACE ESLint rule
NEG-LINT-2 caught by its GRACE ESLint rule
pass=6 fail=0
```

Then resume all 142 gates that were stopped:

```bash
python3 scripts/test_grace_front_lint.py
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/app/checkin-page.test.tsx \
  __tests__/app/today-redirect.test.ts \
  __tests__/horary/horary-error-state.test.tsx \
  __tests__/natal/natal-component-states.test.tsx \
  __tests__/natal/natal-no-english.test.tsx
git diff --check
```

Run explicit GRACE lint against the same 14 paths: PASS_14.

Run full marker gate and `pnpm guardrails:frontend` diagnostic. Required exact
remainder:

```text
32 violations / 27 failing paths / 20 green paths / 47 checked paths
remaining prefixes only components/grace/, lib/api/, lib/grace/
frontend ESLint/typecheck sections PASS
```

## 11. Final state and callback

Tracked diff exact 15 paths: accepted 14 comment-only app pages plus the one
negative harness script. Index empty. Docs 141–143 unchanged. No commit/push.

```text
READY_STAGE_2_W2C1_R1_APP_AND_NEGATIVE_HARNESS_REVIEW
tracked_scope: EXACT_15
app_comment_only_equivalence: PASS_14
authorized_paths_grace: PASS_14
negative_clean_baseline: PASS
negative_cases: 6 PASS / 0 FAIL
negative_exact_codes: GRC001_GRC004_GRC030_GRC031_AND_2_ESLINT_RULES
grace_linter_self_tests: 11 PASS
eslint: PASS_ZERO
typecheck: PASS
targeted_tests: <exact count> PASS
remaining_grace: 32 violations / 27 failing / 47 checked
remaining_prefixes: COMPONENTS_LIB_API_LIB_GRACE_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_docs: UNCHANGED_141_142_143
```

Then stop for architect review. Do not begin W2C-2.
