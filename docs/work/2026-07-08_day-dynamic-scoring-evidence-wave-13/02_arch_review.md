# Wave 13 Architect Review

Status: REWORK REQUIRED

Reviewed commit range: `9541926..4b0f100`

## Findings

### P0 — E2E/default test auth mutates the real Basil Telegram user

Evidence:
- `scripts/generate-telegram-test-initdata.py:63-68` and `:147-149` default to `user_id=833478509`, `username=testuser`.
- `e2e/fixtures.ts:103-109` defaults `uniqueTelegramUser=false`, so many E2E tests use that default real user.
- `e2e/auth-helper.ts:29-71` also calls the generator without overriding the user.
- `apps/api/tests/test_pipeline_integration.py:222-239` hardcodes the real Basil Telegram id, bot token, username, and remote dev URL.
- Live DB check after the wave: `tg_user_id=833478509` currently has `tg_username=testuser`, while the requested production user is `basil_ivanov`.

Impact:
- Running E2E/smoke against the real API can overwrite the production user's username/session/cache.
- Any "verify on Basil data" result is polluted by the test harness itself.

Required fix:
- Stop using `833478509` as the default test user anywhere.
- Make E2E generate an isolated synthetic Telegram user by default. Keep real-user testing opt-in only via explicit CLI/env variables.
- Change `uniqueTelegramUser` default to the safe path, or make `generateInitData()` itself choose a synthetic non-real id when no id is passed.
- Disable or env-gate `test_pipeline_integration.py` remote dev calls; no normal pytest should call `https://dev...` or use a hardcoded bot token/user.
- Add a regression check that default generated initData does not contain `833478509`.
- Restore the DB username for `tg_user_id=833478509` to `basil_ivanov` after the code fix, only if it is still `testuser`.

### P1 — `ConcreteAdvice` verdict can contradict its own evidence

Evidence:
- `apps/api/app/services/today_interpretation_service.py:233-243` builds `planet_aspect_verdicts` by overwriting a planet's verdict while iterating all aspects.
- `apps/api/app/services/today_interpretation_service.py:322-359` later chooses evidence independently with `next(...)`.
- Live cache for 2026-07-08 shows:
  - `shopping`: `verdict=good`, evidence `Венера квадратура Уран`.
  - `documents`, `creativity`, `study`: `verdict=caution`, evidence `Солнце трин Меркурий`.

Impact:
- Counts like `1 благоприятно / 8 осторожно` are not reliably explainable by the row evidence.
- The UI looks templated because the text is LLM wording over inconsistent backend facts.

Required fix:
- Make the selected primary evidence signal the source of the row verdict.
- Remove the independent mutable `planet_aspect_verdicts` fallback, or replace it with a helper that returns `(selected_signal, verdict)` together.
- For rows without direct canon sphere score:
  - do not inflate them to `good/caution/avoid` from generic planet influence alone;
  - use a non-neutral verdict only when the selected primary evidence has a compatible aspect polarity.
- For rows with direct canon score:
  - evidence ordering must prefer signals that explain that verdict: tense aspects for `caution/avoid`, soft aspects for `good`, then house evidence.
- Add tests proving a row cannot be `good` with primary square/opposition evidence, and cannot be `caution/avoid` with only soft-aspect primary evidence.

### P1 — Calendar day status still uses mixed natal+day scoring and unversioned semantic cache

Evidence:
- `apps/api/app/services/calendar_service.py:254-255` calls `score_day(signals)` on the full `normalize_day()` output, including static natal signals.
- `/day` now filters to `day_signals` in `apps/api/app/services/today_service.py:231-237`.
- `apps/api/app/services/calendar_service.py:196-207` trusts `SemanticLayerCache` before checking versioned `TodayPayloadCache`, but semantic cache has no content/scoring version.

Impact:
- Calendar/week status can diverge from `/day`.
- Old semantic statuses can survive a day-scoring change even after `TODAY_CONTENT_VERSION` is bumped.

Required fix:
- Extract one shared helper for "day-scored signals" and use it in both `TodayService` and `CalendarService`.
- Stop using unversioned `SemanticLayerCache` as an authoritative status source, or add a version/profile key and invalidate old entries.
- Add a regression test where full mixed signals and filtered day signals produce different statuses; calendar must match the filtered `/day` result.

### P1 — Current content cache version is not enough after scoring/verdict semantics changed

Evidence:
- `TODAY_CONTENT_VERSION` is `4`.
- Existing v4 cache rows were generated during this wave and already contain the verdict/evidence mismatch above.

Impact:
- After fixing the logic, production can still serve stale v4 rows with wrong counts/text.

Required fix:
- Bump `TODAY_CONTENT_VERSION` again after the rework.
- Ensure stale semantic/payload rows no longer win for `/day` or calendar.
- Update generated frontend/API contracts and tests that assert content version.

## Verification Required

Run at minimum:
- `cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py tests/test_day_endpoints.py tests/test_access_service.py tests/test_calendar_endpoints.py -q`
- targeted regression for the Telegram initData default safety
- `npx vitest run TodayScreen.test.tsx sphere-labels.test.ts`
- production-style calculation check for `tg_user_id=833478509` after the fix:
  - DB username is `basil_ivanov`
  - 2026-07-08 `/day` has no verdict/evidence contradictions
  - 2026-07-12 remains locked because access ends 2026-07-11, not because Sunday calculation is skipped
