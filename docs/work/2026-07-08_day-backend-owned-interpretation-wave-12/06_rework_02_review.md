# Wave 12 Rework 02 Architect Review

Date: 2026-07-08
Status: REWORK REQUIRED
Reviewed commit: `f3fc46b`
Previous review: `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/04_rework_01_review.md`

## Findings

### Critical: runtime still contains test/mock-aware LLM key filtering

`apps/api/app/services/today_interpretation_service.py:350-360` introduces `is_real_key()` and rejects configured keys when the secret contains `mock` or `test`.

This is still test-specific behavior in product code, just hidden behind key-string heuristics. It can also disable the real LLM if a legitimate secret contains those substrings. The product decision must be explicit: a non-empty configured key means the LLM path is enabled. Tests must patch keys and LLM methods explicitly.

### Important: old forecast-copy strings still live in test data

`apps/api/tests/test_today_concrete_advice.py:85`, `:145`, and `:174` still contain `Сократи траты...`; in two cases it is used as accepted fake LLM output.

`__tests__/components/TodayScreen.test.tsx:148` still uses `без взлётов — занимайся рутиной` as default fixture copy.

`e2e/mock-visual/day.spec.ts:277-279` contains old exact product strings in negative assertions. These are not runtime UI copy, but they make the static gate fail and keep the old oracle copy alive in the repo.

Wave 12's goal is to remove old mock-preview advice text from active code and fixtures. Use neutral sentinel strings or unavailable text instead.

### Note: Wave 11 artifact final state is clean

`git diff --name-only 50f6150..HEAD -- docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03` returned no output. The final cumulative state no longer changes Wave 11 artifacts. The Rework 02 commit itself contains the revert because `e0e1832` had introduced the churn; that is acceptable for final state.

## Verification Run

Passed:

```bash
rg -n "hasattr\(llm_service\.generate_.*mock|assert_called|is_mocked" apps/api/app -S
# no output

cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
# 4 passed

npx vitest run __tests__/components/TodayScreen.test.tsx
# 14 passed

pnpm contracts:check
# regenerated contracts; no diff

git diff --check 50f6150..HEAD
# no output
```

Failed:

```bash
rg -n "mock|test" apps/api/app/services/today_interpretation_service.py apps/api/app/services/llm_service.py -S
# today_interpretation_service.py filters configured keys by "mock"/"test"

rg -n "Сократи траты|Дела идут со скрипом|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|особое влияние дня|Фокусируйся на текущих|Приобретай только|Взвешивай все последствия" apps/api/app apps/api/tests __tests__ e2e components lib -S
# matches in backend tests, TodayScreen test fixture, and e2e negative assertions
```

## Required Outcome

One more narrow rework. Do not change the architecture again; remove the runtime key heuristic and clean stale test copy.
