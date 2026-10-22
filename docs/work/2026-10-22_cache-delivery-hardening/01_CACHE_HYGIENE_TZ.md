# TZ 01: Cache hygiene + release plumbing + баннер обновления

1. **Packet title**: SLICE-01 cache hygiene + release version plumbing
2. **Phase / Wave**: W-CACHE-DELIVERY-HARDENING (2026-10-22), срез 01/02
3. **Modules**: M-GRACE-LAYOUT/`app/(grace)/page.tsx`, `apps/api/app/main.py`,
   `apps/web/Dockerfile`, новый M-RELEASE-VERSION-CHECK (`components/release-version-check.tsx`)
4. **Goal**: `/` перестаёт быть годовым статическим кэшем; все `/api/*` отдают
   `Cache-Control: no-store`; фронт-бандл знает свой release sha; при мисматче версий
   пользователь видит баннер «Доступна новая версия» с кнопкой обновления.

## 5. Exact write scope

- `app/(grace)/page.tsx` — server-side redirect вместо клиентского.
- `apps/api/app/main.py` (или `apps/api/app/middleware/`, если там уместнее по структуре) — no-store middleware.
- `apps/web/Dockerfile` — `NEXT_PUBLIC_RELEASE_SHA` в builder stage.
- `components/release-version-check.tsx` — НОВЫЙ.
- `app/layout.tsx` — монтирование компонента (одна строка внутри TelegramProvider).
- `__tests__/components/release-version-check.test.tsx` — НОВЫЙ.
- `grace/frontend.paths` — добавить `components/release-version-check.tsx` (и middleware.ts в срезе 02, НЕ здесь).
- Один backend-тест на заголовок (расширить ближайший health/auth тест по месту).

## 6. Frozen / out-of-scope

- `middleware.ts` — срез 02, здесь НЕ создавать.
- `app/(grace)/today/page.tsx` — уже server redirect, не трогать.
- nginx-конфиги, infra, workflow-файлы — не трогать (build-arg RELEASE_SHA уже передаётся).
- Любая другая страница/компонент.

## 7. Must-preserve invariants

- Поведение входа: `/` → /day/today сохраняется; редирект серверный (307/308 от Next).
- API-контракты и тела ответов не меняются — только добавление заголовка.
- Баннер не блокирует контент и не показывается при совпадении версий/при неизвестном sha.
- GRACE-маркеры: новый компонент — полный набор; обновить contract'ы затронутых файлов.
- Секреты не трогаем; sha не является секретом (уже в /api/health).

## Техническое задание

1. **`app/(grace)/page.tsx`**: заменить клиентский редиректор на серверный, по образцу
   `app/(grace)/today/page.tsx` (`import { redirect } from "next/navigation"; redirect("/day/today")`).
   Клиентский logger-вызов убрать. Обновить AI_HEADER/contract (динамический server redirect).
   Результат: `/` становится ƒ (dynamic), уходит `x-nextjs-cache: HIT` + `s-maxage=31536000`.
2. **API no-store**: middleware, добавляющий `Cache-Control: no-store` на ВСЕ ответы
   приложения (весь app — это /api/*). Разместить рядом с CorrelationMiddleware,
   после него по курсу ответа. Backend-тест: GET /api/health → заголовок no-store.
3. **`apps/web/Dockerfile`**: в builder stage добавить `NEXT_PUBLIC_RELEASE_SHA=${RELEASE_SHA}`
   в ENV (ARG RELEASE_SHA объявить ДО использования). Больше ничего в Dockerfile не менять.
4. **`components/release-version-check.tsx`** (client):
   - build sha = `process.env.NEXT_PUBLIC_RELEASE_SHA`; пусто/`unknown` → no-op.
   - Серверный sha: `GET /api/health` → `release_sha`; проверка на mount И на
     `visibilitychange` (когда document снова visible — кейс resume из WebView-снапшота).
   - Мисматч → фиксированный внизу баннер: `data-testid="release-update-banner"`,
     `role="status"`, текст «Доступна новая версия» + кнопка «Обновить»
     `data-testid="release-update-reload"` → `location.reload()`. Не auto-reload.
   - Ошибки fetch — молча игнорировать (не ломать UX).
5. **`app/layout.tsx`**: смонтировать `<ReleaseVersionCheck />` внутри TelegramProvider
   (рядом с FrontendErrorCapture). Contract layout'а обновить.
6. **Тесты** (`__tests__/components/release-version-check.test.tsx`):
   a. мисматч sha → баннер виден, клик вызывает reload (mock location);
   b. совпадение → баннера нет; c. build sha пуст/unknown → fetch не вызывается;
   d. fetch упал → баннера нет, ошибок наружу.

## 8. Verification

```bash
npx vitest run __tests__/components/release-version-check.test.tsx && cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "health or auth" && cd /opt/solarsage-astro && NODE_ENV=production npm run build 2>&1 | tail -5
```

Плюс ручная проверка на деве (после build + restart): `curl -sI https://dev.astro.vasiliy-ivanov.ru/` → 307, нет `s-maxage=31536000`; `curl -sD- -o /dev/null https://dev.astro.vasiliy-ivanov.ru/api/health | grep -i cache-control` → no-store. (Рестарт dev-сервисов входит в задачу.)

## 9. Expected evidence

diff по файлам п.5; вывод verification; вывод curl-проверок на деве; подтверждение,
что build показывает `/` как ƒ (dynamic).

## 10. Escalation rule

Если server redirect ломает e2e/пререндеры или no-store требует правок nginx — стоп,
доложить, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
