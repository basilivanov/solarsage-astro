# Wave 12 Rework 03 TZ — Remove Runtime Key Heuristic and Stale Test Copy

Date: 2026-07-08
Status: ready for coder
Owner: architect
Coder model: Flash 3.5
Branch: `main`
Reviewed commit: `f3fc46b`
Review: `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/06_rework_02_review.md`
Report path: append to `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md`

## Goal

Finish the last Wave 12 blockers. This is a narrow cleanup:

- product code must not classify secrets by words like `mock` or `test`;
- old mock-preview forecast strings must not appear in runtime code, fixtures, or tests scanned by the gate.

Do not push.

## Required Fixes

### 1. Remove `is_real_key()` and key-string heuristics

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Required:

- Delete `is_real_key()`.
- Delete checks like `"mock" not in k` and `"test" not in k`.
- Use explicit non-empty configuration only:

```python
has_llm_keys = any(
    bool((key or "").strip())
    for key in (
        settings.openrouter_api_key,
        settings.anthropic_api_key,
        getattr(settings, "deepseek_api_key", ""),
    )
)
```

or equivalent.

Add/update a backend test proving a fake key containing `test`, e.g. `test-key`, still enables the patched LLM path. The test should assert `generate_concrete_advice` was called.

### 2. Remove stale forecast-copy literals from tests and fixtures

Modify:

```text
apps/api/tests/test_today_concrete_advice.py
__tests__/components/TodayScreen.test.tsx
e2e/mock-visual/day.spec.ts
```

Required:

- Replace valid fake LLM outputs like `Сократи траты...` with neutral/sentinel Russian text that contains no planet/aspect/house facts.
- Replace invalid prefix test strings with neutral text containing `Transit_` / `Natal_`, not old advice copy.
- Replace `без взлётов — занимайся рутиной` in `TodayScreen.test.tsx` with `Сводка временно недоступна.` or a sentinel string.
- Remove exact old-copy literals from `e2e/mock-visual/day.spec.ts`; rely on the static gate rather than embedding the old strings in Playwright assertions.

Do not weaken the frontend assertions that sentinel backend text renders verbatim.

### 3. Keep artifact final-state cleanup

No extra work required if this stays true:

```bash
git diff --name-only 50f6150..HEAD -- docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03
```

Expected: no output.

## Required Gates

Run and report exact results:

```bash
rg -n "is_real_key|\"mock\" not in|\"test\" not in|hasattr\(llm_service\.generate_.*mock|assert_called|is_mocked" apps/api/app -S
```

Expected: no output.

```bash
rg -n "Сократи траты|Дела идут со скрипом|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|особое влияние дня|Фокусируйся на текущих|Приобретай только|Взвешивай все последствия" apps/api/app apps/api/tests __tests__ e2e components lib -S
```

Expected: no output.

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py -q
npx vitest run __tests__/components/TodayScreen.test.tsx
pnpm contracts:check
git diff --check 50f6150..HEAD
git diff --name-only 50f6150..HEAD -- docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03
```

If you touch frontend build-affecting files beyond tests, also run:

```bash
pnpm build
```

## Commit Requirements

Create a new rework commit on `main`.

Do not push.

Do not commit unrelated untracked paths:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- `test-results/`
- `playwright-report/`

## Required Callback

At the very end, run this callback from the repo root:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 12 Rework 03 ready for architect review. Report: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md. Review: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/06_rework_02_review.md. Rework TZ: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/07_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

Replace `<commit_sha>` with the actual final commit SHA.
