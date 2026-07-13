# Stage 2.W2C-4 — truthful GRACE preambles for final GRACE library files

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`
Predecessor: W2C-3 must be accepted, committed and pushed first.

Статус: **PREPARED FINAL W2C WAVE — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Goal and deterministic completion condition

Replace the generic leading GRACE preambles in the final three failing
frontend files with truthful module contracts/maps. Runtime code must remain
byte-identical from the first directive/export statement onward.

Required accepted baseline after W2C-3 push:

```text
3 violations
3 failing paths
44 green paths
47 checked paths
remaining paths exactly the three files in section 2
```

Required result after this implementation wave:

```text
0 violations
0 failing paths
47 green paths
47 checked paths
pnpm guardrails:frontend PASS
```

This is the final W2C marker wave. It is still implementation-only: no
staging, commit or push until separate architect acceptance.

## 2. Exact edit allowlist

```text
lib/grace/hooks/useCalendar.ts
lib/grace/hooks/useDay.ts
lib/grace/index.ts
```

Edit exact three only. Do not edit callers, tests, API clients, contracts,
logging registry, configs, scripts, manifests or docs. Do not touch any
previous W2C file. Do not start backend/sidecar gates, final RC, merge or
deployment.

No `git add`, commit or push. Stop after the required callback.

## 3. Hard comment-only invariant

For each authorized file:

- replace only the leading comments and adjacent blank lines before the first
  runtime directive/export statement;
- preserve `'use client';` in both hook files exactly;
- preserve the first `export` and all barrel exports in `index.ts` exactly;
- do not change imports, exports, types, interfaces, functions, dependency
  arrays, strings, event names, logging metadata, timeout duration, status
  codes, redirect target, state transitions or error behavior;
- do not run a formatter;
- runtime suffix must remain byte-identical;
- comment-stripped source must remain equivalent;
- existing function/block-marker counts must remain unchanged;
- remove the redundant legacy mini-header lines (`// AI_HEADER`, `// module`,
  `// wave`, `// purpose`) together with the false generic preamble; do not
  leave a second header after the canonical preamble.

No function contracts or new `START_BLOCK` markers are requested. This wave
owns only one canonical module preamble per file.

## 4. Canonical preamble form

Each file receives exactly one AI header within the first 30 lines, one paired
module contract and one paired module map using the same unique ID:

```ts
// ############################################################################
// AI_HEADER: <NAME> — <truthful one-line description>
// ROLE: <actual callers and responsibility>
// ############################################################################

// START_MODULE_CONTRACT: <ID>
// purpose: ...
// owns:
//   - exact/path.ts
// inputs: ...
// outputs: ...
// dependencies: ...
// side_effects: ...
// emitted_logs: <exact events or none.>
// invariants:
//   - ...
// failure_policy: ...
// END_MODULE_CONTRACT: <ID>

// START_MODULE_MAP: <same ID>
// public_entrypoints:
//   - ...
// semantic_blocks:
//   - ...
// owned_tests:
//   - exact test path, or none direct.
// END_MODULE_MAP: <same ID>
```

Forbidden generic/false phrases:

```text
n/a
Function arguments
Return values
local modules
log and raise
UI — useDay
UI — useCalendar
Library: index
v2 logging: logEvent/logStart/logSuccess/logFailure
```

## 5. Exact truthful contract — `useCalendar.ts`

Use these required facts. Grammar may be minimally aligned, but do not invent
behavior.

```text
ID: M-FRONTEND-GRACE-HOOK-USE-CALENDAR
AI_HEADER name: GRACE_USE_CALENDAR
AI_HEADER meaning: client hook for month-scoped CalendarPayload loading state.
ROLE: Hook used by calendar consumers to fetch one month and expose data,
      loading and normalized ApiError state.
purpose: Fetch CalendarPayload whenever the month input changes and guard
         state writes after effect cleanup.
owns: lib/grace/hooks/useCalendar.ts
inputs: month string in the existing YYYY-MM caller format.
outputs: exported UseCalendarResult interface and useCalendar hook returning
         data/loading/error.
dependencies: React useState/useEffect; lib/grace/api/client fetchCalendar and
              ApiError; packages/contracts CalendarPayload.
side_effects: delegated calendar network request plus React state updates.
emitted_logs: none.
invariants:
  - Initial state remains data=null, loading=true, error=null.
  - Each month effect sets loading=true and clears error before fetching.
  - Existing data is not proactively cleared when a new month load starts.
  - Cleanup marks the request cancelled; later success/error/finally handlers
    do not update state for that effect.
  - A month change starts a new fetch through the existing [month] dependency.
  - Existing ApiError instances are preserved; unknown failures become
    ApiError('Unknown error', 500).
failure_policy: expose the preserved/normalized ApiError and finish loading
                only while the effect remains active; do not throw from hook.
public_entrypoints: UseCalendarResult, useCalendar.
semantic_blocks: RESULT_SHAPE; CALENDAR_STATE; MONTH_LOAD_EFFECT;
                 CANCEL_GUARD; ERROR_NORMALIZATION.
owned_tests:
  - __tests__/hooks/useCalendar.test.ts
```

