# TZ: White-screen resilience — Today screen (случаи «замороженный webview» и «вечный скелет»)

Дата: 2026-10-23. Постановщик: архитектор (kimi, сессия dc). Исполнитель: кодер в tmux `astro` (cwd `/opt/solarsage-astro`).
Основание: инцидент 2026-10-22/23 (Настя, iPhone iOS 18.7) — два различённых по логам класса белых экранов:

- **Класс 1 (11:07)**: до nginx не дошло НИ ОДНОГО запроса — webview Telegram не начал навигацию (восстановленный/очищенный снапшот iOS). Кодом страницы не лечится: страница не исполняется. Лечится вероятностно (срез C2) и инструкцией пользователю.
- **Класс 2 (11:30)**: сервер отдал auth (200, 23 ms) и день (200, 218 ms), но ни одного `/api/_log` после — JS перестал исполняться/запрос повис, на экране остались скелеты. Это наш дефект: у первичной загрузки дня нет дедлайна.

---

## 1. Packet title
`today-white-screen-resilience` — дедлайн загрузки дня, детекторы воскрешения webview, милстоун-телеметрия, прогрев API; эксперимент no-store.

## 2. Phase / Wave
W-WHITE-SCREEN-RESILIENCE (инцидент-driven, вне плановой волны).

## 3. Modules
- `lib/grace/hooks/useTodayConvergence.ts` (M-HOOK-TODAY-CONVERGENCE)
- `components/today-convergence/today-screen.tsx` (скелет/ошибка)
- `lib/api/today-convergence.ts` (transport; при необходимости)
- новый модуль `lib/grace/resume-guard.ts` (детекторы resume)
- `hooks/use-telegram-auth.ts` (ТОЛЬКО добавление beacon после успешного auth; логика дедлайна 12 s не меняется)
- `lib/log/index.ts`, `lib/log/events.gen.ts` (registry событий)
- `apps/api/app/api/_log.py` (приём beacon), `apps/api/app/core/logging_events.py` (registry backend)
- `apps/api/app/main.py` (преwarm при старте)
- `__tests__/hooks/useTodayConvergence.test.ts` (+ новые тесты)
- `next.config.*` ИЛИ слой nginx dev — только для среза C2 (dev-only эксперимент)

## 4. Goal
1. Зависшая загрузка дня больше не показывает вечные немые скелеты: дедлайн 15 s → понятный экран ошибки с «Повторить» и жёсткой перезагрузкой.
2. Восстановленный из снапшота/замороженный webview детектируется при resume и уходит в жёсткую перезагрузку с защитой от reload-loop.
3. Каждая сессия оставляет милстоуны (`auth_ok → day_start → day_ok/day_timeout`), отправленные немедленно через sendBeacon — «смерть после auth» становится измеримой метрикой, а не анекдотом.
4. Первый auth после простоя API не стоит 3.1 s (прогрев пула asyncpg при старте).

## 5. Exact write scope
- `lib/grace/hooks/useTodayConvergence.ts`
- `lib/api/today-convergence.ts` (только если нужен параметр timeout в RequestOptions)
- `lib/grace/resume-guard.ts` (НОВЫЙ)
- `components/today-convergence/today-screen.tsx` (текст в скелете, кнопка hard reload в error)
- компонент экрана ошибки шелла, если error-UI живёт отдельно (найти по `screenState === "error"`)
- `hooks/use-telegram-auth.ts` (только точка beacon `auth_ok` + platform/version в лог)
- `lib/log/events.gen.ts`, `apps/api/app/core/logging_events.py` (additive: новые события)
- `apps/api/app/api/_log.py` (additive: приём одиночных beacon-конвертов, content-type Blob JSON)
- `apps/api/app/main.py` (startup-преwarm)
- `__tests__/hooks/useTodayConvergence.test.ts`, новые `__tests__/**` для resume-guard и beacon-утилиты
- `apps/api/tests/**` для _log beacon (additive)
- Срез C2: `next.config.*` (headers) — ТОЛЬКО для dev-проверки, в коммит включить с комментарием-флагом, в прод НЕ выкатывать (см. C2)
- `docs/agents/known-issues.md` (одна additive-запись о классе белых экранов после приёмки)

## 6. Frozen / out-of-scope
- Логика auth-дедлайна (`AUTH_TIMEOUT_MS`, 12 s), state-machine auth — не менять (только добавить вызов beacon после успеха).
- Семантика PENDING_POLLING (4 s / 120 s), IMPRESSION (once per snapshot), Retry-After countdown — не менять.
- `data-testid`, `data-screen-state`, `role`/`aria-*` — публичный UI-контракт: не переименовывать, не удалять; новые элементы добавлять по `docs/agents/ui-test-contract.md`.
- Никаких новых npm-зависимостей (sendBeacon, AbortController, location — всё платформенное).
- Не трогать `.worktrees/`, `e2e/mock-visual`, прод-конфиг nginx (`/etc/nginx/sites-enabled/astro.conf` — вне этого packet).
- Не рефакторить `lib/log/index.ts` батчер (beacon идёт отдельным путём, мимо батчера).
- Случай класса 1 (ноль запросов до сервера) кодом страницы НЕ чинить — только эксперимент C2 и запись в known-issues.

