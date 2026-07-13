# Архитектурная приёмка — dev-only three-horizon timing fixture

Дата: 2026-07-11
Вердикт: `ACCEPTED_FOR_LOCAL_PREVIEW`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
HEAD: `04bebb331575909c70c36412449101ccba999a79`
Commit/push: не выполнялись.

## Принятый URL

```text
http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1
```

## Проверенное поведение

- long: `12 мая 2026 — 11 мая 2027`, `Фон уже действует`;
- medium: `3 июля 2026 — 18 июля 2026`, пик
  `10 июля 2026, 11:32`, `Набирает силу`;
- fast: `7 июля 2026 — 9 июля 2026`, пик `8 июля 2026, 05:00`,
  `Пик уже пройден · влияние ослабевает`;
- fixture root и три timing containers присутствуют в публичном DOM contract;
- evidence без timing не создаёт пустой timing container;
- fixture browser context вызывает только
  `GET /api/dev-fixtures/three-horizon-timing`;
- auth, profile, day и calendar API в fixture context не вызываются;
- обычный URL сохраняет normal auth/profile/day/calendar flow;
- переход с fixture на другой день удаляет fixture query;
- fixture endpoint: local `200`, public Host `404`, unsafe proxy `404`;
- production branch защищён `NODE_ENV` guard;
- общий Grace layout использует Suspense-safe query router с fallback без API и
  auth side effects.

## Независимые gates архитектора

```text
Vitest: 3 files, 15 tests passed
TypeScript: npx tsc --noEmit passed
Diff: git diff --check passed
Playwright mobile: 1 passed
Production build: NEXT_DIST_DIR=.next-arch-review-final pnpm build passed
Preview health after build: HTTP 200 on 3003
```

Временный `.next-arch-review-final` удалён. Автоматические изменения
`next-env.d.ts` и `tsconfig.json` возвращены к исходному содержимому; diff по ним
отсутствует. Production `3002`, API `8000`, nginx, systemd и sidecar не менялись.

Review screenshot:

```text
docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/assets/browser-timing-fixture-mobile.png
```
