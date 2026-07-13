# Stage 2.W2B-2B — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`18d51de15b5050a229bf424c8f283e8fa1ccf276`
Accepted implementation:
`139_STAGE_2_W2B2B_HOOKS_EMPTY_CATCH_AND_ASYNC_GENERATOR_SEMANTICS_TZ.md`

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

## 1. Accepted evidence

Architect independently reviewed all six diffs and accepts:

```text
async generator failure             rejects before first emitted chunk
horary poll dependency              id + primitive questionStatus
horary 30-second lifecycle          not reset by same-status object refreshes
calendar days identity              memoized by payload.days
week days identity                  memoized by Monday startKey
storage catches                     explicit best-effort policy, no data logging
ESLint                              zero errors / zero warnings
targeted Vitest                     51 PASS
typecheck                           PASS
full Vitest                         1067 PASS
contracts check                     110 PASS / zero drift
production guard                   PASS
isolated production build           PASS
isolated build tree                 safely removed
next-env.d.ts / tsconfig.json       restored byte-identical to HEAD
working diff check                 PASS
runtime/services                    unchanged
ports 3003/8001/18092              absent
```

Exact W2C entry inventory:

```text
GRACE violations       49
failing paths          41
already-green paths     6
total checked paths    47
```

Do not report “47 failing paths”: 47 is the total checked set. No further edit
is authorized in this acceptance wave.

## 2. Mandatory preflight

Before staging:

1. read this document completely;
2. fetch origin without merge/rebase;
3. prove branch/local/tracking/remote feature remain at the base SHA;
4. prove `main`/`origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor;
5. prove index empty;
6. prove tracked diff exact six accepted paths from document 139;
7. prove next-env.d.ts and tsconfig.json have zero diff;
8. prove `.next-stage2-w2b2b` absent;
9. prove docs 139 and 140 are the only task docs untracked;
10. prove only the five frozen unrelated untracked paths otherwise remain;
11. prove runtime/services/ports unchanged.

Stop on mismatch. No source edit, reset, rebase, force push, build, runtime
operation or W2C work.

## 3. Exact staging

Stage only these eight explicit paths:

```text
__tests__/hooks/useChat.test.ts
app/(grace)/readings/horary/[id]/page.tsx
components/calendar/calendar-screen.tsx
components/today/week-strip.tsx
hooks/use-onboarded.ts
hooks/use-telegram-auth.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/139_STAGE_2_W2B2B_HOOKS_EMPTY_CATCH_AND_ASYNC_GENERATOR_SEMANTICS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/140_STAGE_2_W2B2B_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit paths; never `git add .`, `-A` or a directory.

Before commit require:

```text
staged count                  exactly 8
staged set                    exact list above
unstaged tracked diff         empty
next-env/tsconfig in index    no
frozen paths in index         no
git diff --cached --check     PASS
```

Stop for architect correction on any doc EOF issue.

## 4. Commit and post-commit gates

Create exactly one commit:

```text
fix(frontend): stabilize hook lint semantics
```

After commit and before push run:

```bash
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/hooks/useChat.test.ts \
  __tests__/hooks/useOnboarded.test.ts \
  __tests__/hooks/useTelegramAuth.test.ts \
  __tests__/components/CalendarScreen.test.tsx \
  __tests__/components/WeekStrip.test.tsx \
  __tests__/horary/horary-error-state.test.tsx
npx vitest run
pnpm contracts:check
pnpm guardrails:prod
git diff --check origin/main...HEAD
```

Required exact counts remain targeted 51, full 1067, contracts 110. ESLint
must be fully clean.

Run `pnpm guardrails:frontend` as expected-nonzero diagnostic and capture to:

```text
/tmp/stage2-w2b2b-accepted-guardrails-frontend.log
```

Require:

```text
frontend ESLint section      PASS
frontend typecheck section   PASS
failure stage                GRACE marker gate only
violations                   49
failing paths                41
green paths                  6
checked paths                47
```

Do not alter GRACE markers in this commit. The already accepted isolated build
does not need to be repeated in this commit/push-only wave.

## 5. Normal push and final equality

Push normally to the existing feature branch, never force. Then prove:

```text
local HEAD = tracking ref = remote feature SHA
tracked worktree clean
index empty
only five frozen unrelated untracked paths remain
main untouched
runtime/env/systemd untouched
3003/8001/18092 absent
```

Do not begin W2C before callback.

## 6. Callback

```text
PUSHED_STAGE_2_W2B2B_FINAL_FRONTEND_LINT
commit: <sha> fix(frontend): stabilize hook lint semantics
staged_scope: EXACT_8
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
targeted_tests: 51 PASS
typecheck: PASS
vitest_full: 1067 PASS
contracts_check: 110 PASS_ZERO_DRIFT
prod_guard: PASS
frontend_guard_eslint_typecheck: PASS
remaining_grace: 49 violations / 41 failing paths / 47 checked paths
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
main_deploy: NOT_STARTED
```

Then stop.
