# Deploy Report: Wave 10 To 3002

Date: 2026-07-08
Branch: `main`
Frontend commit deployed: `8ada887`
Docs accept commit: `91dd48e`

## Actions

- Ran fresh production build with `pnpm build`.
- Restored generated `next-env.d.ts` to the tracked canonical import after build.
- Fixed `.next-prod` ownership to `astro:astro` because the build artifact had root-owned files and `solarsage-frontend.service` runs as `astro`.
- Restarted `solarsage-frontend.service`.
- Updated Telegram menu button cachebuster for @vi_astro_bot:
  - default menu: `https://dev.astro.vasiliy-ivanov.ru/day/today?tg_build=91dd48e-20260708011640`
  - admin chat menu: `https://dev.astro.vasiliy-ivanov.ru/day/today?tg_build=91dd48e-20260708011743`

## Verification

```bash
systemctl status solarsage-frontend.service --no-pager -l
```

Result: active/running on port 3002.

```bash
curl http://127.0.0.1:3002/day/2026-07-05
```

Result: HTTP 200.

```bash
curl --resolve dev.astro.vasiliy-ivanov.ru:443:127.0.0.1 \
  https://dev.astro.vasiliy-ivanov.ru/day/2026-07-05
```

Result: HTTP 200.

```bash
curl --resolve test.astro.vasiliy-ivanov.ru:443:127.0.0.1 \
  https://test.astro.vasiliy-ivanov.ru/day/2026-07-05
```

Result: HTTP 200.

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile
```

Result: PASS, 4 tests.

## Bot Notes

`ductor-astro.service` has `WEBAPP_URL=https://dev.astro.vasiliy-ivanov.ru`, and nginx routes that host to 3002.

The service log still reports intermittent `TelegramConflictError`, which means another polling client for the same Telegram bot may exist outside the visible `ductor-astro.service` process. The Telegram menu button itself was verified after update and retained the new `91dd48e` cachebuster.
