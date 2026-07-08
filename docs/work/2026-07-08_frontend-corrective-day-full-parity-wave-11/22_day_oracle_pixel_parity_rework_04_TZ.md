# Wave 11 Rework 04 TZ — Russian Copy Leak Fix

Owner: coder agent
Branch: `main`
Scope: minimal follow-up after Rework 03
Report path: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/23_day_oracle_pixel_parity_rework_04_report.md`

## Read First

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/21_day_oracle_pixel_parity_rework_03_review.md`

## Required Work

1. Fix the visible English copy leak:
   - replace `Сократи траты — день для financial discipline`
   - with `Сократи траты — день для финансовой дисциплины`

2. Add/strengthen tests:
   - concrete advice rows must not contain Latin alphabet words (`/[A-Za-z]/`) in visible row text;
   - keep the existing no-placeholder/no-unavailable tests.

3. Update stale comments in `components/today/concrete-day-advice.tsx`:
   - remove references to graceful/unavailable rows from the module contract;
   - describe the new oracle fallback behavior.

4. Regenerate evidence under the existing Rework 03 artifact folder:
   - `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/summary.json`
   - screenshots may be overwritten if the capture script does so.

5. Verification commands:

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
git diff --check HEAD~2..HEAD
```

If `7777` needs restart, start it with `NODE_ENV=production`, otherwise it may serve the wrong `.next` directory.

## Commit and Callback

Commit the follow-up fix on `main`.

Do not include unrelated untracked paths:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`

After commit, call back:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Day Oracle Pixel Parity Rework 04 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/23_day_oracle_pixel_parity_rework_04_report.md. Branch: main. Commit: <SHA>."}'
```
