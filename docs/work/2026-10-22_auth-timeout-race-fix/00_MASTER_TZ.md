# MASTER TZ: Auth timeout race fix (iOS Telegram Mini App white screen)

Дата: 2026-10-22. Исполнитель: кодер (Codex, tmux astro1) по срезам 01→05.
Ревьюер/коммит: архитектор (kimi). Связанное ТЗ: `docs/work/2026-09-27_auth_timeout_race_TZ.md`
(§2.1, §2.3, §2.4 — реализуем здесь; §2.2 backend warmup и §2.5 natal promo — ВНЕ скоупа).

## 1. Инцидент

Пользователь @ani96O (tg 327427409) на iOS: Mini App открывается, `POST /api/auth/telegram → 200`,
далее клиент не шлёт НИ одного запроса (`/api/day/today`, `/api/referral`, `/api/_log` — тишина),
вечный спиннер/пустое окно. 5 сессий 19–21.10, воспроизводится стабильно. Android и Chromium —
здоровы. В nginx — 499 на `GET /api/day/today` только с iPhone-UA (~1.03–1.08 с).

## 2. Корневые причины (подтверждены чтением кода 2026-10-22)

1. `hooks/use-telegram-auth.ts:77-80` — ранний `return`, если SDK Telegram не загрузился:
   таймер не ставится вообще, `isLoading=true` навсегда. Это и есть случай Насти.
2. `hooks/use-telegram-auth.ts:96-103` — таймаут 5000 мс ставится только внутри
   `authenticate()`, т.е. после появления SDK.
3. `hooks/use-telegram-auth.ts:219,302` — `clearTimeout` после `await sleep(500)` и после
   referral-claim fetch → эффективный бюджет ~4.5 с, гонка SUCCESS-then-TIMEOUT.
4. Два независимых экземпляра `useTelegramAuth()` (`app/(grace)/layout.tsx:82` и
   `lib/grace/hooks/useTodayConvergence.ts:88`) → дубли POST /api/auth/telegram
   (40 за сессию на Android) и гейтинг данных дня «второй» авторизацией.
5. `components/telegram-provider.tsx:123-174` — `inTelegram` вычисляется один раз по
   `!!webApp.initData` в момент резолва SDK; на iOS initData может появиться позже →
   `inTelegram=false` навсегда.
6. `app/(grace)/layout.tsx:99` — `if (error && inTelegram)` подавляет экран ошибки при
   `inTelegram=false` → пустое окно без текста и без ретрая.
7. Нет fallback на `#tgWebAppData` в URL (Telegram кладёт initData туда всегда); SDK
   грузится с `https://telegram.org/js/telegram-web-app.js` — блокировка telegram.org
   ломает вход.

## 3. Дизайн-решение (архитектор)

- **Единое auth-состояние** — module-level singleton store в `hooks/use-telegram-auth.ts`
  (useSyncExternalStore), НЕ React provider: diff минимален, не трогаем root layout,
  существующие вызовы `useTelegramAuth()` автоматически начинают читать общее состояние.
  Один POST, один таймер, один источник истины для layout и хуков данных.
- **initData без SDK**: `resolveTelegramInitData()` = `webApp?.initData || tgWebAppData
  из location.hash`. Если initData есть — авторизуемся немедленно, не дожидаясь SDK.
- **Дедлайн 12 с** ставится при первой попытке auth (до проверки SDK); `clearTimeout`
  сразу по приходу ответа fetch, до любых sleep; `retry()` — полный перезапуск с новым таймером.
- **Самохостинг SDK**: `public/telegram-web-app.js` (vendored 2026-10-22, 119731 B),
  провайдер грузит `/telegram-web-app.js`. CSP в nginx/next.config отсутствует — безопасно.
- **auth_attempt_id** (uuid per attempt) — фронт шлёт в теле POST, бэкенд прикладывает к
  `auth.tg_login_succeeded/failed` и bind в log context (additive kwarg в `bind_log_context`).

## 4. Карта срезов

| Срез | Файлы | Проверка |
|------|-------|----------|
| 01 provider+initData | `components/telegram-provider.tsx`, `lib/telegram/init-data.ts` (new), `public/telegram-web-app.js` (new), `__tests__/components/telegram-provider.test.tsx` (new) | vitest двух файлов |
| 02 shared auth + retry UI | `hooks/use-telegram-auth.ts`, `app/(grace)/layout.tsx`, `__tests__/hooks/useTelegramAuth.test.ts` | vitest трёх файлов |
| 03 today convergence | `lib/grace/hooks/useTodayConvergence.ts`, `__tests__/hooks/useTodayConvergence.test.ts` | vitest двух файлов |
| 04 auth_attempt_id | `hooks/use-telegram-auth.ts`, `apps/api/app/schemas/auth.py`, `apps/api/app/api/auth.py`, `apps/api/app/core/logging.py`, backend test | pytest -k auth + grace_lint |
| 05 e2e | `e2e/auth-resilience.spec.ts` (new) | playwright one spec |

Срезы строго последовательно. Кодер НЕ коммитит и НЕ пушит — коммит делает ревьюер.

## 5. Глобальные критерии приёмки

- [ ] iOS-кейс: auth возможен только по `#tgWebAppData` без загруженного SDK.
- [ ] Нет вечного isLoading: при любой ветке через ≤12 с — конечное состояние.
- [ ] Ответ до дедлайна никогда не превращается в `Authentication timeout`.
- [ ] Один POST /api/auth/telegram на сессию (не два экземпляра).
- [ ] Экран `auth-error` показывается независимо от `inTelegram`, с рабочей кнопкой `auth-retry`.
- [ ] TIMEOUT-лог содержит `timeout_budget_ms`, `elapsed_ms`, attempt; бэкенд-логи находят попытку по `auth_attempt_id`.
- [ ] `npx vitest run` зелёный; `pytest` зелёный; `python3 scripts/grace_lint.py apps/api/app` PASS; прод-выкат через prod-deploy после дев-проверки.

## 6. Вне скоупа

- Backend pool warmup (ТЗ 2026-09-27 §2.2) — отдельной задачей.
- Natal promo «entitled, ждёт генерации» (§2.5) — отдельной задачей.
- Редизайн auth-error, смена auth-контракта (кроме additive `auth_attempt_id`).
