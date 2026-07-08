# Wave 13 Rework 02 Architect Review

Status: ACCEPTED

Reviewed commits:
- `70cc05f` — backend scoring/advice/cache/test safety implementation.
- `f4c6445` — frontend fixture/test self-contained cleanup.
- `3d6cef4` — rework 02 report.
- `4a55a54` — non-self-referential report SHA note.

## Acceptance Notes

- `main` HEAD is self-contained for the reviewed scope.
- `next-env.d.ts` is not modified and was not committed.
- Runtime mock/demo files remain present in the repo, but current `/day` route uses API payload through `adaptTodayPayload`; concrete advice text is rendered from `payload.concreteAdvice.rows[].text`.
- Remaining untracked files are outside the reviewed Wave 13 scope:
  - `.grace/`
  - `grace.db`
  - `skills/`
  - `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`

## Architect Verification

Fresh verification from `HEAD`:

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/hooks/useDay.test.ts __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/lib/display/sphere-labels.test.ts
```

Result:
- `5 passed`
- `69 passed`

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py tests/test_day_endpoints.py tests/test_access_service.py tests/test_calendar_endpoints.py tests/test_telegram_hmac.py -q
```

Result:
- `37 passed`
- `1 warning`

```bash
git diff --check HEAD~5..HEAD
git status --short --branch
```

Result:
- `git diff --check`: clean.
- tracked working tree: clean.

## Basil Production-Style Calculation Check

Architect independently verified via DB + real sidecar calculation:

- `tg_user_id=833478509` has username `basil_ivanov`.
- profile data: `1980-10-30`, `19:50`, `Мончегорск`, current city `Сочи, Россия`, timezone `Europe/Moscow`.
- access:
  - `2026-07-08`: `full`, referral days left `4`, access until `2026-07-11`.
  - `2026-07-11`: `full`, referral days left `1`, access until `2026-07-11`.
  - `2026-07-12`: `locked`, reason `outside_access_window`, access until `2026-07-11`.
- Sunday `2026-07-12` does compute: direct scoring returns `steady`; it is locked only by access window.
- Direct day scoring and calendar scoring match for `2026-07-08`, `2026-07-11`, `2026-07-12`.
- Concrete advice verdict/evidence contradiction check returned no contradictions for those dates.

## Push/Deploy

Not attempted in this review.
