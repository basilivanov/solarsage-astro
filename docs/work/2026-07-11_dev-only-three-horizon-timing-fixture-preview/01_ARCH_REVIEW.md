# Архитектурное ревью — dev-only three-horizon timing fixture

Дата ревью: 2026-07-11
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Исходное ТЗ: `docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/00_TZ.md`
Режим: только локальный preview, **без commit/push**.

## Вердикт

`REWORK_REQUIRED`.

Визуальная часть принята: новый screenshot показывает три читаемых timing-блока
с нужными датами, пиками и стадиями. Блокирующие замечания относятся к изоляции
fixture от обычного auth/API flow и к local-only guard.

## 1. BLOCKER — fixture всё ещё запускает auth и profile API

Независимая проверка в новом browser context на URL:

```text
http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1
```

зафиксировала запросы:

```text
POST /api/auth/dev
GET  /api/profile
POST /api/auth/dev
GET  /api/dev-fixtures/three-horizon-timing
GET  /api/profile
...
```

`/api/day/...` действительно не вызывается, но fixture не изолирован от auth и
profile. Причины в текущем коде:

- `DayPage` всегда вызывает `useDay(dateStr, !isDevTimingFixture)`;
- `useDay` всегда вызывает `useTelegramAuth()`, даже при `enabled=false`;
- `DayPage` всегда вызывает `useOnboarded()`, который при пустом localStorage
  обращается к `/api/profile`.

### Обязательная переделка

Разделить обычную и fixture-ветки на разные React child components, чтобы hooks
одной ветки вообще не исполнялись в другой.

Требуемая структура по смыслу:

1. Верхний route component читает `dateStr` и query parameter и выбирает ровно
   одну ветку.
2. Обычная ветка вызывает прежние `useDay(dateStr)`, `useOnboarded()` и calendar
   API без fixture-флагов.
3. Fixture-ветка вызывает только dev fixture loader и рендерит `TodayScreen`.
   В ней не должно быть `useDay`, `useTelegramAuth`, `useOnboarded`, calendar API.
4. Общую чистую часть отображения/loader/error можно вынести в отдельный
   component, если это уменьшит дублирование, но side-effect hooks должны
   оставаться внутри соответствующей ветки.
5. Вернуть публичную сигнатуру `useDay` к исходной:

   ```ts
   useDay(date: string): UseDayResult
   ```

   Удалить `enabled` и весь связанный diff из `lib/grace/hooks/useDay.ts`.
6. Сохранить suppression week-status requests для fixture. Текущий общий prop
   `disableRemoteStatusFetch` допустим, если его default остаётся `false` и
   обычная ветка его не передаёт.
7. Переход на другой день из fixture должен уходить на обычный `/day/<date>` без
   переноса `fixture=...`.

### Сетевой acceptance contract fixture-ветки

После открытия fixture URL среди запросов с pathname `/api/**` разрешён только:

```text
GET /api/dev-fixtures/three-horizon-timing
```

Должно быть ровно `0` запросов к:

```text
/api/auth/**
/api/profile
/api/day/**
/api/calendar/**
```

Повторный GET fixture endpoint из-за React Strict Mode допустим; остальные API
запросы — нет.

## 2. BLOCKER — fixture endpoint не является local-only

Сейчас dev server слушает `0.0.0.0:3003`, а проверка:

```bash
curl -H 'Host: preview.example.test' \
  http://127.0.0.1:3003/api/dev-fixtures/three-horizon-timing
```

возвращает `200`.

### Обязательная переделка route

1. Сигнатура route должна принимать `request: Request`.
2. До чтения/dynamic import fixture выполнить guards в таком порядке:
   - `process.env.NODE_ENV === "development"`;
   - `isLocalDevHost(request.headers.get("host"))`;
   - `!hasUnsafeProxyOriginHeaders(request)`.
3. Переиспользовать готовые helpers из `lib/api/dev-auth-guard.ts`.
4. При любом отказе возвращать `404` или `403`; для скрытого dev harness
   предпочтителен единый `404`.
5. Ни fixture import, ни чтение fixture не должны происходить до прохождения
   всех guards.
6. Production и запрос с публичным Host не должны получать fixture payload.

## 3. Correctness — fixture привязан к одной дате

Fixture payload описывает `2026-07-08`. Не разрешать тому же query parameter
активировать этот payload на `/day/2026-07-09` или другой дате, иначе header и
payload расходятся.

Условие fixture-ветки должно одновременно требовать:

