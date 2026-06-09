# ТЗ: W-PROD-DEMO-GUARD — защита production от demo/mock режима

Дата: 2026-06-09
Статус: ready for coder
Scope: frontend production safety / demo-mode guard

## 1. Цель

Сделать защиту, чтобы production-сборка и production-runtime не могли случайно работать на demo/mock данных.

В проекте есть demo-mode через `NEXT_PUBLIC_DEMO_MODE`, `lib/demo-mode.ts`, `lib/demo-data.ts`. Это нормально для разработки, но опасно для прода: пользователь может увидеть локальные demo payloads вместо реального API.

После пакета production должен работать только с реальным backend API или явно прерывать сборку/старт при небезопасной env-конфигурации.

## 2. Не входит в пакет

Не делать:

- оплату / YooKassa;
- paywall;
- natal frontend;
- новый natal renderer;
- переработку Today;
- переработку Horary;
- backend astrology pipeline;
- новые product-фичи.

Натал-фронт — следующий отдельный пакет: `W-NATAL-FRONTEND-MVP`.

## 3. Требуемое поведение

### Development

В development demo-mode разрешён:

- `NODE_ENV=development`;
- `NEXT_PUBLIC_DEMO_MODE=true`.

Приложение запускается. Допустим console warning: `Demo mode enabled`.

### Preview / staging

Preview/staging demo-mode разрешён только если явно задан override:

- `NEXT_PUBLIC_DEMO_MODE=true`;
- `ALLOW_DEMO_MODE_IN_PREVIEW=true`.

Без override preview/staging должен блокировать demo-mode как production.

### Production

В production demo-mode запрещён.

Если `NODE_ENV=production` и `NEXT_PUBLIC_DEMO_MODE=true`, build/startup должен падать с понятной ошибкой вроде:

`Unsafe production config: NEXT_PUBLIC_DEMO_MODE=true is forbidden in production`.

Предпочтительно падать на build/startup, а не показывать ошибку пользователю уже в UI.

## 4. Что изменить

### 4.1. Добавить централизованный production guard

Создать модуль, например:

`lib/env/production-guard.ts`

Он должен экспортировать:

`assertProductionSafety()`

Логика:

- определить `NODE_ENV`;
- определить `NEXT_PUBLIC_DEMO_MODE`;
- определить `ALLOW_DEMO_MODE_IN_PREVIEW`;
- определить deployment env через `VERCEL_ENV` или `APP_ENV`;
- запретить demo-mode в production;
- запретить demo-mode в preview/staging без явного override.

### 4.2. Подключить guard на frontend startup/build

Нужно подключить проверку так, чтобы она сработала до пользовательского UI.

Подходящие места:

- `next.config.*` для build-time проверки;
- `lib/demo-mode.ts` для runtime проверки.

Лучше сделать обе защиты: build-time + runtime.

### 4.3. Обновить `lib/demo-mode.ts`

Сделать явную функцию `resolveDemoMode()`.

Она должна:

- вызвать production guard;
- вернуть boolean demo-mode;
- в development при включённом demo-mode логировать warning;
- в production не допускать `true`.

### 4.4. Запретить production fallback на demo data

Нельзя, чтобы production при ошибке API возвращал demo payload.

Правило:

- demo data можно использовать только если demo-mode явно включён и разрешён guard-ом;
- production API error должен приводить к error/empty/locked state, но не к demo payload.

Проверить минимум:

- `lib/api/*`;
- `lib/demo-data.ts`;
- `lib/demo-mode.ts`;
- `components/today/*`;
- `app/(app)/day/*`;
- `app/(app)/readings/*`.

### 4.5. Optional dev marker

Можно добавить dev-only marker `DEMO MODE`, если demo-mode включён в development.

Это optional и не блокирует acceptance.

## 5. Обновить документацию/env

Обновить `.env.example` и README/docs env-файл, если есть.

Обязательно зафиксировать:

- production должен использовать `NEXT_PUBLIC_DEMO_MODE=false`;
- `NEXT_PUBLIC_DEMO_MODE=true` в production должен ломать build/startup;
- `ALLOW_DEMO_MODE_IN_PREVIEW=true` разрешён только для preview/staging;
- `APP_ENV` может использоваться как deployment env fallback.

## 6. Тесты

Добавить тесты на production guard.

Рекомендуемый файл:

`lib/env/production-guard.test.ts`

Покрыть сценарии:

1. development + demo-mode true: не падает;
2. production + demo-mode true: падает;
3. production + demo-mode false: не падает;
4. preview/staging + demo-mode true без override: падает;
5. preview/staging + demo-mode true с `ALLOW_DEMO_MODE_IN_PREVIEW=true`: не падает;
6. production + API error не возвращает demo payload.

## 7. Guardrails

Добавить CI-ready скрипт, например:

`guardrails:prod`

Он должен проверять хотя бы базовые вещи:

- нет production env example с `NEXT_PUBLIC_DEMO_MODE=true`;
- demo payload imports не используются напрямую в production routes;
- опасные `DEMO_*` fallback не обходят `IS_DEMO_MODE` / `resolveDemoMode()`.

Не нужен идеальный AST-анализ. Достаточно простого guardrail, который ловит явные опасные случаи.

## 8. Acceptance criteria

Пакет принимается, если:

- production build/startup падает при `NEXT_PUBLIC_DEMO_MODE=true`;
- development с `NEXT_PUBLIC_DEMO_MODE=true` работает;
- preview/staging demo-mode требует `ALLOW_DEMO_MODE_IN_PREVIEW=true`;
- production API error не подменяется demo payload;
- тесты production guard проходят;
- `.env.example` / docs обновлены;
- `package.json` содержит `guardrails:prod` или эквивалентный CI-ready скрипт;
- обычный build проходит при `NEXT_PUBLIC_DEMO_MODE=false`;
- build/guard test доказывает падение при production + demo-mode true.

## 9. Evidence от кодера

Кодер должен приложить:

- вывод frontend test suite;
- вывод production guard tests;
- вывод обычного build при demo-mode false;
- вывод negative check при production + demo-mode true;
- список изменённых файлов;
- короткое объяснение, где именно guard подключён.

## 10. Ограничения

Не переписывать архитектуру API.

Не трогать horary credit ledger.

Не трогать payment/YooKassa.

Не трогать natal frontend.

Не менять generated contracts вручную.

Не менять Pydantic schemas, если это не требуется для prod guard.

## 11. Следующий пакет

После этого пакета следующий логичный шаг:

`W-NATAL-FRONTEND-MVP`

Причина: natal calculation уже есть, но полноценного frontend-представления нет.

Отдельно описать в следующем ТЗ:

- где брать natal payload;
- как рендерить sections/blocks;
- как открыть `/readings/natal`;
- empty/loading/error states;
- mobile-first UI;
- tests.
