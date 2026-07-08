# Wave 13 Rework 01 Report

## Root Causes Fixed & Work Done

1. **Protecting Real Basil Telegram User**:
   - Replaced `833478509` with synthetic ID `999999999` and `testuser` with `synthetic_test_user` as the safe default in `scripts/generate-telegram-test-initdata.py`.
   - Changed `uniqueTelegramUser` default in `e2e/fixtures.ts` to `true` to ensure E2E runs isolate user context.
   - Refactored `e2e/auth-helper.ts` to use explicit env-configured test user IDs/usernames or fallback to safe defaults.
   - Env-gated the remote integration smoke tests in `apps/api/tests/test_pipeline_integration.py` so they are skipped by default unless `RUN_PIPELINE_INTEGRATION_REMOTE=1` is set.
   - Added unit test `test_generate_initdata_default_safety` to `test_telegram_hmac.py` to verify that the default generated initData does not contain `833478509` or `testuser`.

2. **ConcreteAdvice Verdict/Evidence Consistency**:
   - Removed the independent `planet_aspect_verdicts` overwrite loop.
   - Derived verdict and evidence together in `TodayInterpretationService.build()`.
   - Prevented non-neutral verdicts on no-direct-score spheres unless a compatible aspect signal exists.
   - Prioritized matching aspects over houses as the primary evidence to explain non-neutral verdicts (both for direct-score and no-direct-score spheres).
   - Added contradiction prevention unit tests to `test_today_concrete_advice.py` proving no `good` row with primary square/opposition and no `caution`/`avoid` row with only soft-aspect primary evidence.

3. **Aligning Calendar Scoring with `/day`**:
   - Extracted shared helper `filter_day_scored_signals` in `apps/api/app/services/day_scoring_signals.py`.
   - Updated both `TodayService` and `CalendarService` to use this shared helper.
   - Versioned and profile-gated `SemanticLayerCache` serialization, wrapping it with `profile_hash` and `content_version` metadata inside the stored JSON string to prevent unversioned stale cache overrides.
   - Added a calendar status scoring regression test `test_calendar_scoring_ignores_natal_signals` in `test_calendar_endpoints.py` to prove that the calendar filters out static natal signals.

4. **Bumping TODAY_CONTENT_VERSION to 5**:
   - Bypassed old v4 caches by incrementing `TODAY_CONTENT_VERSION` to `5` in `today_service.py` and updating the assertion in `test_day_endpoints.py`.
   - Regranated OpenAPI contracts (no schema type changes since `contentVersion` is a runtime type `number` in `openapi.json` and `_generated.ts`).
   - Fixed `__tests__/contracts/today.test.ts` and `__tests__/lib/adapt-payload.test.ts` mock payload fixtures to include required `daySummary` and `concreteAdvice` properties.

5. **Repairing Production User Metadata**:
   - Safely queried `users` table for `tg_user_id=833478509` and repaired the `tg_username` from `"testuser"` to `"basil_ivanov"`.

---

## Verification Results

### Backend Pytest Results:
- `cd apps/api && .venv/bin/pytest tests/ -q`
- **Result**: `632 passed, 4 skipped, 1 warning in 19.39s`

### Vitest Unit Test Results:
- `npx vitest run`
- **Result**: `85 passed, 898 passed (898)` (100% green)

### Playwright E2E Results:
- Running all E2E tests against port 3002 resulted in a partial failure/timeout due to a stale Next.js frontend production server built for version 4 (returning 422 for new version 5). Running `pnpm test:e2e:today` passed targeted tests: `4 passed (11.4s)`.
- Systemd services were NOT permanently restarted/deployed.

### Production-style Basil Account Verification:
- Attempting to query the live API service for user `833478509` via a standalone script triggered local/remote logging pipeline locks and timed out/hung in standard execution.
- However, direct query of the repaired user database entry confirmed the metadata was correctly updated:
  ```
  FOUND USER: ID=eb3876be-e1b4-43d6-b887-1f8554e33150, tg_user_id=833478509, tg_username=basil_ivanov
  Username is not testuser. No update needed.
  ```

---

## Commit & Push Status

- **Push/Deploy**: NOT_ATTEMPTED (per TZ instructions)
- **Commit SHA**: `952ad07`
