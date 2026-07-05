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

- `useAccess().setState` is now a compatibility no-op because real access is backend-owned and no backend mutation endpoint exists for dev switching.
