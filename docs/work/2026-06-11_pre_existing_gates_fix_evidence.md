# Evidence Report: pre-existing gates fix

Date: 2026-06-11
Reviewed/Fixed commit: based on `c71aa5f` (origin/main)
Branch: `fix/pre-existing-gates`

## 1. Initial Failing Tests & Typecheck Errors

### A. Backend Pytest Errors
1. `test_solarsage_client` failed because the Pydantic schema for `SolarSagePlanetPosition` and `SolarSageTransitPlanet` did not include the `latitude` field returned by the sidecar.
2. `test_solarsage_client` also failed because the Pydantic schema `SolarSageHouseCusp` declared the cusp field as `longitude: float` instead of `cusp: float`, whereas the sidecar response maps to `cusp`.
3. `test_llm_fallback` failed with `TypeError: object MagicMock can't be used in 'await' expression` because `mock_solarsage_client` in `integration/conftest.py` only mocked `"app.services.today_service.get_solarsage_client"`, leaving other services (like `natal_context_service` and `natal_report_service`) calling the unmocked client.
4. `test_alembic_roundtrip` failed because:
   - It hardcoded the path `.venv/bin/alembic`, which is not portable across environments.
   - The Alembic migration `0016` attempted to drop a unique constraint using `op.drop_constraint(...)`, which raises `NotImplementedError` in SQLite.

### B. TypeScript Compiler Errors (`npx pnpm typecheck`)
- `edit-sheet.tsx` failed because `CityPicker` requires `City | null` but it was given a string.
- `week-strip.tsx` failed because `getDayStatus` was asynchronous (returned `Promise<DayStatus>`) while the component expected it to be synchronous.
- Reducer tests (`chatReducer.test.ts`) failed because the reducer was rewritten in Wave 2.4/onboarding, but the tests were still checking for the old action types.
- Missing imports, type casting, and implicitly typed parameters in various components and tests.

---

## 2. Fixes Applied

### Work package A: `test_solarsage_client`
- Added `latitude: float | None = None` to `SolarSagePlanetPosition` and `SolarSageTransitPlanet` in `apps/api/app/schemas/natal.py`.
- Fixed `SolarSageHouseCusp` to map the `cusp` sidecar field to `longitude` using `longitude: float = Field(..., alias="cusp")`.
- Updated `apps/api/tests/test_solarsage_client.py` mock responses and assertions to expect correct schemas and camelCase keys. Added `test_validation_errors`.

### Work package B: `test_llm_fallback`
- Updated `apps/api/tests/integration/conftest.py` to globally patch `app.clients.solarsage_client.get_solarsage_client` for all namespaces. Added `sign` to mock house structures.
- Isolated `test_llm_fallback.py` from the sidecar by patching both context service and today service client factory namespaces in the test body.

### Work package C: `test_alembic_roundtrip`
- Removed hardcoded alembic binary path. Used `sys.executable` to run Alembic module.
- Modified migration `0016_add_natal_cache_and_reports.py` to use `op.batch_alter_table` for SQLite compatibility during constraint dropping/adding.

### Work package D: TypeScript Errors
- **`components/profile/edit-sheet.tsx`**: Updated `CityEditor` to manage state as `City | null` instead of `string`, and formatted using `formatCity` on save.
- **`components/today/week-strip.tsx`**: Refactored to fetch day statuses asynchronously via `useEffect` and state, preventing promise mismatch.
- **`components/readings/natal/`**: Replaced all imports from `@/lib/readings/natal-schema` with `@/lib/contracts/natal` and added explicit mapping parameter types to eliminate implicit `any` errors.
- **`__tests__/lib/chatReducer.test.ts`**: Replaced outdated reducer tests with the correct test suite from `reducers.test.ts`.
- **Other files**: Added imports for `vi` in `storage-keys.test.ts`, typed mock objects in `horary-question-card.test.tsx`, cast `process.env.NODE_ENV` assignments, and cast WebApp object properties.

---

## 3. Files Modified

- `apps/api/app/schemas/natal.py`
- `apps/api/tests/test_solarsage_client.py`
- `apps/api/tests/test_llm_fallback.py`
- `apps/api/tests/integration/conftest.py`
- `apps/api/tests/test_alembic_roundtrip.py`
- `apps/api/alembic/versions/0016_add_natal_cache_and_reports.py`
- `components/profile/edit-sheet.tsx`
- `components/today/week-strip.tsx`
- `components/chat/chat-screen.tsx`
- `components/readings/natal/block-renderer.tsx`
- `components/readings/natal/highlights-strip.tsx`
- `components/readings/natal/natal-section.tsx`
- `components/readings/natal/natal-toc.tsx`
- `components/readings/natal/widgets/planets-widget.tsx`
- `components/readings/natal/widgets/spheres-widget.tsx`
- `hooks/use-telegram-auth.ts`
- `hooks/use-telegram-user.ts`
- `lib/log/index.ts`
- `__tests__/components/TabBar.test.tsx`
- `__tests__/contracts/natal.test.ts`
- `__tests__/hooks/useTelegramAuth.test.ts`
- `__tests__/horary/horary-question-card.test.tsx`
- `__tests__/lib/chatReducer.test.ts`
- `__tests__/lib/storage-keys.test.ts`

---

## 4. Execution Commands & Verification Status

1. **TypeScript Typecheck**:
   ```bash
   npx pnpm typecheck
   ```
   *Status*: **PASSED** (0 compile errors).

2. **Frontend Tests**:
   ```bash
   npx vitest run
   ```
   *Status*: **PASSED** (745 passed, 1 skipped).

3. **Backend API Tests**:
   ```bash
   .venv/bin/pytest
   ```
   *Status*: **PASSED** (455 passed, 2 skipped).

4. **Sidecar Tests**:
   ```bash
   PYTHONPATH=. venv/bin/pytest
   ```
   *Status*: **PASSED** (20 passed).

5. **Specific Target Tests**:
   - `npx vitest run __tests__/api/natal-report.test.ts` — **PASSED** (24 tests)
   - `npx vitest run __tests__/natal/natal-component-states.test.tsx` — **PASSED** (4 tests, 1 skipped)
   - `.venv/bin/pytest tests/test_natal_golden_zhanna.py` — **PASSED** (61 tests)

---

## 5. Conclusion

All pre-existing gates have been successfully repaired:
- Sidecar schema drift for `latitude` is resolved in `natal.py`.
- `test_llm_fallback` is hermetic and doesn't hit sidecar.
- Alembic migration test does not depend on `.venv/bin/alembic` and handles constraint alteration under SQLite correctly.
- Strict `pnpm typecheck` compiles clean.
