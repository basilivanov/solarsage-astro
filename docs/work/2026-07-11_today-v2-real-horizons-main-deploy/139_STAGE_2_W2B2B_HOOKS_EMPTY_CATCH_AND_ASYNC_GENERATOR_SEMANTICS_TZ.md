# Stage 2.W2B-2B — hooks, best-effort storage catches and async-generator semantics

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`18d51de15b5050a229bf424c8f283e8fa1ccf276`
Parent: `138_STAGE_2_W2B2A_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`
Evidence: `/tmp/stage2-w2b2a-accepted-eslint.json`

Статус: **AUTHORIZED FINAL W2B SOURCE SEMANTIC CORRECTION — NO CONFIG/SUPPRESSION, NO COMMIT/PUSH**

## 1. Objective

The only remaining frontend ESLint findings are:

```text
6 errors / 5 warnings / 6 paths
```

This wave fixes all of them through truthful code semantics:

- one failing async-generator test keeps its “fail before first chunk” behavior;
- one horary polling effect depends on a primitive status, not a mutable object;
- calendar and week collections have stable memoized identities;
- five deliberately swallowed localStorage failures receive explicit
  best-effort policy comments.

Exit must be:

```text
pnpm lint = zero errors / zero warnings
```

No ESLint config/rule/ignore/global/dependency change and no eslint-disable
comment is allowed.

## 2. Mandatory preflight

Before editing:

1. read this document completely;
2. prove branch/local/tracking/remote feature equal the base SHA above;
3. prove `main`/`origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor;
4. prove tracked worktree and index clean;
5. prove only five frozen unrelated untracked paths plus architect doc 139;
6. record hashes of the six authorized source files and doc 139;
7. reproduce exact baseline `6 errors / 5 warnings / 6 paths` from current
   aggregate ESLint JSON;
8. prove canonical services unchanged and 3003/8001/18092 absent.

Frozen paths are never touched/staged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Stop on mismatch. No reset/rebase/force operation.

## 3. Exact authorized scope

Edit only:

```text
__tests__/hooks/useChat.test.ts
app/(grace)/readings/horary/[id]/page.tsx
components/calendar/calendar-screen.tsx
components/today/week-strip.tsx
hooks/use-onboarded.ts
hooks/use-telegram-auth.ts
```

Architect doc 139 remains byte-identical and untracked. No new test file,
config, dependency, contract, generated artifact, selector, copy or public API
change.

## 4. Async-generator failure test

In `__tests__/hooks/useChat.test.ts`, preserve the test intent: the mocked
stream must reject before yielding any assistant chunk, so `useChat` executes
its error path and appends only the honest fallback assistant message.

Replace only this body:

```ts
async function* () {
  throw new Error('Network error')
}
```

with:

```ts
async function* () {
  yield await Promise.reject<string>(new Error('Network error'))
}
```

This contains a real syntactic yield for `require-yield`, but the awaited
rejection occurs before any value is emitted. Preserve all assertions and
other stream mocks.

Required focused proof: the test still produces exactly two messages (user +
fallback assistant), and fallback copy remains unchanged.

## 5. Horary polling dependency: status primitive, never whole object

In `app/(grace)/readings/horary/[id]/page.tsx`:

1. derive immediately before the polling effect:

```ts
const questionStatus = question?.status
```

2. change only the effect’s entry guard to test `questionStatus` instead of
   reading `question`/`question.status`;
3. set its dependency array to:

```ts
[id, questionStatus]
```

Do not add `question` itself. Depending on the whole polled object would tear
down/recreate the interval after every response, reset `startTime`, and could
prevent the intended 30-second timeout from ever firing.

Preserve:

- 2-second polling cadence;
- 30-second timeout measured from one polling-status lifecycle;
- terminal statuses `answered`, `failed`, `expired`;
- explicit interval clear on terminal/auth/server/network outcomes;
- cleanup, logging, error states and rendered UI.

Do not refactor the load/retry effects or introduce a new helper/constant in
this narrow wave.

## 6. Calendar stable days identity

In `components/calendar/calendar-screen.tsx`, replace:

```ts
const days = payload?.days ?? []
```

with exactly:

```ts
const days = useMemo(() => payload?.days ?? [], [payload?.days])
```

Keep all three existing dependent memos and their dependency arrays. This
stabilizes the empty-array identity across unrelated renders while changing it
when the backend day array changes.

Do not change payload loading, month navigation, matrix construction,
selection, public props, access semantics or test selectors.

## 7. Week strip stable weekly identity

In `components/today/week-strip.tsx`:

1. add `useMemo` to the existing React import;
2. replace the current eager `start`/`days`/`range` setup with this semantic
   shape:

```ts
const startKey = startOfWeek(selectedDate).getTime()
const days = useMemo(() => {
  const weekStart = new Date(startKey)
  return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index))
}, [startKey])
const range = formatWeekRange(new Date(startKey))
```

3. remove the later duplicate `startKey` declaration;
4. change the status-fetch effect dependencies to:

```ts
[days, disableRemoteStatusFetch]
```

Architectural invariants:

- rerenders and selected-day changes within the same Monday–Sunday week reuse
  the same `days` array and do not restart seven remote requests;
- crossing into another week changes `startKey`, recomputes days and reloads;
- toggling `disableRemoteStatusFetch` still clears or loads statuses;
- cleanup still prevents late state writes;
- render dates/range, access, `data-testid`, labels and onSelect remain exact.

Do not depend on the raw `selectedDate` object, use an eslint suppression, move
the request outside the effect or change per-day error fallback.

## 8. Best-effort localStorage catches

The five empty catches intentionally prevent storage restrictions from
breaking auth/onboarding. Keep them behaviorally empty but make the policy
explicit with comments. Do not log referral codes or storage values.

### `hooks/use-onboarded.ts`

Expand the three empty catches with these exact comments:

1. backend-to-storage synchronization:

```ts
catch {
  // Browser storage is best-effort; authenticated backend state remains authoritative.
}
```

2. `setOnboarded` persistence:

```ts
catch {
  // Keep React state authoritative when browser storage is unavailable.
}
```

3. `resetOnboarded` cleanup:

```ts
catch {
  // Reset still succeeds in React state when browser storage is unavailable.
}
```

Preserve all fetch, logger and state transitions.

### `hooks/use-telegram-auth.ts`

Replace only the two empty catches:

1. referral-code persistence:

```ts
catch {
  // Referral persistence is best-effort; authentication must continue.
}
```

2. persisted-code removal after claim:

```ts
catch {
  // Referral cleanup is best-effort after a completed claim attempt.
}
```

Do not alter the non-empty fallback read catch, referral claim conditions,
self-referral guard, auth result, logging payloads or network calls.

## 9. Forbidden shortcuts

Do not:

- add eslint-disable or change any rule severity;
- add `question` as a polling dependency;
- use a fresh `days` array in a hook dependency;
- add dummy/unreachable `if (false) yield` code;
- swallow a new error path;
- add storage/referral data to logs;
- change public selectors, copy, ports, runtime, contracts or mocks;
- edit any file outside the exact six-path scope.

## 10. Required gates

Run targeted tests first:

```bash
npx vitest run \
  __tests__/hooks/useChat.test.ts \
  __tests__/hooks/useOnboarded.test.ts \
  __tests__/hooks/useTelegramAuth.test.ts \
  __tests__/components/CalendarScreen.test.tsx \
  __tests__/components/WeekStrip.test.tsx \
  __tests__/horary/horary-error-state.test.tsx
