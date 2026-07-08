# Wave 13 Rework 01 TZ

You are the coder agent. Work on branch `main` in `/opt/solarsage-astro`.

Read first:
- `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/00_TZ.md`
- `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/02_arch_review.md`

Goal: resolve all review findings without cosmetic frontend changes.

## Required Work

1. Protect the real Basil Telegram account from tests.
   - Remove `833478509` as the default test user from `scripts/generate-telegram-test-initdata.py`.
   - Default E2E auth must use a synthetic isolated Telegram id, or unique generated ids by default.
   - Keep real-user smoke possible only via explicit CLI/env input.
   - Env-gate or refactor `apps/api/tests/test_pipeline_integration.py` so normal pytest never calls the remote dev URL or hardcoded Basil credentials.
   - Add/adjust a test proving default generated initData does not contain `833478509`.

2. Fix `ConcreteAdvice` verdict/evidence consistency.
   - A row's primary evidence and verdict must be derived together.
   - Remove the independent `planet_aspect_verdicts` overwrite pattern.
   - For no-direct-score product spheres, do not produce `good/caution/avoid` from generic planet influence alone.
   - If a no-direct-score row gets a non-neutral verdict, it must come from selected aspect evidence with compatible polarity.
   - For direct-score rows, choose evidence that explains the score direction.
   - Add tests for contradiction prevention:
     - no `good` row with primary square/opposition evidence;
     - no `caution`/`avoid` row with only soft-aspect primary evidence.

3. Align calendar scoring with `/day`.
   - Extract a shared helper for filtering day-scored signals.
   - Use the same helper in `TodayService` and `CalendarService`.
   - Do not let unversioned `SemanticLayerCache` override current scoring semantics. Either version it properly or stop using it as an authoritative calendar status source.
   - Add a calendar regression where full mixed signals and filtered day signals differ; calendar must match filtered day scoring.

4. Bump cache version after the scoring/verdict fix.
   - Increment `TODAY_CONTENT_VERSION` beyond `4`.
   - Update API/frontend generated contracts and tests.
   - Ensure stale payload/semantic cache cannot serve the old v4 contradiction.

5. Repair production user metadata safely.
   - After code/tests pass, check `users` for `tg_user_id=833478509`.
   - If `tg_username` is exactly `testuser`, update it to `basil_ivanov`.
   - Do not mutate profile birth/current-city/access data.

## Verification

Run and report exact commands/results:
- `cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py tests/test_day_endpoints.py tests/test_access_service.py tests/test_calendar_endpoints.py -q`
- targeted test for `scripts/generate-telegram-test-initdata.py` default safety
- `npx vitest run TodayScreen.test.tsx sphere-labels.test.ts`
- a production-style script for `tg_user_id=833478509` showing:
  - DB username
  - access states for 2026-07-08, 2026-07-11, 2026-07-12
  - `/day` concrete advice rows for 2026-07-08 have no verdict/evidence polarity contradictions
  - calendar status for 2026-07-08 matches filtered day scoring

## Report

Write:
- `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/04_rework_01_report.md`

Include:
- changed files
- root causes fixed
- verification outputs
- production user metadata result
- commit hash
- push/deploy status

Commit your changes. Do not push/deploy unless explicitly asked.

When done, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 13 Rework 01 ready for architect review. Report: docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/04_rework_01_report.md. Branch: main. Commit: <HEAD>. Push: NOT_ATTEMPTED"}'
```
