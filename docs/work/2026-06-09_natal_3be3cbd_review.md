# Review: Natal/Gender frontend follow-up

Date: 2026-06-09
Reviewed commit: 3be3cbd09a7459d3369f4d2f478afba73ddacd46
Previous review: `docs/work/2026-06-09_natal_a615ca8_review.md`
Verdict: REJECTED

## Scope reviewed

Commit message: `fix: remove silent female default, add frontend tests`.

Changed files:

- `components/onboarding/onboarding-flow.tsx`
- `__tests__/reducers/onboarding-reducer.test.ts`
- `__tests__/contracts/profile.test.ts`
- `__tests__/hooks/useOnboarded.test.ts`
- `__tests__/horary/horary-error-state.test.tsx`
- `app/(grace)/readings/horary/[id]/page.tsx`

This follow-up targets the remaining blockers from the natal/gender review:

1. Remove silent `female` fallback in onboarding save.
2. Add frontend tests for gender onboarding / natal preview-related UI/error behavior.

## Positive findings

### F1 — silent `?? "female"` fallback removed

Status: PARTIAL

The explicit fallback was removed from `onboarding-flow.tsx`:

```ts
gender: state.gender,
```

This is directionally correct: the app no longer silently writes `female` when `state.gender` is missing.

### F2 — reducer tests for gender step were added

Status: ACCEPTED

The reducer tests now cover:

- `set_gender` to `male`;
- `set_gender` to `female`;
- `isStepValid` returns false when `step === "gender"` and `gender === null`;
- `isStepValid` returns true for `male`/`female`;
- `selectProgress` updated for the new 6-step onboarding flow.

This covers the reducer-level validation.

### F3 — profile contract tests updated

Status: ACCEPTED

Profile contract tests now include required `gender` in valid profile fixtures.

### F4 — horary error-state tests added

Status: ACCEPTED FOR HORARY COVERAGE

The commit adds frontend tests for horary detail error states:

- 404/null → `Вопрос не найден`;
- 401 → `Нужно авторизоваться`;
- 500 → `Сервер временно недоступен`;
- network error → `Нет соединения`.

This is useful coverage, but it belongs mostly to the horary cleanup. It does not fully close the natal/gender onboarding acceptance criteria.

## Blocker

### B1 — onboarding save path can still persist `gender: null` and likely fails TypeScript typecheck

Status: BLOCKER

The explicit `?? "female"` fallback was removed, but no guard was added before constructing/saving the profile.

Current code still builds a `Profile` object with:

```ts
gender: state.gender,
```

But `state.gender` is typed as:

```ts
gender: "male" | "female" | null
```

while `ProfileSchema` requires:

```ts
gender: z.enum(["male", "female"])
```

Because `tsconfig.json` has `strict: true` and `noEmit: true`, this should fail `pnpm typecheck` / `guardrails:frontend`. Vitest can pass while the TypeScript typecheck still fails.

Even ignoring typecheck, the runtime save path still lacks an explicit guard. If a future navigation/refactor/test setup reaches `finish()` with `state.gender === null`, the app can call:

- `saveProfile(profile)` with invalid local profile;
- `updateProfile({ gender: null, ... })`.

That violates the requirement from the previous review: do not default gender, and also do not persist an incomplete gender selection.

Required fix:

1. Add an explicit guard at the beginning of `finish()` before constructing `profile`:

```ts
if (!state.gender) {
  dispatch({ type: "go_to_step", value: "gender" }) // or another project-appropriate event
  return
}
```

If the reducer does not have `go_to_step`, add a small explicit event such as:

```ts
| { type: "go_to_step"; value: StepKey }
```

or implement another local UI error path.

2. After the guard, narrow the value:

```ts
const gender = state.gender
```

and use only `gender` in both `Profile` and `updateProfile()`:

```ts
gender,
...
await updateProfile({ gender, ... })
```

3. Add a component-level test or a small extracted helper test proving that `finish()` does not call `saveProfile()` / `updateProfile()` when `gender` is missing.

4. Provide `pnpm typecheck` or `guardrails:frontend` evidence, not only Vitest count.

## Remaining test gap

### R1 — reducer tests are not enough to prove onboarding cannot finish without gender

The reducer correctly says `gender` step is invalid when gender is null. But `OnboardingFlow.finish()` itself is not tested, and the active component currently bypasses `isStepValid()` in the save path.

Recommended frontend tests:

- render onboarding flow in/near done state with missing gender and call finish;
- assert `updateProfile` is not called;
- assert user is returned to gender step or sees a validation error;
- assert selected `male`/`female` is sent to `updateProfile`.

## Verification evidence

Coder/local evidence from user message:

- 493 frontend tests pass.
- 277 backend tests pass.
- Total: 770 passed.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `3be3cbd09a7459d3369f4d2f478afba73ddacd46`.
- No combined status checks were visible for the commit.

Important limitation:

- Test counts do not prove TypeScript typecheck passed.
- `package.json` has a dedicated `typecheck` script, and frontend guardrails include `tsc --noEmit`; this evidence was not provided.

## Final decision

REJECTED.

The silent `female` default was removed, and useful reducer/frontend tests were added. But the save path now accepts a nullable gender value where the profile contract requires `male|female`. Add an explicit `finish()` guard, narrow the type before constructing the profile/update payload, and provide typecheck/guardrails evidence.
