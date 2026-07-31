# 46 — P7-F2B DAY PAGE WIRING TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер работает
только в apps/api + components (sphere page) — не пересекайся (см. §7).

## 1. Packet title

P7-F2b — подключение `/day/[date]` к новому TodayScreen: API client +
data hook на `TodayConvergencePayload`, impression после первого paint,
pending-polling, переписывание W9 «переписать» тестов страницы/хука.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F2b.

## 3. Modules

- Новый: `M-API-CLIENT-TODAY-CONVERGENCE` — `lib/api/today-convergence.ts`
- Новый: `M-HOOK-TODAY-CONVERGENCE` — `lib/grace/hooks/useTodayConvergence.ts`
  (рядом с существующим lib/grace/hooks/useDay.ts — паттерн повторить)
- Изменяемый: `M-APP-DAY-PAGE` — `app/(grace)/day/[date]/page.tsx`
- Tests: `__tests__/components/TodayScreen.test.tsx` (переписать),
  `__tests__/app/day-page.test.tsx` (переписать),
  `__tests__/hooks/useDay.test.ts` → удалить, заменив
  `__tests__/hooks/useTodayConvergence.test.ts` (новый)

## 4. Goal

`/day/[date]` (включая `/day/today`) рендерит `components/today-convergence/today-screen`
на реальном `GET /api/day/{date}` envelope: loading/error/ready states,
impression `surface=day` после первого успешного paint, polling пока
`contentState=pending`, retry с cooldown. Legacy `useDay`/
`adaptTodayPayload`/legacy `components/today/today-screen` из страницы
удаляются (файлы legacy остаются до W9, но недостижимы).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §2 (оси), §9 (loading/retry/disclosure/impression :233-244), §11
  (test contract).
- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §6 (HTTP: retry 202+Retry-After, impression POST).
- Существующее:
  - `components/today-convergence/today-screen.tsx` (P7-F2a, в HEAD) —
    публичные props компонента.
  - `lib/grace/hooks/useDay.ts` — паттерн hook (НЕ переиспользовать код,
    он legacy; паттерн структуры — да).
  - `lib/api/calendar.ts` — паттерн API client с zod-валидацией.
  - `packages/contracts/today-convergence.ts` — TodayConvergencePayload +
    TodayConvergencePayloadWireSchema.
  - `app/(grace)/day/[date]/page.tsx` — текущая страница (loading/error
    handling, onboarding guard, TODAY constant, toDateParam/fromDateParam).
  - Impression endpoint: `POST /api/day/snapshots/{id}/impression`
    body `{surface: "day"}` → 204.
  - Retry endpoint: `POST /api/day/{date}/retry` → 200 envelope |
    202 + Retry-After.

## 6. Exact write scope

- `lib/api/today-convergence.ts` (новый)
- `lib/grace/hooks/useTodayConvergence.ts` (новый)
- `app/(grace)/day/[date]/page.tsx` (переписать на новый путь)
- `__tests__/components/TodayScreen.test.tsx` (переписать под новый
  компонент, см. §8.4)
- `__tests__/app/day-page.test.tsx` (переписать)
- `__tests__/hooks/useTodayConvergence.test.ts` (новый)
- Удалить `__tests__/hooks/useDay.test.ts` (равноценная замена выше)
- `grace/frontend.paths` — если новые lib-пути требуют регистрации
  (проверить покрытие)

## 7. Frozen / Out of scope

- НЕ менять: `lib/grace/hooks/useDay.ts`, `lib/adapters/*`,
  `components/today/*` (legacy, недостижимы после переключения — удалит W9),
  `components/today-convergence/*` (приняты; если обнаружишь баг —
  эскалация, не правка), backend, `packages/contracts/*`,
  `app/(grace)/today/page.tsx` (redirect уже верный), calendar/sphere
  страницы (F3), e2e.
- НЕ добавлять новых npm-зависимостей.

## 8. Функциональные требования

