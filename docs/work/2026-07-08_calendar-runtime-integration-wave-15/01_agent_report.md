# Wave 15 Calendar Runtime Integration Agent Report

Date: 2026-07-08
Branch: `main`
Final status: ready for architect review

## Summary

Wave 14 calendar parity was deployed into the canonical runtime. `main` was pushed, `solarsage-api.service` and `solarsage-frontend.service` were rebuilt/restarted, API calendar contract v2 was verified on port `8000`, and `/calendar` was verified on production frontend port `3002` with both real and mock-visual Playwright suites.

No product UI code was changed. Two e2e-only harness fixes were made after production runtime verification exposed stale assumptions:

- `e2e/calendar.spec.ts`: use stable `calendar-view-moon` / `calendar-view-day` test IDs instead of ambiguous role names; extend real-runtime readiness timeout.
- `e2e/mock-visual/calendar.spec.ts`: cover production Next prefetch requests for `/api/day/2026-07-DD` in mock fixtures.

Runtime deploy fixes applied outside the repo:

- `apps/api/app/services/lunar_facts_service.py` ownership/permissions fixed to `astro:astro`, readable by `solarsage-api.service`.
- `.next-prod/` ownership fixed to `astro:astro` after root-run `pnpm build`.
- `/etc/nginx/sites-enabled/astro.conf` got a localhost-only HTTP proxy block so exact loopback smoke `curl -I http://127.0.0.1/calendar` reaches the canonical frontend.

## Preflight

```bash
git status --short --branch
```

Result before deploy: exit 0. Tracked tree was clean; only known unrelated untracked files were present: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git log --oneline -5
```

Result:

```text
a240931 docs(calendar): request wave 15 runtime integration
729634e docs(calendar): accept wave 14 e2e rework 04
4a22bb5 fix(e2e): default playwright to deterministic workers
a8e39cf docs(calendar): request wave 14 e2e rework 04
dcb63fb fix(calendar): serialize mock visual parity spec
```

```bash
git diff --check HEAD~1..HEAD
```

Result: exit 0, no output.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0, no output.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 78.99s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

## Push

```bash
git push origin main
```

Result: exit 0.

```text
To github.com-solarsage:basilivanov/solarsage-astro.git
   14bcf54..a240931  main -> main
```

The final Wave 15 report/artifact/e2e-harness commit was pushed after this report was created.

## Build And Services

```bash
systemctl restart solarsage-api.service && systemctl status solarsage-api.service --no-pager
```

Initial restart exposed a deploy permission issue:

```text
PermissionError: [Errno 13] Permission denied: '/opt/solarsage-astro/apps/api/app/services/lunar_facts_service.py'
```

Runtime fix:

```bash
chown astro:astro apps/api/app/services/lunar_facts_service.py
chmod 664 apps/api/app/services/lunar_facts_service.py
```

Final API status:

```text
Active: active (running)
Uvicorn running on http://127.0.0.1:8000
```

```bash
pnpm build
```

Result: exit 0. Next.js 16.2.6 compiled successfully; 18 static pages generated.

```bash
systemctl restart solarsage-frontend.service && systemctl status solarsage-frontend.service --no-pager
```

Initial restart exposed a deploy artifact ownership issue:

```text
Error: EACCES: permission denied, open '/opt/solarsage-astro/.next-prod/BUILD_ID'
```

Runtime fix:

```bash
chown -R astro:astro .next-prod
```

Final frontend status:

```text
Active: active (running)
next-server (v16.2.6)
Local: http://localhost:3002
```

Port check:

```text
127.0.0.1:8000 LISTEN uvicorn
*:3002 LISTEN next-server
```

## Runtime API Contract

Commands used:

```bash
INITDATA=$(python3 scripts/generate-telegram-test-initdata.py | rg '^query_id=' | head -1)
BODY=$(INITDATA="$INITDATA" node -e 'process.stdout.write(JSON.stringify({initData: process.env.INITDATA}))')
rm -f /tmp/astro_cookie.txt
curl -s -c /tmp/astro_cookie.txt -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/auth/telegram -d "$BODY"
curl -s -b /tmp/astro_cookie.txt 'http://127.0.0.1:8000/api/calendar?month=2026-07'
```

Result summary:

```json
{
  "schemaVersion": "calendar/v1",
  "contractVersion": 2,
  "julyDays": 92,
  "daysWithPhaseIndex": 92,
  "day20260708": {
    "phase": "waning_crescent",
    "phaseIndex": 7,
    "phaseLabel": "убыв. серп",
    "illumination": 39,
    "lunarDay": 24,
    "moonSign": "Aries",
    "voidOfCourse": false
  }
}
```

Required assertions passed: `contractVersion=2`, `days[].lunar.phaseIndex` exists, and `2026-07-08` has non-null `phase`, `phaseIndex`, `phaseLabel`, `illumination`, and `lunarDay`.

## Frontend Runtime Smoke

```bash
curl -I http://127.0.0.1:3002/calendar
```

Final result: exit 0, `HTTP/1.1 200 OK`.

```bash
curl -I http://127.0.0.1/calendar
```

Initial result: `HTTP/1.1 404 Not Found` because loopback HTTP hit another nginx default. Since API and frontend were healthy, a localhost-only nginx proxy block was added and nginx was reloaded:

```bash
nginx -t && systemctl reload nginx
```

Final result: exit 0, `HTTP/1.1 200 OK`.

## E2E Results

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/calendar.spec.ts
```

Initial result: failed.

- Chromium: strict locator violation because `getByRole('button', { name: 'Луна' })` matched the view toggle plus lunar day buttons.
- Mobile: real production auth/calendar loading exceeded the old 15s readiness window.

Harness-only fix: switched to stable `data-testid` selectors and raised the runtime readiness timeout.

Final result:

```text
Running 2 tests using 1 worker
2 passed (9.2s)
```

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Initial result: failed.

- Production Next prefetch requested `/api/day/2026-07-05`, `/api/day/2026-07-06`, `/api/day/2026-07-07`, `/api/day/2026-07-08`, `/api/day/2026-07-09`, and `/api/day/2026-07-11`; the mock visual harness had only `/api/day/2026-07-10`.

Harness-only fix: added deterministic July day fixture coverage for `/api/day/2026-07-DD`.

Final result:

```text
Running 12 tests using 1 worker
12 passed (37.4s)
```

## Screenshot Evidence

Artifacts:

- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/oracle-3001-calendar.png`
- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/runtime-3002-calendar.png`
- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/runtime-3002-day-mode-top.png`
- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/runtime-3002-moon-mode.png`
- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/runtime-3002-mobile-390x844.png`
- `docs/work/2026-07-08_calendar-runtime-integration-wave-15/artifacts/runtime-3002-tall-430x932.png`

Artifact sizes:

```text
oracle-3001-calendar.png              87K
runtime-3002-calendar.png             54K
runtime-3002-day-mode-top.png         52K
runtime-3002-mobile-390x844.png       43K
runtime-3002-moon-mode.png            47K
runtime-3002-tall-430x932.png         46K
```

Visible runtime gap versus 3001: the 3002 real runtime screenshot is from an authenticated real test user whose access state shows locked/preview day states, while the 3001 oracle is demo/full-access. The calendar contract and lunar presentation are present on 3002; the visible access-state difference is not a calendar parity rendering defect.

## Callback

Callback response: `{"ok": true}`.
