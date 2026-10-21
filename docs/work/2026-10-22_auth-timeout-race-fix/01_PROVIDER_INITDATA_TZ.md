# TZ 01: Telegram provider — initData fallback, late-initData, self-hosted SDK

1. **Packet title**: SLICE-01 telegram-provider initData hardening
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 01/05
3. **Modules**: M-TELEGRAM-PROVIDER (`components/telegram-provider.tsx`),
   новый M-TELEGRAM-INIT-DATA (`lib/telegram/init-data.ts`)
4. **Goal**: `inTelegram` и initData больше не зависят от одного момента загрузки SDK:
   initData берётся из `#tgWebAppData` в URL как fallback, поздно появившийся
   `webApp.initData` пересчитывает `inTelegram`, SDK грузится с нашего origin.

## 5. Exact write scope (только эти файлы)

- `lib/telegram/init-data.ts` — НОВЫЙ.
- `components/telegram-provider.tsx` — правка.
- `public/telegram-web-app.js` — НОВЫЙ (vendored SDK).
- `__tests__/components/telegram-provider.test.tsx` — НОВЫЙ.

## 6. Frozen / out-of-scope

- `hooks/use-telegram-auth.ts`, `app/(grace)/layout.tsx`, `lib/grace/hooks/useTodayConvergence.ts` — срезы 02/03, НЕ трогать.
- `components/telegram-init.tsx` — не трогать.
- `grace/frontend.paths` — не трогать (lib/telegram вне whitelist, оставляем как есть).
- Никаких правок бэкенда.

## 7. Must-preserve invariants

- SSR/гидратация: на сервере и при первом клиентском рендере `loaded=false, webApp=null, inTelegram=false` (провайдер сейчас hydration-safe — сохранить).
- Предустановленный `window.Telegram.WebApp` (e2e `addInitScript`) — детектится без загрузки скрипта, как сейчас.
- `script.id = 'telegram-web-app-sdk'`, safety timeout 10 с → `loaded=true` даже если скрипт не загрузился.
- GRACE-маркеры: новый `lib/telegram/init-data.ts` — полный набор (AI_HEADER, MODULE_CONTRACT, MODULE_MAP с owned_tests); обновить contract/map провайдера (emitted_logs/dependencies) под новое поведение.
- Нет логирования raw initData.

## Техническое задание

1. **`lib/telegram/init-data.ts`** (новый):
   - `parseTgWebAppDataFromHash(): string` — читает `window.location.hash`, достаёт
     параметр `tgWebAppData` (hash вида `#tgWebAppData=<urlencoded>&...`), возвращает
     декодированную строку initData или `''`. SSR-safe (нет window → `''`).
   - `resolveTelegramInitData(webApp): string` — `webApp?.initData || parseTgWebAppDataFromHash()`.
   - Pure functions, легко тестируются; без логов initData.
2. **`components/telegram-provider.tsx`**:
   - `hasTelegramContext` заменить на проверку через `resolveTelegramInitData(webApp)` (учитывает hash fallback).
   - После резолва SDK: если `webApp` есть, но initData пуст — повторные проверки на 250/500/1000/2000 мс; при появлении initData (или наличии hash fallback) обновить state (`inTelegram` пересчитывается каждый раз, не «один раз навсегда»). Таймеры чистить в cleanup.
   - `script.src` → `/telegram-web-app.js` (self-hosted). Комментарий: vendored 2026-10-22 с telegram.org, обновлять осознанно.
3. **`public/telegram-web-app.js`**: `curl -sS https://telegram.org/js/telegram-web-app.js -o public/telegram-web-app.js` (уже проверено: 200, 119731 B). Первой строкой добавить комментарий `/* Vendored from https://telegram.org/js/telegram-web-app.js on 2026-10-22. Do not edit; re-vendor consciously. */`.
4. **Тесты** `__tests__/components/telegram-provider.test.tsx` (jsdom, RTL):
   - `tgWebAppData` в hash без `window.Telegram` → после загрузки скрипта `inTelegram=true` (hash fallback работает даже когда SDK не выставил initData).
   - SDK резолвится с пустым initData, затем initData появляется → `inTelegram` flips to true (fake timers для 250/500/... серии).
   - Нет `window.Telegram`, нет hash, скрипт error/timeout → `loaded=true`, `inTelegram=false`.
   - src скрипта = `/telegram-web-app.js` (не telegram.org).

## 8. Verification (одна команда)

```bash
npx vitest run __tests__/components/telegram-provider.test.tsx __tests__/hooks/useTelegramAuth.test.ts
```

Оба файла зелёные (второй — регресс, он мокает провайдер и не должен сломаться).

## 9. Expected evidence

- diff по 4 файлам; вывод verification-команды (PASS); подтверждение размера vendored файла (`wc -c public/telegram-web-app.js` ≈ 119731 + строка комментария).

## 10. Escalation rule

Нужен файл вне списка п.5 или меняется публичный контракт провайдера (имена полей контекста) → стоп, доложить ревьюеру, ждать новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
