# Stage 2.W2B-2A — mechanical unused cleanup and generated directive source fix

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`cf37dc951dd385534095b6f64d6e64582a92edd0`
Parent: `136_STAGE_2_W2B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`
Evidence: `/tmp/stage2-w2b1-accepted-eslint.json`

Статус: **AUTHORIZED EXACT SOURCE CLEANUP — NO HOOK/EMPTY/GENERATOR-TEST SEMANTIC FIX, NO COMMIT/PUSH**

## 1. Objective and hard boundary

Accepted TypeScript-aware lint leaves:

```text
33 errors / 6 warnings / 28 paths
```

This subwave owns only:

- 27 truthful `@typescript-eslint/no-unused-vars` errors;
- the one unused `/* eslint-disable */` warning in generated Zod output,
  corrected at the generator source and regenerated deterministically.

It must intentionally leave untouched for W2B-2B:

```text
5 no-empty errors
1 require-yield error
5 react-hooks/exhaustive-deps warnings
```

Expected exit inventory after this subwave:

```text
6 errors / 5 warnings / 6 paths
```

No lint rule/config/dependency change, no suppression, no hook dependency edit,
no empty-catch edit and no async-generator-test edit is authorized here.

## 2. Mandatory preflight

Before editing:

1. read this document completely;
2. prove branch, local HEAD, tracking ref and remote feature equal the base SHA;
3. prove `main`/`origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor;
4. prove tracked worktree/index clean;
5. prove only the five frozen unrelated untracked paths plus architect doc 137
   exist;
6. copy the accepted JSON to a separate `/tmp` baseline if needed and record
   hashes for every authorized path plus doc 137;
7. prove canonical services unchanged and 3003/8001/18092 absent.

Frozen paths are never touched or staged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Stop on mismatch. No reset/rebase/force operation.

## 3. Exact authorized path set

Coder may edit only these 25 tracked paths:

```text
__tests__/contracts/access.test.ts
__tests__/contracts/calendar.test.ts
__tests__/contracts/chat.test.ts
__tests__/contracts/city.test.ts
__tests__/contracts/natal.test.ts
__tests__/contracts/profile.test.ts
__tests__/contracts/today.test.ts
__tests__/hooks/useChat.test.ts
__tests__/hooks/useTelegramAuth.test.ts
__tests__/lib/production-guard.test.ts
app/(grace)/debug/page.tsx
components/calendar/calendar-screen.tsx
components/onboarding/onboarding-flow.tsx
components/today/concrete-day-advice.tsx
components/today/day-chart.tsx
components/today/today-screen.tsx
components/today/why-expanded.tsx
components/ui/use-toast.ts
e2e/edge-cases.spec.ts
hooks/use-chat.ts
hooks/use-toast.ts
lib/grace/hooks/useDay.ts
lib/log/index.ts
scripts/contracts/generate.sh
packages/contracts/_generated.zod.ts
```

Document 137 remains unchanged and untracked. Do not edit `eslint.config.mjs`,
package metadata, other generated files, GRACE marker files or any W2B-2B path
outside the exact overlap above.

## 4. Exact import/dead-local cleanup

Perform these removals only; do not replace genuine dead code with underscore
aliases when it can be safely deleted.

### Contract tests

Remove only the listed unused imports; test bodies/names/fixtures/assertions
remain byte-equivalent:

```text
__tests__/contracts/access.test.ts    AccessInfoSchema
__tests__/contracts/calendar.test.ts  DayStatusSchema, DayStatusMapSchema
__tests__/contracts/chat.test.ts      ChatHistorySchema
__tests__/contracts/city.test.ts      CitySchema
__tests__/contracts/natal.test.ts     NatalReportSchema
__tests__/contracts/profile.test.ts   ProfileSchema
__tests__/contracts/today.test.ts     TodayPayloadSchema
```

### Test-only locals/imports

- `__tests__/hooks/useChat.test.ts`: delete only the unused local
  `const ms = new Map<string, string>()` inside the hoisted setup. Do not touch
  the later failing async generator yet; `require-yield` must remain for
  W2B-2B.
- `__tests__/hooks/useTelegramAuth.test.ts`: remove only unused `act` from the
  testing-library import.
- `__tests__/lib/production-guard.test.ts`: delete both unused
  `const origEnv = { ...process.env }` declarations. Preserve `stubEnv`,
  `unstubAllEnvs` and mock cleanup behavior.
- `e2e/edge-cases.spec.ts`: remove only unused `prevBtn`; preserve the existing
  next-button navigation scenario and selectors.

### Runtime/component dead bindings

- `app/(grace)/debug/page.tsx`: change `catch (e)` at JSON parsing to `catch`
  with no binding. Preserve the exact thrown error and fetch flow.
- `components/onboarding/onboarding-flow.tsx`: delete only `currentCityStr` and
  `birthdayCityStr`; retain `effectiveCurrentCity` and
  `effectiveBirthdayCity`, which build the structured API locations.
- `components/today/concrete-day-advice.tsx`: delete only the unused `label`
  inside the navigator button loop around current line 163. Preserve the
  separately used `label` inside `SphereDetails`.
- `components/today/day-chart.tsx`: remove only unused `getPlanetLabel` import.
- `components/today/why-expanded.tsx`: remove the unused second `index`
  parameter from `sections.map`; preserve keying by `section.id` and all
  paragraph indexes.
- `hooks/use-chat.ts`: remove only unused type import `ChatEvent`.
- `lib/grace/hooks/useDay.ts`: destructure only
  `isLoading: authLoading` from `useTelegramAuth`; do not rename or change the
  authentication/loading behavior.
- `lib/log/index.ts`: remove the dead `LogContext` interface only. Preserve all
  live context globals, public setters and envelope behavior.

## 5. Preserve public prop APIs while removing unused bindings

The following props remain in their public `Props` type and remain accepted by
callers/tests. Do not delete or rename the public fields and do not change
callers.

- `components/calendar/calendar-screen.tsx`: change function destructuring
  from `{ access, onOpenDay }` to `{ onOpenDay }`; keep `access: AccessInfo` in
  `Props` for compatibility.
- `components/today/today-screen.tsx`: remove `calendarLunar` and
  `importantToday` only from the function destructuring list; keep both fields,
  imports and documented input contract in `Props`. Preserve page/test call
  sites exactly.

No underscore alias is necessary when an accepted object prop can simply stay
undestructured.

## 6. Replace type-only runtime maps in both toast modules

In both:

```text
components/ui/use-toast.ts
hooks/use-toast.ts
```

the runtime `const actionTypes = {...} as const` exists only to derive a type.
Remove that runtime object and replace `type ActionType = typeof actionTypes`
with this pure type map:

```ts
type ActionType = {
  ADD_TOAST: 'ADD_TOAST'
  UPDATE_TOAST: 'UPDATE_TOAST'
  DISMISS_TOAST: 'DISMISS_TOAST'
  REMOVE_TOAST: 'REMOVE_TOAST'
}
```

Keep the existing `ActionType['...']` discriminants and reducer runtime string
literals unchanged. Do not merge the duplicate modules, alter toast timing,
exports, reducer behavior or hook dependencies in this wave.

## 7. Generated Zod directive: fix source, then regenerate

`packages/contracts/_generated.zod.ts` is generated and must not be hand-edited.
The warning originates from `scripts/contracts/generate.sh` line that prepends:

```text
/* eslint-disable */
```

to the Zod artifact.

In the second stamping block only (the block for `_generated.zod.ts`), remove
that single echo line. Preserve:

- the disable banner for `_generated.ts`;
- all autogenerated/source/regenerate banners;
- `generate-zod.cjs` and Handlebars template;
- atomic temp-file replacement.

Then run:

```bash
pnpm contracts:generate
```

Required generated diff:

```text
packages/contracts/_generated.zod.ts: only first line /* eslint-disable */ removed
packages/contracts/_generated.ts: unchanged
packages/contracts/openapi.json: unchanged
```

If generation changes any schema, order, banner, OpenAPI or `_generated.ts`
content, stop and report rather than accepting drift.

Do not run canonical `pnpm contracts:check` as a success gate before the
accepted generated diff is committed: its final git-diff step is expected to
reject an intentional uncommitted generated change. Instead run its semantic
sub-gates in section 9; canonical check will be mandatory post-commit.

## 8. Explicitly forbidden W2B-2B edits

Leave these exact findings unchanged:

```text
__tests__/hooks/useChat.test.ts                 require-yield = 1
app/(grace)/readings/horary/[id]/page.tsx      hooks warning = 1
components/calendar/calendar-screen.tsx        hooks warnings = 3
components/today/week-strip.tsx                 hooks warning = 1
hooks/use-onboarded.ts                          no-empty = 3
hooks/use-telegram-auth.ts                      no-empty = 2
```

Do not add comments to empty catches, memoize dependencies, modify effects or
alter the failing async generator yet. This keeps review mechanically isolated.

## 9. Gates

Run:

```bash
pnpm typecheck
npx vitest run
pnpm guardrails:prod
git diff --check
```

Run contract semantic gates without the final expected-dirty diff check:

```bash
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  scripts/contracts/test_check_compat.py -q
bash scripts/contracts/today_fixture.sh --check
```

Expected contract-focused total is 110 passed and fixture check passes.

Run aggregate ESLint as expected non-zero JSON:

```bash
pnpm exec eslint . -f json > /tmp/stage2-w2b2a-eslint.json
```

Required exact result:

```text
6 errors / 5 warnings / 6 paths
@typescript-eslint/no-unused-vars = 0
unused eslint-disable directive = 0
no-empty = 5 errors
require-yield = 1 error
react-hooks/exhaustive-deps = 5 warnings
parsing/fatal/unmatched/build-doc findings = 0
```

Verify all 25 authorized diffs manually. No source behavior, test assertion,
selector, public prop type, contract schema or output except the removed
generated directive may change.

## 10. Final state and callback

Tracked diff must be exactly the 25 authorized paths. Index empty. Architect
doc 137 unchanged. Frozen paths untouched. No commit/push/runtime operation.

Callback:

```text
READY_STAGE_2_W2B2A_MECHANICAL_SOURCE_REVIEW
tracked_scope: EXACT_25
unused_errors: ZERO
generated_directive_warning: ZERO_VIA_GENERATOR_SOURCE
generated_zod_diff: FIRST_LINE_ONLY
openapi_generated_ts_drift: ZERO
remaining_expected: 6 errors / 5 warnings / 6 paths
typecheck: PASS
vitest_full: <exact count> PASS
contract_semantic_tests: 110 PASS
fixture_check: PASS
prod_guard: PASS
git_diff_check: PASS
public_props: PRESERVED
runtime_behavior: UNCHANGED
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_doc: UNCHANGED_137
```

Then stop for architect review.
