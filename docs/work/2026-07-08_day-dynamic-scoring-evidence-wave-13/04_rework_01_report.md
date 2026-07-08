# Wave 13 Rework 01 Report

## Changed files

- `scripts/generate-telegram-test-initdata.py`
- `e2e/fixtures.ts`
- `e2e/auth-helper.ts`
- `apps/api/tests/test_telegram_hmac.py`
- `apps/api/tests/test_pipeline_integration.py`
- `apps/api/app/services/day_scoring_signals.py`
- `apps/api/app/services/today_service.py`
- `apps/api/app/services/calendar_service.py`
- `apps/api/app/services/today_interpretation_service.py`
- `apps/api/tests/test_today_concrete_advice.py`
- `apps/api/tests/test_calendar_endpoints.py`
- `apps/api/tests/test_day_endpoints.py`
- `__tests__/contracts/today.test.ts`
- `__tests__/lib/adapt-payload.test.ts`
- `__tests__/components/TodayScreen.test.tsx`
- `__tests__/hooks/useDay.test.ts`
- `lib/mocks/today.ts`
- `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/04_rework_01_report.md`

## Root causes fixed

1. **Default Telegram test auth used Basil's real account.**
   - Default generator identity is now synthetic (`999999999` / `synthetic_test_user`).
   - Playwright fixture default now derives unique synthetic Telegram ids.
   - `e2e/auth-helper.ts` uses explicit env ids only when provided, otherwise safe synthetic defaults.
   - Remote pipeline smoke tests are env-gated and no longer contain hardcoded Basil credentials or dev URL in the executable path.
   - Added a regression proving default generated initData does not contain `833478509` or `testuser`.

2. **ConcreteAdvice verdict and primary evidence could diverge.**
   - Removed the independent mutable `planet_aspect_verdicts` overwrite pattern.
   - Direct-score rows now choose primary evidence compatible with score direction; otherwise they fall back to score/house evidence instead of contradictory aspect evidence.
   - No-direct-score rows can become non-neutral only from selected aspect evidence with matching polarity.
   - Generic planet influence no longer produces `good/caution/avoid` for no-direct-score rows.
   - Added contradiction regressions for `good` + tense primary evidence and `caution/avoid` + soft primary evidence.

3. **Calendar status could diverge from `/day` and stale semantic cache could win.**
   - Added shared `filter_day_scored_signals()` helper and used it from both `TodayService` and `CalendarService`.
   - Calendar now checks versioned `TodayPayloadCache` first and only accepts `SemanticLayerCache` entries wrapped with matching `profile_hash` and `content_version`.
   - Added regression where full mixed natal+day signals score differently from filtered day signals; calendar matches filtered `/day` scoring.
   - Added regression that unversioned semantic cache is ignored.

4. **Stale v4 payloads could still serve old semantics.**
   - `TODAY_CONTENT_VERSION` is now `5`.
   - Tests that assert the content version were updated.
   - Contract generation was run; generated OpenAPI/TS contract types stayed structurally unchanged because `contentVersion` is typed as `number`.
   - Frontend test/mock payload fixtures were aligned with required `daySummary` and `concreteAdvice` contract fields.

## Verification outputs

### Required backend pytest

Command:

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py tests/test_day_endpoints.py tests/test_access_service.py tests/test_calendar_endpoints.py -q
```

Result:

```text
29 passed, 1 warning in 1.36s
```

### Targeted initData default safety

Command:

```bash
cd apps/api && .venv/bin/pytest tests/test_telegram_hmac.py::test_generate_initdata_default_safety -q
```

Result:

```text
1 passed in 0.04s
```

### Required frontend vitest

Command:

```bash
npx vitest run TodayScreen.test.tsx sphere-labels.test.ts
```

Result:

```text
Test Files  2 passed (2)
Tests       22 passed (22)
Duration    2.07s
```

### Diagnostics / typecheck / build

Commands and results:

```bash
cd apps/api && .venv/bin/python -m compileall app -q
# exit 0, no output

npm run typecheck
# tsc --noEmit passed

npm run build
# Next.js production build compiled successfully; 18/18 static pages generated
```

### Production-style Basil verification

Command: standalone Python script using `SessionLocal`, `AccessService`, `TodayService`, `CalendarService`, `NormalizationService`, `ScoringService`, and `filter_day_scored_signals()` for `tg_user_id=833478509`.

Result summary:

```json
{
  "content_version_constant": 5,
  "db_username_before_command": "basil_ivanov",
  "db_username_after_command": "basil_ivanov",
  "username_repair_rows": 0,
  "access": {
    "2026-07-08": {"state": "full", "reason": "active_referral_days", "referralDaysLeft": 4, "accessUntil": "2026-07-11"},
    "2026-07-11": {"state": "full", "reason": "active_referral_days", "referralDaysLeft": 1, "accessUntil": "2026-07-11"},
    "2026-07-12": {"state": "locked", "reason": "outside_access_window", "accessUntil": "2026-07-11"}
  },
  "day": {
    "date": "2026-07-08",
    "cached": false,
    "content_version": 5,
    "day_status": "supportive",
    "contradictions": []
  },
  "calendar_vs_filtered_scoring": {
    "calendar_status": "supportive",
    "filtered_day_status": "supportive",
    "full_signal_count": 77,
    "filtered_day_signal_count": 47,
    "matches": true
  }
}
```

Concrete advice primary-evidence polarity was checked for all 12 rows; contradiction list is empty.

## Production user metadata result

- `users.tg_user_id=833478509` existed.
- `tg_username` was already `basil_ivanov` when checked.
- Conditional repair query (`WHERE tg_user_id=833478509 AND tg_username='testuser'`) updated `0` rows.
- Birth/current-city/profile/access data were not mutated.

## Commit / push / deploy status

- Branch: `main`
- Implementation commit present before final report/typecheck follow-up: `70cc05f`
- Final HEAD is reported in the callback and final assistant response after the last commit is created.
- Push: `NOT_ATTEMPTED`
- Deploy: `NOT_ATTEMPTED`