Do not claim that the underlying request itself is aborted: runtime only
suppresses post-cleanup state writes through the `cancelled` flag.

## 6. Exact truthful contract — `useDay.ts`

```text
ID: M-FRONTEND-GRACE-HOOK-USE-DAY
AI_HEADER name: GRACE_USE_DAY
AI_HEADER meaning: authenticated day hook with logging and onboarding routing.
ROLE: Hook consumed by the day route to wait for Telegram auth, fetch
      TodayPayload and expose loading/data/error or redirect incomplete users.
purpose: Coordinate auth readiness, delayed day loading, structured logging,
         cancellation-safe state updates and onboarding redirects.
owns: lib/grace/hooks/useDay.ts
inputs: ISO date string; Telegram-auth loading state; Next router context.
outputs: exported UseDayResult interface and useDay hook returning
         data/loading/error.
dependencies: React useState/useEffect; next/navigation useRouter;
              lib/grace/api/client fetchDay and ApiError;
              hooks/use-telegram-auth; lib/log logEvent;
              packages/contracts TodayPayload.
side_effects: structured browser logs; existing 100 ms delay; delegated day
              request; React state updates; router.replace('/onboarding').
emitted_logs: day.viewed, auth.tg_login_started, day.payload_built,
              system.error, profile.lazy_created, auth.session_expired.
invariants:
  - The existing render-path INIT log remains and emits day.viewed.
  - While authLoading is true, the effect logs auth.tg_login_started, does not
    fetch and leaves the current loading state unchanged.
  - The load effect remains dependent on [date, router, authLoading].
  - The existing 100 ms delay occurs before fetchDay(date).
  - Successful payload state is applied only when the effect is not cancelled.
  - HTTP 422 with code NOT_ONBOARDED or HTTP 409 with exact message
    'Profile is incomplete' logs profile.lazy_created and redirects to
    /onboarding without surfacing an error.
  - HTTP 401 logs auth.session_expired and replaces the ApiError message with
    the existing Russian Telegram authorization message before exposing it.
  - Unknown failures become ApiError('Unknown error', 500).
  - Cleanup logs day.viewed and sets the local cancellation flag.
failure_policy: log system.error; redirect recognized incomplete-profile
                failures; otherwise expose the preserved/normalized ApiError
                and finish loading only when the effect is active.
public_entrypoints: UseDayResult, useDay.
semantic_blocks: RESULT_SHAPE; DAY_STATE; RENDER_LOG; AUTH_GATE;
                 DAY_LOAD_EFFECT; SUCCESS_APPLY; ERROR_ROUTING;
                 UNAUTHORIZED_COPY; CANCEL_CLEANUP.
owned_tests:
  - __tests__/hooks/useDay.test.ts
  - __tests__/app/day-page.test.tsx
```

List only the six exact event names above. Do not claim `logStart`,
`logSuccess` or `logFailure`; this file calls only `logEvent`. Do not rename
the semantically odd but real `profile.lazy_created` event in this comment-only
wave.

## 7. Exact truthful contract — `lib/grace/index.ts`

```text
ID: M-FRONTEND-GRACE-INDEX
AI_HEADER name: GRACE_FRONTEND_INDEX
AI_HEADER meaning: public barrel for the GRACE frontend API and hooks.
ROLE: Pure re-export boundary for GRACE API client functions/errors, hooks and
      hook result types.
purpose: Provide the existing stable import surface without adding runtime
         behavior.
owns: lib/grace/index.ts
inputs: none.
outputs: exact exports fetchDay, fetchCalendar, ApiError, ApiContractError,
         useDay, useCalendar, UseDayResult and UseCalendarResult.
dependencies: lib/grace/api/client; lib/grace/hooks/useDay;
              lib/grace/hooks/useCalendar.
side_effects: none introduced by this barrel.
emitted_logs: none.
invariants:
  - Value exports and type-only exports remain exactly separated as today.
  - All eight public names and their source modules remain unchanged.
  - The module contains no wrapper logic or new initialization.
failure_policy: none locally; import/runtime failures propagate from exported
                dependency modules.
public_entrypoints: fetchDay, fetchCalendar, ApiError, ApiContractError,
                    useDay, useCalendar, UseDayResult, UseCalendarResult.
semantic_blocks: API_CLIENT_EXPORTS; HOOK_EXPORTS; RESULT_TYPE_EXPORTS.
owned_tests: none direct; covered through typecheck and hook/API consumers.
```