## 7. Must-preserve invariants
- Существующие тесты зелёные: `npx vitest run` без регрессий; `__tests__/hooks/useTodayConvergence.test.ts` может расширяться, но существующие кейсы не переписывать под новое поведение без необходимости.
- `useTodayConvergence`: day API никогда не вызывается, пока auth loading или завершился терминальной ошибкой (текущий invariant — сохранить).
- 401 → максимум один re-auth per mount; onboarding-ошибки → `/onboarding` (как сейчас).
- `/api/_log` продолжает принимать текущие батчи без изменений формата (beacon — additive-совместимый).
- GRACE canon репозитория: AI_HEADER, START_MODULE_CONTRACT/MAP с `owned_tests`, function contracts для нетривиальных публичных функций; логирование только через `logEvent`/`logStart`/`logSuccess`/`logFailure`; **новые события сначала регистрируются** в `lib/log/events.gen.ts` + `apps/api/app/core/logging_events.py`; `grace_control` не существует — не импортировать.
- Форматирование отчётов без LaTeX (см. AGENTS.md).

---

## Срезы (выполнять строго по порядку, коммит на каждый срез)

### СРЕЗ A — дедлайн + resume-детекторы + UI (ядро фикса)

**A1. Дедлайн загрузки дня 15 s** в `useTodayConvergence`:
- Константа `DAY_LOAD_TIMEOUT_MS = 15_000` (экспортируемая, как `AUTH_TIMEOUT_MS`).
- Армить таймер+AbortController при старте fetch в INITIAL_LOAD (после прохождения auth-gate); снимать при settle; при срабатывании — abort запроса, один **тихий авторетрай через 2 s**, при повторном фейле/таймауте → `screenState="error"` + событие `day.load_timeout`.
- Тот же дедлайн на follow-up GET внутри `refetch` (после Retry-After отсчёта).
- Таймеры/abort убираются в cleanup эффекта (существующий паттерн unmount/generation).
- Pending-поллинг (уже bounded 120 s) дедлайном НЕ накрывать.

**A2. Error-UI**: на экране ошибки дня две кнопки: «Повторить» (существующий `refetch`) и «Обновить полностью» (hard reload: `location.replace` текущего path + `?r=<timestamp>` cache-buster). `role="alert"` сохранить, новым кнопкам — `aria-label` и стабильные `data-testid` (`today-error-retry`, `today-error-reload`).

**A3. Живой скелет**: в `today-loading-skeleton` добавить видимый текст «Считаем день…» (и при pending — «Собираем разбор, ещё немного…» если состояние доступно). Сохранить `data-testid`, `role="status"`, `aria-live`; обновить `aria-label`.

**A4. Resume-Guard** — новый `lib/grace/resume-guard.ts` (client-only, без React-зависимостей внутри, подключение из экрана дня):
- Heartbeat: модульная `lastAliveTs`, обновление каждые 5 s.
- `pageshow` с `event.persisted === true` → если экран не в состоянии ready → hard reload.
- `visibilitychange → visible`: если `Date.now() − lastAliveTs > 30_000` → не ready → hard reload; ready → мягкий `refetch()`.
- **Защита от reload-loop (обязательно)**: счётчик авто-перезагрузок в `sessionStorage`, максимум 2 за 10 минут; дальше — не reload, а показ error-UI (событие `resume.reload_loop_suppressed`).
- События: `resume.snapshot_reload`, `resume.stale_reload` (registry сначала).

### СРЕЗ B — милстоун-телеметрия через sendBeacon

**B1.** Registry: добавить события (имена согласовать с существующим стилем `events.gen.ts`): `auth.ok` (если нет), `day.load_start`, `day.load_ok`, `day.load_timeout`, `resume.snapshot_reload`, `resume.stale_reload`, `app.pagehide_state`. Backend registry синхронно (`logging_events.py`).

**B2.** Beacon-утилита (например `lib/log/beacon.ts`): `navigator.sendBeacon("/api/_log", new Blob([JSON.stringify(envelope)], {type: "application/json"}))` — немедленно, мимо батчера. Точки вызова:
- после успешного `POST /api/auth/telegram` (в auth-хуке, без изменения его логики): milestone + `platform` и `version` из `initData` (`tgWebAppPlatform`, `tgWebAppVersion`);
- старт загрузки дня, успех дня, таймаут дня;
- срабатывания resume-guard;
- `pagehide`: последнее известное состояние экрана.
- Общий session/correlation id на время жизни страницы (crypto.randomUUID при первом beacon), чтобы милстоуны одной сессии склеивались.

