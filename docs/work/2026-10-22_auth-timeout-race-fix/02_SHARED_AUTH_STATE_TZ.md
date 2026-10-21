# TZ 02: Единое auth-состояние (singleton store), гонка таймаута, retry UI

1. **Packet title**: SLICE-02 shared auth state + timeout race fix + auth-error retry
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 02/05
3. **Modules**: M-HOOK-TELEGRAM-AUTH (`hooks/use-telegram-auth.ts`),
   M-GRACE-LAYOUT (`app/(grace)/layout.tsx`)
4. **Goal**: один общий auth-state для всех потребителей (один POST, один таймер),
   дедлайн 12 с ставится до проверки SDK, `clearTimeout` сразу по ответу fetch,
   экран `auth-error` рендерится независимо от `inTelegram` и имеет рабочую кнопку retry.

## 5. Exact write scope (только эти файлы)

- `hooks/use-telegram-auth.ts` — переработка на module singleton store.
- `app/(grace)/layout.tsx` — экран ошибки + кнопка retry.
- `__tests__/hooks/useTelegramAuth.test.ts` — обновление + новые кейсы.

## 6. Frozen / out-of-scope

- `components/telegram-provider.tsx`, `lib/telegram/init-data.ts` — срез 01 (уже принят; использовать `resolveTelegramInitData` оттуда).
- `lib/grace/hooks/useTodayConvergence.ts` — срез 03, НЕ трогать.
- Бэкенд, e2e — срезы 04/05.
- Не менять публичные поля возврата хука: `{ isLoading, isAuthenticated, error }` (добавляется `retry`).

## 7. Must-preserve invariants

- Promo tokens never hit referral claim endpoint / localStorage; только numeric referral codes persisted/claimed.
- Promo intent stored перед `isAuthenticated=true`.
- Нет raw initData / start_param / promo / referral кодов в логах.
- Dev auth (`/api/auth/dev`) только при `NODE_ENV=development`.
- `data-testid`: `auth-loading`, `auth-error` — не переименовывать; новый `auth-retry`.
- GRACE-маркеры: обновить MODULE_CONTRACT (invariants: single shared state), MODULE_MAP (entrypoints: `useTelegramAuth`, `AUTH_TIMEOUT_MS`, `__resetTelegramAuthForTests`), FUNCTION_CONTRACT'ы под новое поведение.

## Техническое задание

### 8.1. `hooks/use-telegram-auth.ts` — module singleton store

Текущая проблема: каждый экземпляр хука = независимый state machine (два POST, гонки).
Целевая схема (без React provider, без правки root layout):

- Module-level store: `{ state, listeners }`; `setState` создаёт НОВЫЙ объект и нотифицирует.
- `useTelegramAuth()` — `useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)`;
  server snapshot = константа `{ isLoading: true, isAuthenticated: false, error: null }`
  (как текущий initial — гидратация не ломается).
- useEffect хука (в каждом экземпляре) вызывает `ensureAuthStarted({ webApp, loaded })` —
  идемпотентно: одинаковый ключ + не-error статус → no-op. Unmount потребителя auth НЕ отменяет.
- Экспорты: `useTelegramAuth()`, `AUTH_TIMEOUT_MS = 12000`, `__resetTelegramAuthForTests()`.
- Хук возвращает `{ ...state, retry }`.

Логика `ensureAuthStarted` / `authenticate`:
1. initData = `resolveTelegramInitData(webApp ?? window.Telegram?.WebApp)` (helper из среза 01).
2. При ПЕРВОМ ensure-вызове (любом) запустить deadline-таймер `AUTH_TIMEOUT_MS`, если ещё не запущен. Срабатывание → state error `'Authentication timeout'` + `logger.warn` с `{ timeout_budget_ms: AUTH_TIMEOUT_MS, elapsed_ms, attempt }`.
3. initData есть → `authenticate()` НЕМЕДЛЕННО (не ждать `loaded`).
4. initData нет + `loaded` → текущая ветка not-in-telegram (dev auth в dev-режиме, иначе skip: isLoading=false, error=null) — это конечное состояние, таймер гасится.
5. initData нет + `!loaded` → ждём (эффект перезапустится при смене provider state); deadline-таймер из п.2 тикает.
6. В `authenticate()`: `clearTimeout` СРАЗУ после прихода ответа fetch (до `sleep(500)`, до referral-claim, до коммита state). При любом конечном исходе таймер погашен ровно один раз.
7. Лог длительности: `logger.info('[TGAuth] Auth completed', { duration_ms, attempt })` (и для неуспеха).
8. `retry()`: гасит таймер, attempt += 1, state → loading, полный перезапуск authenticate с тем же ключом (force, минуя dedup). Используется кнопкой и (в срезе 03) при 401.
9. `__resetTelegramAuthForTests()`: возвращает store в исходное (для beforeEach в тестах).

### 8.2. `app/(grace)/layout.tsx` — экран ошибки

- `if (error)` — БЕЗ `&& inTelegram`. Текст: `inTelegram` → «Пожалуйста, попробуйте ещё раз.»; иначе → «Пожалуйста, откройте приложение через Telegram бот.»
- Кнопка `<button type="button" data-testid="auth-retry" onClick={retry}>Попробовать снова</button>` — всегда на экране ошибки; стили в духе существующих (кнопка primary, Tailwind-токены проекта).
- `retry` берётся из `useTelegramAuth()`.

### 8.3. Тесты `__tests__/hooks/useTelegramAuth.test.ts`

- beforeEach: `__resetTelegramAuthForTests()` (state больше module-level — изоляция обязательна).
- Существующие кейсы сохранить (поправить под store-семантику).
- Новые кейсы (fake timers):
  a. ответ fetch на 11 с при бюджете 12 с → success, ошибки нет, таймер погашен (гонка закрыта);
  b. ответ после 12 с → `Authentication timeout`; warn-лог содержит `timeout_budget_ms` и `elapsed_ms`;
  c. SDK не загружен и initData нет → через 12 с всё равно конечное состояние error (не вечный isLoading);
  d. два одновременно смонтированных экземпляра хука → ровно ОДИН POST /api/auth/telegram;
  e. `retry()` после timeout → повторный authenticate, новый таймер, при успехе isAuthenticated=true;
  f. initData из `#tgWebAppData` без SDK → authenticate стартует немедленно (если срез 01 уже в дереве).

## 8. Verification (одна команда)

```bash
npx vitest run __tests__/hooks/useTelegramAuth.test.ts __tests__/hooks/useTodayConvergence.test.ts __tests__/hooks/useCalendar.test.ts
```

Все три зелёные (два последних мокают `useTelegramAuth` — регресс-контроль API).

## 9. Expected evidence

- diff по 3 файлам; вывод verification (PASS); краткое описание store-схемы (5 строк в отчёте).

## 10. Escalation rule

Понадобился файл вне п.5, изменение полей возврата хука или отказ от singleton-подхода → стоп, доложить, ждать новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
