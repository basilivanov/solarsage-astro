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
*   **`components/today/concrete-day-advice.tsx`**: Renders exact backend-owned `concreteAdvice` block. Removed local templates and verdict logic. Added semantic `iconName` to emoji `ICON_MAP`.
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
    *   `cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py` (4 passed)
    *   `cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py` (16 passed)
*   **Vitest (unit)**:
    *   `npx vitest run TodayScreen.test.tsx` (14 passed)
    *   `npx vitest run sphere-labels.test.ts` (8 passed)
*   **Playwright (E2E)**:
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts` (8 passed)
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/today.spec.ts` (8 passed)

---

## 6. Static Source Gate Results

*   `rg -n "SPHERE_ADVICE_TEXTS|buildConcreteAdviceRows|planetDescription\(|PLANET_THEME|Дела идут со скрипом|Сократи траты|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|Интерпретация для" components lib app apps/api/app -S` -> **No matches found.**
*   `rg -n "pytest.*sys\.modules|sys\.argv|is_test_env" apps/api/app -S` -> **No matches found.**
*   All old frontend forecast templates and text builders are 100% removed.

---

## 7. Rework 02 Fixes (2026-07-08)

*   **Removed mock checks**: Deleted all mock introspection (`is_mocked`, `is_chart_mocked`, etc.) from `today_interpretation_service.py`. Product code only runs the LLM when real keys are configured.
*   **Factual Day Summary Card**: Replaced hardcoded action advice in summary facts with factual, non-forecast summaries. Omitted the forecast summary from top flag facts, using `"транзитный аспект"` instead.
*   **Cleaned LLM Prompt**: Removed hardcoded product templates from prompt examples in `llm_service.py`.
*   **Semantic Icon Names Fallback**: Used a neutral `"•"` fallback in `concrete-day-advice.tsx` if `ICON_MAP` does not resolve the semantic icon name, completely preventing raw text leaks.
*   **Strict Allowed Evidence Planets/Aspects Validator**: Derives the allowed planets/aspects/houses in `validate_row_text()` strictly from `row.evidence` only (no static planet maps). Mentioning any planet/aspect/house not in the evidence rejects the row.
*   **Mocked LLM explicitly in tests**: Set the API keys to empty in `conftest.py` so cache/endpoints tests verify the true no-LLM fallback path (`"Рекомендация временно недоступна."`).
*   **Updated E2E mock fixtures**: Restored contract/prompt version numbers to `3` and `2`, used semantic icon names, and filled text fields with backend-owned sentinel strings (e.g. `СЕНТИНЕЛ ОТНОШЕНИЯ`).
*   **Cleaned up visual artifacts**: Restored the `artifacts/pixel-rework-03` directory to its state before commit `e0e1832`.