```text
NODE_ENV === development
dateStr === 2026-07-08
fixture === three-horizon-timing
```

При другой дате route page должен идти по обычному auth/API flow.

## 4. Обязательное усиление тестов

### Browser / Playwright

Обновить `e2e/dev-timing-fixture.spec.ts`:

1. Отслеживать **все** `/api/**`, а не только `/api/day/**`.
2. Для fixture URL доказать сетевой contract из раздела 1.
3. Проверить все восемь пользовательских строк по конкретным horizon cards:

```text
long:
Действует: 12 мая 2026 — 11 мая 2027
Сейчас: Фон уже действует

medium:
Активно: 3 июля 2026 — 18 июля 2026
Пик: 10 июля 2026, 11:32
Сейчас: Набирает силу

fast:
Активно: 7 июля 2026 — 9 июля 2026
Пик: 8 июля 2026, 05:00
Сейчас: Пик уже пройден · влияние ослабевает
```

4. Проверить `data-testid="dev-timing-fixture"` и ровно три
   `data-testid="why-time-horizon-timing"`.
5. В отдельном новом browser context открыть обычный
   `/day/2026-07-08?why=1` и проверить:
   - нет `dev-timing-fixture`;
   - нет запроса к `/api/dev-fixtures/three-horizon-timing`;
   - обычный auth/API flow не подменён fixture-веткой.
6. Проверить, что fixture query на другой дате не включает fixture root и не
   вызывает dev fixture endpoint.
7. Оставить один review screenshot только в assets текущего work item.

### Route/unit

Добавить focused tests для dev fixture route:

- development + direct localhost/127.0.0.1 request → `200`;
- production → не `200` и fixture не читается;
- development + public Host → не `200`;
- unsafe forwarded/proxy headers → не `200`.

Существующий тест отсутствия timing-container у evidence без timing сохранить.

## 5. GRACE contracts должны соответствовать коду

Обновить только затронутые contracts/maps, без форматирования посторонних файлов:

- `app/(grace)/day/[date]/page.tsx`: текущий contract ошибочно говорит
  `purpose: Tests for page.tsx behavior`, `emitted_logs: n/a (tests)` и не
  описывает две изолированные ветки;
- `components/today/today-screen.tsx`: указать optional suppression remote week
  statuses, если prop остаётся;
- `components/today/week-strip.tsx`: описать входной prop и реальный network
  side effect/default behavior;
- `components/today/why-time-horizon-card.tsx`: contract сейчас говорит, что
  evidence не отображается вообще, хотя теперь из evidence показывается
  human-readable timing; явно описать это исключение и dependency на stage
  formatter;
- новые dev hook/route contracts обновить с учётом local-host guards и точного
  сетевого поведения;
- после восстановления исходной сигнатуры `useDay` его contract не должен
  упоминать fixture/enabled.

## 6. Scope и assets

- Не делать commit, push, merge.
- Не трогать `3002`, API `8000`, nginx, systemd, sidecar.
- Не добавлять запрещённые untracked paths из `00_TZ.md`.
- Не создавать новые изменения в assets предыдущего work item.
- Если бинарные изменения в
  `docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/*` были
  сделаны именно во время этой browser-fixture задачи, вернуть только их к
  состоянию до этой задачи. Если они уже существовали на момент получения
  `00_TZ.md`, оставить как pre-existing и явно указать это в callback. Не
  использовать общий reset/checkout worktree.

## 7. Проверки перед повторным callback

Выполнить:

```bash
npx vitest run <route-test> __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit
git diff --check
E2E_BASE_URL=http://127.0.0.1:3003 npx playwright test e2e/dev-timing-fixture.spec.ts --project=mobile
curl -fsS -o /dev/null -w '%{http_code}\n' \
  'http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1'
```

Также повторить hostile Host curl и убедиться, что endpoint больше не отвечает
`200`.

## Callback R2

После исправлений вернуть в tmux:

```text
READY_FOR_BROWSER_FIXTURE_TIMING_PREVIEW_R2
fixture_url: http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1
fixture_api_requests: <список уникальных /api/**>
normal_flow: <что проверено>
host_guard: <local status; public-host status; unsafe-proxy status>
timing: long=<...>; medium=<...>; fast=<...>
tests: <точные команды и результаты>
screenshot: <path>
preexisting_asset_diffs: <оставлены/не было/возвращены>
production_untouched: YES
commit: NOT_YET
push: NOT_YET
```
