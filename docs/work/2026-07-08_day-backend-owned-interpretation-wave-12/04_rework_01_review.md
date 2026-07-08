# Wave 12 Rework 01 Architect Review

Date: 2026-07-08
Status: REWORK REQUIRED
Reviewed commit: `e0e1832`
Previous review: `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/02_arch_review.md`

## Findings

### Critical: product service still branches on test/mocking details

`apps/api/app/services/today_interpretation_service.py:341-346` and `:495-496` inspect whether `LLMService` methods have mock/assert attributes. This removes the pytest/sys.argv branch, but keeps test-aware logic inside product code.

Product code must not know whether a dependency is mocked. Tests should explicitly configure the LLM path using a fake key plus patched/fake LLM, or exercise the no-key path with keys disabled.

### Critical: global autouse LLM mock masks the real fallback path

`apps/api/tests/conftest.py:43-80` replaces LLM generation for every backend test. Because the product service then detects the mock, normal endpoint/cache tests never exercise the actual no-key/no-LLM fallback. This directly contradicts the rework requirement to prove unavailable fallback behavior.

The autouse mock also reintroduces product-style advice strings, including `Сократи траты`, into shared test setup.

### Critical: LLM validator allows unsupported astrology through static sphere defaults

`apps/api/app/services/today_interpretation_service.py:145-149` adds allowed planets from `PLANET_TO_SPHERES_MAP` even when those planets are not present in row evidence. That means the validator may accept LLM text mentioning Venus/Jupiter/Mars/etc. solely because the sphere normally maps to that planet, not because the calculation produced that fact.

The allowed token set must be derived from actual row evidence only. Static product sphere defaults may drive UI ordering or deterministic verdict selection, but not fact validation.

### Important: runtime day summary still contains a forbidden hardcoded phrase

`apps/api/app/services/today_interpretation_service.py:467` still emits `особое влияние дня`. This exact phrase was listed in rework as copy to remove. Use a factual summary derived from the signal, or omit `summary`.

### Important: LLM prompt still contains full recommendation examples

`apps/api/app/services/llm_service.py:1024-1038` still includes a complete 12-row JSON with ready-made recommendation copy. The old exact templates were replaced, but the prompt still seeds the model with local forecast text. Rework asked for schema-only or neutral placeholders.

### Important: mock visual fixture still uses old contract data and old product copy

`e2e/mock-visual/fixtures/day-2026-07-05.ts:28-35` still has `contractVersion: 1`, `promptVersion: 1`, `contentVersion: 1`.

`e2e/mock-visual/fixtures/day-2026-07-05.ts:193-204` still uses emoji `iconName` values and old local advice text.

`e2e/mock-visual/fixtures/day-2026-07-05.ts:208-214` still contains `день на твоей стороне`, `подводи итоги`, and `особое влияние дня`.

This makes visual E2E tests preserve stale behavior instead of the backend-owned contract.

### Important: frontend can still render raw semantic icon names

`components/today/concrete-day-advice.tsx:130` falls back to `row.iconName` when `ICON_MAP` misses a key. That still exposes internal semantic names in the UI. Fallback should be a neutral icon, not raw backend data.

### Important: component tests still use stale copy and emoji icon fixtures

`__tests__/components/TodayScreen.test.tsx:353`, `:359`, and other fixture blocks still use emoji `iconName` and old local forecast text. These tests should use semantic icon names and sentinel backend-owned text so regressions are visible.

### Important: rework commit contains unrelated Wave 11 visual artifact churn

Commit `e0e1832` modifies files under:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/`

Wave 12 should not rewrite previous-wave oracle/candidate PNGs or summaries. Keep the commit scoped.

## Verification Run

Passed:

```bash
git diff --check 50f6150..HEAD
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
# 2 passed
npx vitest run __tests__/components/TodayScreen.test.tsx
# 14 passed
pnpm contracts:check
# regenerated contracts; no diff
```

Failed architectural/static checks:

```bash
rg -n "hasattr\(llm_service\.generate_.*mock|assert_called|is_mocked" apps/api/app -S
# matches in today_interpretation_service.py

rg -n "Сократи траты|Дела идут со скрипом|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|особое влияние дня|Фокусируйся на текущих|Приобретай только|Взвешивай все последствия" apps/api/app apps/api/tests __tests__ e2e components lib -S
# matches in runtime service, backend tests, frontend tests, and mock visual fixtures
```

## Required Outcome

Rework again. The goal is not just passing unit tests: the codebase must enforce the backend-owned interpretation contract and tests/fixtures must stop carrying the old mock-preview copy as hidden truth.