Do not convert type exports into value exports and do not consolidate/reorder
the existing runtime statements.

## 8. Mandatory preflight

Before editing:

1. completely read 141 and 151;
2. confirm W2C-3 has been pushed and local HEAD = tracking = remote feature;
3. record the exact accepted HEAD SHA in the callback;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked paths remain;
6. run the full marker gate and record exact baseline 3/3/44/47 with the three
   allowlisted paths only;
7. hash all three files and extract/hash runtime suffixes beginning at:
   - `'use client';` for both hooks;
   - the first `export` statement for `lib/grace/index.ts`;
8. record imports/exports, function declarations, dependency arrays, event
   names, string literals and existing marker counts;
9. prove runtime services untouched and ports `3003`, `8001`, `18092` absent.

Stop on mismatch. Never reset, restore, checkout, stash, amend or rebase.

## 9. Mechanical equivalence proof after editing

Require all of the following:

```text
tracked changed paths               exact 3 allowlisted files
changed executable lines            zero
runtime suffix hashes               unchanged 3/3
comment-stripped source             equivalent 3/3
imports/exports                     unchanged
function/interface declarations     unchanged
hook dependency arrays              unchanged
event names/log metadata            unchanged
timeout/status/redirect/error copy  unchanged
existing function/block markers     unchanged
module IDs                          unique and paired 3/3
AI headers                          exactly one per file in first 30 lines
canonical fields                    present 3/3
legacy duplicate mini-headers       absent
generic/false phrases               absent
index                               empty
```

Run `git diff --check` and inspect the complete three-file diff manually.

## 10. Required gates

### 10.1. GRACE and strict negative harness

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  lib/grace/hooks/useCalendar.ts \
  lib/grace/hooks/useDay.ts \
  lib/grace/index.ts
bash scripts/grace/check-negative.sh
```

Require: self-tests 11 PASS; authorized files 3/3 clean; negative harness
6 PASS / 0 FAIL with exact reasons.

### 10.2. Static and targeted regression

```bash
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/hooks/useCalendar.test.ts \
  __tests__/hooks/useDay.test.ts \
  __tests__/app/day-page.test.tsx
```

Require: ESLint zero errors/warnings; typecheck PASS; exact 3 files / 17 tests
PASS.

### 10.3. Completed full marker and aggregate frontend guard

Run the full marker gate and require exactly:

```text
violations=0
failing_paths=0
green_paths=47
checked_paths=47
```

Then run:

```bash
pnpm guardrails:frontend
```

It must exit zero and pass every stage, including ESLint, typecheck, full
marker gate and strict negative tests. This is no longer a diagnostic
expected-failure run.

Finally require `git diff --check` PASS_ZERO and re-run exact scope/runtime
audit. No production build or full Vitest in this implementation callback;
those remain mandatory in final release-candidate validation.

## 11. Frozen and forbidden state

Never touch or stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Do not change env, systemd, nginx, database, Docker or runtime processes. Do
not start ports `3003`, `8001` or `18092`. Do not commit/push, start final RC,
merge to main or deploy.

## 12. Required callback

```text
READY_STAGE_2_W2C4_GRACE_LIBRARY_REVIEW
base_head: <accepted pushed W2C3 sha>
tracked_scope: EXACT_3_LIB_GRACE_FILES
comment_only_equivalence: PASS_3
runtime_suffix_hashes: UNCHANGED_3
imports_exports_behavior: UNCHANGED
hook_dependencies_behavior: UNCHANGED
event_names_and_metadata: UNCHANGED
module_ids: UNIQUE_AND_PAIRED_3
authorized_paths_grace: PASS_3
grace_linter_self_tests: 11_PASS
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
typecheck: PASS
targeted_tests: 3_FILES_17_PASS
remaining_grace: 0_VIOLATIONS_0_FAILING_47_GREEN_47_CHECKED
guardrails_frontend: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop for architect review and separate acceptance.
