# TZ 02: Versioned entry — middleware redirect на ?v=<release_sha>

1. **Packet title**: SLICE-02 versioned entry URL via middleware
2. **Phase / Wave**: W-CACHE-DELIVERY-HARDENING (2026-10-22), срез 02/02
3. **Modules**: новый `middleware.ts` (root), e2e
4. **Goal**: любой document-вход на app-страницу без актуального `?v=<release_sha>`
   получает 307 на URL с `?v=<release_sha>` — после деплоя WebView не может открыть
   документ по протухшему кэшированному URL; `#tgWebAppData` при этом сохраняется
   (приёмочный гейт).

## 5. Exact write scope

- `middleware.ts` — НОВЫЙ (корень репо).
- `e2e/versioned-entry.spec.ts` — НОВЫЙ.
- `grace/frontend.paths` — добавить `middleware.ts`.
- При необходимости — точечная правка URL-assertions в существующих e2e (только если
  упали из-за `?v=`; сначала доказать падение).

## 6. Frozen / out-of-scope

- Файлы среза 01 (уже приняты: page redirect, API no-store, Dockerfile, баннер) — не трогать.
- nginx/infra/workflow — не трогать.
- Product-код страниц — не трогать.

## 7. Must-preserve invariants

- Редирект ТОЛЬКО для document-запросов (`sec-fetch-dest: document`; fallback:
  `accept: text/html` без RSC-заголовков). RSC/fetch-навигация, `_next/*`, `/api/*`,
  статика, `/telegram-web-app.js` — НЕ редиректятся.
- Ровно один редирект: при `?v` === текущему sha — пустить без редиректа (loop-guard).
- sha пуст/`unknown` (dev, preview-сборки) → middleware полностью no-op (иначе
  сломаются e2e-харнессы).
- Редирект-ответ — 307 с `Cache-Control: no-store`.
- GRACE-маркеры в middleware.ts (AI_HEADER, MODULE_CONTRACT, MODULE_MAP, owned_tests).

## Техническое задание

1. **`middleware.ts`**: matcher — страницы приложения (исключить `api`, `_next/static`,
   `_next/image`, `_next/data`, `telegram-web-app.js`, favicon/icon/manifest, файлы с
   расширениями). Внутри: `NEXT_PUBLIC_RELEASE_SHA` пуст/unknown → next; document-запрос
   (см. инварианты) и `searchParams.get('v') !== sha` → `url.searchParams.set('v', sha)`,
   `NextResponse.redirect(url, 307)` с no-store; иначе next.
   Hash серверу недоступен — браузер прикрепляет fragment к 3xx сам (проверяется гейтом).
2. **`e2e/versioned-entry.spec.ts`** (mock-уровень, паттерн auth-resilience):
   dev-server поднять с `NEXT_PUBLIC_RELEASE_SHA=e2e-test-sha` (вар начитывается на
   старте сервера), после прогона — убить.
   a. `goto /day/today#tgWebAppData=<encoded initData>` → финальный URL содержит
      `v=e2e-test-sha` И `#tgWebAppData` нетронут; auth POST ушёл с initData из hash;
      `today-screen` ready. Ровно один redirect (считать через request-chain/response
      listener).
   b. повторный document-вход на `/day/today?v=e2e-test-sha` → redirect'а нет (loop-guard).
   c. RSC-запрос (client-side переход на /day/<date> после загрузки) → 200 без redirect
      (проверить, что веб-навигация внутри приложения не ломается).
3. Прогнать `e2e/auth-resilience.spec.ts` + `e2e/versioned-entry.spec.ts` — все зелёные
   (auth-resilience гонять с тем же sha-env, чтобы middleware был активен).

## 8. Verification (одна команда)

```bash
NEXT_PUBLIC_RELEASE_SHA=e2e-test-sha npx next dev --webpack -p 3000 & sleep 8; E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/versioned-entry.spec.ts e2e/auth-resilience.spec.ts --project=chromium; kill %1
```

## 9. Expected evidence

middleware.ts + spec; вывод verification (оба spec passed); подтверждение, что :3000
остановлен; заметка о поведении hash в Chromium (сохранён ли fragment после 307 —
видно по тесту a).

## 10. Escalation rule

Если fragment теряется в Chromium при 307 — стоп, доложить (переходим на клиентский
вариант редиректа). Если нужны правки product-кода — стоп, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
