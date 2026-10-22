# MASTER TZ: Cache delivery hardening (WebView-proof релизы)

Дата: 2026-10-22. Исполнитель: кодер (tmux astro1) по срезам 01→02.
Ревьюер/коммит: архитектор. Контекст: анализ доставки релизов в Telegram WebView —
HTTP no-store не управляет WebView-снапшотами; главный механизм — версионированный
URL входа + проверка версии в приложении.

## Факты (проверено на проде 2026-10-22)

- `/` → `s-maxage=31536000`, `x-nextjs-cache: HIT` (`app/(grace)/page.tsx` — клиентский
  редиректор на /day/today, статический пререндер).
- `/today` — уже server `redirect()` (динамический, no-store) — образец для `/`.
- `/day/today` → `private, no-cache, no-store` ✓; `/_next/static/*` immutable ✓;
  `/telegram-web-app.js` max-age=0 ✓.
- `/api/*` — вообще БЕЗ Cache-Control (проверено на /api/health).
- Во фронт-бандле нет release sha: `apps/web/Dockerfile` кладёт RELEASE_SHA только в
  OCI-label; build-arg `RELEASE_SHA=$GITHUB_SHA` уже передаётся workflow всем образам.
- `middleware.ts` в корне нет.

## Карта срезов

| Срез | Содержание | Проверка |
|------|-----------|----------|
| 01 cache hygiene | `/` → server `redirect()`; API no-store middleware; `NEXT_PUBLIC_RELEASE_SHA` в web Dockerfile; компонент version-check + баннер «Обновить» | vitest + curl заголовков на деве + build |
| 02 versioned entry | `middleware.ts`: document GET на entry-HTML без актуального `?v=<sha>` → 307 на `?v=<sha>`; e2e гейт сохранения `#tgWebAppData` | vitest/playwright subset |

Кодер НЕ коммитит и НЕ пушит — коммит делает ревьюер.

## Критерии приёмки (глобальные)

- [ ] `/` отвечает 307 на /day/today БЕЗ `x-nextjs-cache: HIT` и `s-maxage=31536000`.
- [ ] Все ответы `/api/*` несут `Cache-Control: no-store`.
- [ ] Фронт-бандл знает свой sha: `NEXT_PUBLIC_RELEASE_SHA` инлайнится из build-arg.
- [ ] При мисматче версий — баннер `release-update-banner` с кнопкой; без мисматча/при unknown — ничего.
- [ ] Вход `/day/today` (document) → 307 → `/day/today?v=<sha>`, ровно один редирект; `#tgWebAppData` сохраняется и auth проходит (e2e).
- [ ] RSC/fetch-навигация НЕ редиректится (только document-запросы); API и статика не затронуты.
- [ ] vitest зелёный, build зелёный, CI зелёный; выкат через prod-deploy.
