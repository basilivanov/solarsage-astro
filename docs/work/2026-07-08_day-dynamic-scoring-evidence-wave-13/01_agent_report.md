# Wave 13 Day Dynamic Scoring, Evidence, and Access Clarity Report

**Date**: 2026-07-08
**Branch**: `main`
**Push/Deploy Status**: `NOT_ATTEMPTED`

---

## 1. Changed Files

*   **`apps/api/app/schemas/today.py`**:
    *   Updated `ConcreteAdviceEvidence` to include `house: int | None = None` and `sign: str | None = None` for detailed transit-based evidence.
*   **`apps/api/app/services/normalization_service.py`**:
    *   Added normalized `planet_in_house` signals for each transit planet (prefixed with `"Transit_"`) in `normalize_day()`.
*   **`apps/api/app/services/today_service.py`**:
    *   Filtered `day_signals` to contain only transit/lunar/event signals.
    *   Scoped `score_day`, `_build_planet_influences`, and `TodayInterpretationService` to use `day_signals` instead of full signals (containing static natal signals).
    *   Bumped `TODAY_CONTENT_VERSION` from `3` to `4` for cache invalidation.
*   **`apps/api/app/services/today_interpretation_service.py`**:
    *   Cleaned out all mock/assert key-heuristic checks. Product code only runs LLM based on explicit non-empty configuration checks.
    *   Implemented dynamic evidence collection: for each canonical sphere, row evidence now contains the top contributing day signals (aspect or planet-in-house).
    *   Factual day summary facts: replaced hardcoded summaries with factual descriptors (e.g. `"убывающая фаза"`). Scoped the `top_flag` fact to the top daily aspect signal from `top_signals`, formatted in Russian (e.g. `"Луна оппозиция Плутон"`), with the aspect description `"напряжённый аспект"` or `"поддерживающий аспект"`.
    *   Cleaned out raw `Transit_` / `Natal_` prefixes from all visible summary titles using `strip_prefix()`.
    *   If LLM is unavailable/fails, row texts remain `"Рекомендация временно недоступна."` and no templates are used.
*   **`apps/api/app/services/access_service.py`**:
    *   Added `+ 1` to `can_access_day()` days left calculation to align with `get_summary()` inclusive access logic.
*   **`lib/contracts/today.ts`**:
    *   Added `house` and `sign` to `ConcreteAdviceEvidenceSchema`.
*   **`apps/api/tests/test_today_concrete_advice.py`**:
    *   Removed old forecast-copy template strings and replaced them with sentinel Russian strings.
    *   Added `test_today_interpretation_service_no_key_fallback` verifying all rows stay `"Рекомендация временно недоступна."` when no keys are configured.
    *   Added `test_today_interpretation_service_allowed_evidence_planets` verifying that planet/aspect mentions in LLM text are strictly validated against row evidence.
    *   Added `test_today_interpretation_service_test_key_enables_llm` verifying that a fake key containing `"test"`, e.g. `"test-key"`, still enables the LLM path in tests.
*   **`apps/api/tests/test_day_endpoints.py`**:
    *   Updated `TODAY_CONTENT_VERSION` assertion to `4`.
*   **`__tests__/components/TodayScreen.test.tsx`**:
    *   Updated TodayScreen mock fixtures and tests to use semantic `iconName`s and sentinel backend-owned texts instead of stale forecast templates.
*   **`e2e/mock-visual/fixtures/day-2026-07-05.ts`**:
    *   Updated contract/prompt/content versions to `3`, `2`, `3`.
    *   Replaced emoji `iconName` values with semantic names and filled text fields with sentinel strings.
*   **`e2e/mock-visual/day.spec.ts`**:
    *   Removed exact old-copy literals in negative assertions.

---

## 2. Dynamic Scoring Evidence for `basil_ivanov` (2026-07-08)

### Before (Cached/Static)
*   **Access state**: 3 days left (July 8, 9, 10, 11).
*   **Concrete Advice**: Mixed with unavailable placeholder rows (`"Нет отдельного сигнала на эту сферу."`).
*   **Day Summary**:
    *   `top_planet.summary = "особая тема дня"`
    *   `top_flag.title = "Аспект дня"`
    *   `top_flag.summary = "особое влияние дня"`
    *   `lunar_phase.summary = "подводи итоги"`
*   **Sphere scores**: Static natal baseline dominated.

### After (Dynamic/V4 Recalculation)
*   **Access state**: `full` access with **4** inclusive days left (July 8, 9, 10, 11).
*   **Day Summary**:
    *   `top_planet`: icon `Pluto`, title `"Влияние Плутон"`, summary `None` (factual/omitted).
    *   `lunar_phase`: title `"Убывающая Луна 46%"`, summary `"убывающая фаза"`.
    *   `top_flag`: title `"Луна оппозиция Плутон"`, summary `"напряжённый аспект"` (factual daily aspect).
*   **Concrete Advice**:
    *   Exactly 12 rows are populated with valid, Russian recommendations.
    *   Row evidence contains real daily transit signals: `Transit_Sun` in 1st house, `Transit_Mars` in 12th house, aspect `Transit_Sun` trine `Mercury`.
*   **Score Dynamics**: 8/12 spheres changed score across days between 2026-07-08 and 2026-07-11, proving the scoring is genuinely day-dynamic.

---

## 3. Access State for `basil_ivanov`
*   **2026-07-08**: `full` access, `referral_days_left` is **4** (inclusive of today: July 8, 9, 10, 11).
*   **2026-07-11**: `full` access, `referral_days_left` is **1** (inclusive of today: July 11).
*   **2026-07-12**: `locked` (outside access window, ending 2026-07-11).

---

## 4. Verification Commands & Results

*   **Pytest (backend)**:
    *   `cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py` (5 passed)
    *   `cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py` (16 passed)
    *   `cd apps/api && .venv/bin/pytest tests/test_access_service.py` (3 passed)
*   **Vitest (unit)**:
    *   `npx vitest run TodayScreen.test.tsx` (14 passed)
    *   `npx vitest run sphere-labels.test.ts` (8 passed)
*   **Playwright (E2E)**:
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts` (8 passed)
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/today.spec.ts` (8 passed)