```

Then run:

```bash
pnpm typecheck
pnpm lint
npx vitest run
pnpm contracts:check
pnpm guardrails:prod
NEXT_DIST_DIR=.next-stage2-w2b2b pnpm build
git diff --check
```

Required:

```text
pnpm lint                  PASS_ZERO_ERRORS_ZERO_WARNINGS
full Vitest                1067 PASS
contracts check            110 PASS_ZERO_DRIFT
isolated production build  PASS
```

Run `pnpm guardrails:frontend` as a diagnostic after `pnpm lint`. It is expected
to pass its ESLint and typecheck sections, then stop only at the pre-existing
GRACE marker gate owned by W2C. Capture:

```text
/tmp/stage2-w2b2b-guardrails-frontend.log
```

Report exact remaining GRACE violation/path count. Any ESLint/typecheck failure
or any failure before the marker gate rejects this wave.

After build, remove only the exact generated
`.next-stage2-w2b2b` directory after proving it is a repository-local ignored
Next output and not a symlink. Do not remove canonical `.next-prod` or any other
build tree.

## 11. Final state and callback

Tracked diff exact six authorized source paths. Index empty. Doc 139 unchanged.
Frozen paths untouched. Runtime unchanged and ports absent. No commit/push.

Callback:

```text
READY_STAGE_2_W2B2B_FINAL_FRONTEND_LINT_REVIEW
tracked_scope: EXACT_6
async_generator_failure_before_first_chunk: PRESERVED
horary_poll_lifecycle: STATUS_PRIMITIVE_STABLE
calendar_days_identity: MEMOIZED
week_days_identity: MEMOIZED_BY_START_KEY
storage_failure_policy: BEST_EFFORT_EXPLICIT_NO_DATA_LOGGING
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
targeted_tests: <exact count> PASS
typecheck: PASS
vitest_full: 1067 PASS
contracts_check: 110 PASS_ZERO_DRIFT
prod_guard: PASS
isolated_build: PASS_CLEANED
frontend_guard_eslint_typecheck: PASS
remaining_grace_marker_gate: <exact violations / paths>
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_doc: UNCHANGED_139
```

Then stop for architect review.