### 8.1 API client (`lib/api/today-convergence.ts`)

- `fetchTodayConvergence(dateParam: string): Promise<TodayConvergencePayload>`
  — GET `/api/day/{dateParam}`, zod-валидация ответа
  `TodayConvergencePayloadWireSchema`, typed errors (network/invalid/401/422).
- `retryTodayConvergence(dateParam): Promise<{payload?, retryAfterSeconds?}>`
  — POST retry; 202 → retryAfterSeconds из заголовка.
- `recordDayImpression(snapshotId): Promise<void>` — POST impression
  `{surface:"day"}`; сбой НЕ пробрасывается наружу (telemetry best-effort,
  void).
- Паттерн fetch/credentials — как `lib/api/calendar.ts` (same-origin,
  cookie session).

### 8.2 Hook (`lib/grace/hooks/useTodayConvergence.ts`)

- Состояния: `{screenState: "loading"|"ready"|"error", payload?, refetch}`.
- Первый успешный ready с доступным deterministic блоком → однократный
  `recordDayImpression` (guard от повторов; preview/locked/unavailable —
  НЕ отправлять, 03 §9).
- `contentState=pending` → polling GET каждые ~4s (max ~2 мин, потом стоп
  без error; задокументировать константы).
- `refetch` для retry-кнопок (unavailable / error / narrative retry):
  вызывает POST retry; при 202 → показать countdown по Retry-After,
  disabled-кнопка на время.
- Unmount safety (no setState после unmount), AbortController на fetch.

### 8.3 Страница (`app/(grace)/day/[date]/page.tsx`)

- Рендер `TodayScreen` из `components/today-convergence` с payload hook'а;
  loading → skeleton компонента (`screenState="loading"`); error →
  `screenState="error"` + retry.
- Сохранить: onboarding guard (существующий), dateParam today/ISO логику,
  навигацию по датам (если была).
- Удалить из страницы: `useDay`, `adaptTodayPayload`, legacy
  `components/today/today-screen`, `useThreeHorizonTimingFixture`,
  TodayPayload типы, `getMonthCalendar` если использовался для day.
- GRACE header страницы обновить (dependencies/outputs по факту).

### 8.4 Тесты

- `__tests__/components/TodayScreen.test.tsx` — переписать: рендер
  нового компонента на fixtures (subset: hero ready, quiet steady,
  pending, unavailable, preview, locked) с DOM-contract assertions.
  Старые assertions на DayStatus/TodayFocus — удалить.
- `__tests__/app/day-page.test.tsx` — переписать: mock hook/API client;
  loading/ready/error ветки страницы; onboarding guard сохранён.
- `__tests__/hooks/useTodayConvergence.test.ts` — состояния, impression
  однократно и не на preview/locked, polling стартует на pending и
  останавливается на ready, retry 202 → countdown, unmount safety.
- `__tests__/hooks/useDay.test.ts` — удалить (покрытие заменено выше).

## 9. Must-preserve invariants

- `npx vitest run` зелёный полностью.
- `npx tsc --noEmit` чист.
- `python3 scripts/grace_front_lint.py` PASS.
- Production build собирается: `NODE_ENV=production npx next build` (или
  проектная команда build без dev-server) — без ошибок импорта/типов.
- Legacy rg-gate: `rg -n 'DayStatus|TodayFocus|relativeStatus'
  __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx
  __tests__/hooks/` → 0 matches.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/hooks/useTodayConvergence.test.ts \
  __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx 2>&1 | tail -3
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -3
python3 scripts/grace_front_lint.py 2>&1 | tail -1
NODE_ENV=production npx next build 2>&1 | tail -5
```

## 11. Expected evidence

- Список файлов; вывод §10; подтверждение legacy rg-gate; build tail.

## 12. Escalation rule

Нужно менять компоненты P7-F2a, contracts, backend или onboarding guard →
СТОП, доложить. Нестыковка hook/page API с компонентом → в отчёт.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