**B3.** Backend `_log.py`: принимать одиночный конверт (не только батч) и `application/json` Blob-тело; additive, существующий батч-формат не ломать. Тест: beacon-конверт принимается, валидируется, пишется.

**B4.** Auth-лог на backend: обогатить успешный auth `platform`/`version` из initData (п.3 из разбора инцидента).

**B5.** В отчёт приложить SQL для метрики (ручной запуск): доля сессий с `day.load_start` без `day.load_ok` в течение 10 минут, по дням. Дашбордов не строить.

### СРЕЗ C — харденинг

**C1. Прогрев API при старте** (`apps/api/app/main.py`, рядом с W1-валидацией канона): на startup — установить пул asyncpg и выполнить `SELECT 1` (лог `api.prewarm_ok`/`api.prewarm_failed`). Проверка на деве: после `systemctl restart solarsage-api` первый `POST /api/auth/telegram` (initData через `scripts/generate-telegram-test-initdata.py`) < 300 ms.

**C2. Эксперимент `Cache-Control: no-store` на entry-HTML — ТОЛЬКО DEV.**
- Цель: сделать страницу неeligible для восстановления из page cache → повторное открытие мини-аппа делает реальную навигацию вместо замороженного кадра (класс 1).
- Реализация по выбору кодера (next.config headers для document-маршрутов — предпочтительно, слой единый), зафиксировать выбор в отчёте.
- Проверка на dev: 20–30 циклов «открыть → закрыть шторку → убить Telegram → открыть» на iOS-девайсе владельцем/кодером; критерий — каждое открытие даёт запросы в access-логе (навигация реальная).
- **В ПРОД НЕ ВЫКАТЫВАТЬ в этом packet.** Результат эксперимента — в отчёт; решение о проде за владельцем отдельным словом.

## 8. Verification (targeted-команды по срезам)
```bash
# A: unit
cd /opt/solarsage-astro && npx vitest run __tests__/hooks/useTodayConvergence.test.ts
# A: полный unit-gate
npx vitest run
# B: backend
cd /opt/solarsage-astro/apps/api && source .venv/bin/activate && python -m pytest tests/ -q
# сборка (обязательно перед дев-деплоем)
cd /opt/solarsage-astro && NODE_ENV=production npm run build
# дев-деплой + health (git_sha == HEAD)
systemctl restart solarsage-api solarsage-frontend solarsage-sidecar
curl -s https://dev.astro.vasiliy-ivanov.ru/api/health
```
Плюс sandbox-проверка состояний (`/sandbox/today?fixture=...`, скрин/CF-туннель по `docs/agents/artifact-publishing.md`): скелет с текстом, error-экран с двумя кнопками.

## 9. Expected evidence (в отчёте)
- Список файлов по каждому срезу + SHA коммитов (Conventional Commits по стилю `git log`).
- Выводы: vitest (targeted + полный), pytest, build, health git_sha.
- Скрин sandbox (loading/error состояния) через CF-туннель.
- Замер C1 (первый auth после рестарта, ms).
- C2: выбранный слой, результат 20–30 циклов на dev, явная пометка «в прод не выкачено».
- SQL метрики (B5) текстом.

## 10. Escalation rule
Стоп и доклад, если потребуется: менять логику auth-дедлайна, формат существующих _log-батчей, прод-конфиг nginx, semver-ломающие правки UI-контракта (testid), добавлять зависимость, или если C2 на dev покажет регрессии (двойные навигации, сломанный back). Дальше — новый packet.

## 11. Commit / deploy rule (ОТЛИЧАЕТСЯ от обычного — решение владельца 2026-10-23)
- Коммитить и пушить РАЗРЕШЕНО и требуется: по одному коммиту на срез (A, B, C), Conventional Commits, push в `main`.
- **Прод-деплой срезов A+B+C1 — разрешён владельцем сразу**: после зелёных проверок и дев-деплоя выполнить деплой ТОЛЬКО через skill `prod-deploy` (ручной uvicorn/npm запрещены, см. AGENTS.md). В прод уходит всё, КРОМЕ заголовка no-store из C2 (если реализовано в next.config — выкатить с выключенным флагом/исключить из прод-конфига; задокументировать механизм).
- После прод-деплоя: health + `git_sha` на `https://astro.vasiliy-ivanov.ru/api/health`, один реальный smoke (auth → day) и проверка, что милстоуны `day.load_start`/`day.load_ok` видны в `_log`.
