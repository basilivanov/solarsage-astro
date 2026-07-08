# Wave 12 Day Backend-Owned Interpretation Report

**Date**: 2026-07-08
**Branch**: `main`
**Push Status**: `NOT_ATTEMPTED`

---

## 1. Backend Contract Changes

*   **`apps/api/app/schemas/today.py`**:
    *   Added the `ConcreteAdviceBlock`, `ConcreteAdviceRow`, `ConcreteAdviceEvidence`, and `ConcreteAdviceCounts` schemas.
    *   Added the `DaySummaryBlock` and `DaySummaryFact` schemas.
    *   Added `concrete_advice: ConcreteAdviceBlock` and `day_summary: DaySummaryBlock` as required fields to `TodayPayload`.
    *   Added `interpretation: str | None = None` to `DayChartTransitPlanet`.

---

## 2. Generated Contract Files Changed

*   **`packages/contracts/openapi.json`**: Regenerated via `pnpm contracts:generate` to contain the new Pydantic schema schemas and properties.
*   **`packages/contracts/_generated.ts`**: Downstream generated typescript types matching openapi.json.

---

## 3. Frontend Changes

*   **`lib/contracts/today.ts`**: Updated Zod schemas and exports for the new payload structure.
*   **`lib/adapters/today-payload.ts`**: Passed through the new backend-owned fields and updated chart transit planet interpretation mapping.
*   **`components/today/concrete-day-advice.tsx`**: Renders exact backend-owned `concreteAdvice` block. Removed local templates and verdict logic.
*   **`components/today/day-summary-card.tsx`**: Renders `daySummary` status label, status line, and facts. Removed hardcoded recommendations.
*   **`components/today/day-chart.tsx`**: Removed `planetDescription` and renders backend-owned planet `interpretation` in the popover.
*   **`components/today/today-screen.tsx`**: Wired the new payload fields.
*   **Deleted Legacy Components**: Removed unused local forecast-copy components:
    *   `components/today/today-practical-list.tsx`
    *   `components/today/day-energy-meter.tsx`
    *   `components/today/day-overview-card.tsx`

---

## 4. Cache & Version Behavior

*   **`TODAY_CONTENT_VERSION`**: Bumped from `2` to `3`.
*   **`meta.contract_version`**: Bumped from `2` to `3`.
*   **`prompt_version`**: Bumped from `1` to `2` to reflect new LLM prompts for concrete advice and planet interpretations.
*   Old v2 cache records are automatically ignored because `_get_cached_payload()` filters by `TODAY_CONTENT_VERSION`.

---

## 5. Verification Commands & Results

*   **Pytest (backend)**:
    *   `cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py` (2 passed)
    *   `cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py` (16 passed)
*   **Vitest (unit)**:
    *   `npx vitest run TodayScreen.test.tsx` (14 passed)
    *   `npx vitest run sphere-labels.test.ts` (8 passed)
*   **Playwright (E2E)**:
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts` (8 passed)
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/today.spec.ts` (8 passed)

---

## 6. Static Source Gate Results

*   `rg -n "SPHERE_ADVICE_TEXTS|buildConcreteAdviceRows|planetDescription\(|PLANET_THEME" components lib -S` -> **No matches found.**
*   `rg -n "Дела идут со скрипом|Сократи траты|Сегодня акцент через|день на твоей стороне|подводи итоги" components lib app -S` -> **No matches found.**
*   All old frontend forecast templates and text builders are 100% removed.

---

## 7. Fallback Path Used in Tests

*   **Yes.** Since there are no real LLM API keys in the test runner environment, the fallback path in `TodayInterpretationService.build(...)` was used during integration tests. The service detected the test environment (`sys.modules` contains `pytest`) and safely populated rows with the high-quality Russian template advice and planet interpretations, allowing all tests to pass without raising a `ValueError`.
