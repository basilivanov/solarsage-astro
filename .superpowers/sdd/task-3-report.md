# Task 3 Report: Make Profile And Access Real-Data First

## Status

Implemented and verified on branch `codex/real-data-frontend-migration`.

## Summary

- Reworked `useProfile` to hydrate from `GET /api/profile`, persist edits through `PUT /api/profile`, expose saving/error state, and cache only API-sourced profiles.
- Reworked profile mapping so empty backend profiles stay empty instead of using Kyiv/Lisbon defaults, while real birth/current/birthday location city, latitude, longitude, and timezone are preserved.
- Updated profile edit UI so saves await the backend path and validation errors remain visible in the sheet.
- Added `GET /api/access`, backed by `AccessService.get_summary()`, and wired it into FastAPI.
- Reworked `useAccess` and `lib/api/access.ts` to read authenticated backend access state instead of localStorage/synthetic state.
- Hid the profile dev access controls outside `NODE_ENV=development`.
- Updated onboarding cache behavior so local profile cache is written only from the backend response.
- Regenerated `packages/contracts/openapi.json` and `packages/contracts/_generated.ts` for `AccessSummary.accessStart`.

## Tests

- `pnpm exec vitest run __tests__/hooks/useProfile.test.ts __tests__/lib/profile.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts` passed: 66 tests.
- `cd apps/api && source .venv/bin/activate && python -m pytest tests/test_profile_endpoints.py -q` passed: 18 tests.
- `npm run contracts:check` passed.
- Additional: `pnpm exec vitest run __tests__/hooks/useAccess.test.ts` passed: 3 tests.
- Additional: `pnpm exec tsc --noEmit` passed.
- Additional: `git diff --check` passed.

## Self-Review

- No runtime product imports from `lib/demo-data`, `lib/demo-mode`, or `lib/mocks/*` were introduced.
- The only `rg` match for `lib/mocks` is an existing comment in `lib/profile-meta.ts`.
- `AccessSummary` now includes `accessStart`; contract generation is idempotent after staging generated artifacts.

## Concerns

- No known concerns from the initial implementation remained before review.

## Fix Review

### Review Findings Addressed

- Blocked profile editing in `ProfileScreen` until `GET /api/profile` hydration succeeds, and added a hook-level guard that rejects updates before hydration without issuing `PUT /api/profile`.
- Preserved the exact backend city display string and metadata when a city edit is untouched. A newly selected city now persists its formatted display, latitude, longitude, and timezone.
- Changed onboarding so completion occurs only after a successful profile `PUT`. Failed persistence remains on the completion step, shows a retryable error, and does not set the onboarded state or route onward. The welcome-step bypass was removed.
- Removed the non-functional development access switcher and the no-op `useAccess().setState` API. Access remains backend-owned with no localStorage override.

### Test Evidence

The following command completed successfully:

```bash
pnpm exec vitest run __tests__/hooks/useProfile.test.ts __tests__/lib/profile.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts __tests__/components/EditSheet.test.tsx __tests__/components/ProfileScreen.test.tsx __tests__/components/OnboardingFlow.test.tsx __tests__/components/OnboardingWelcome.test.tsx __tests__/hooks/useAccess.test.ts __tests__/api/onboarding-payload.test.ts __tests__/contracts/city.test.ts && cd apps/api && source .venv/bin/activate && python -m pytest tests/test_profile_endpoints.py -q && cd ../.. && npm run contracts:check && pnpm exec tsc --noEmit && git diff --check
```

Results:

- Vitest: 12 test files passed, 92 tests passed.
- Backend pytest: 18 tests passed in 1.11 seconds.
- `npm run contracts:check`: passed; generated contracts remained unchanged.
- `pnpm exec tsc --noEmit`: passed with no output.
- `git diff --check`: passed with no output.
- Runtime demo/mock import check: no product runtime imports found; the sole text match is an existing comment in `lib/profile-meta.ts`.

### Remaining Concerns

- None for the review findings. Vitest still emits the repository's existing Vite CommonJS deprecation warning.
