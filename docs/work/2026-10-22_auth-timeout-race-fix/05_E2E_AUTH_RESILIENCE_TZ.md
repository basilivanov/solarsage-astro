# TZ 05: e2e auth-resilience (mock-уровень)

1. **Packet title**: SLICE-05 e2e auth resilience spec
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 05/05
3. **Modules**: e2e harness (новый spec)
4. **Goal**: end-to-end доказательство трёх сценариев устойчивости входа на уровне
   публичного DOM-контракта: медленный auth, заблокированный telegram.org, ошибка + retry.

## 5. Exact write scope

- `e2e/auth-resilience.spec.ts` — НОВЫЙ.

При необходимости читать (не править): `e2e/fixtures.ts`, `e2e/hydration-guard.spec.ts`,
`e2e/mock-visual/` (паттерны route interception).

## 6. Frozen / out-of-scope

- Любой product/runtime код — только тест. Если сценарий не воспроизводится без правки
  рантайма — стоп, доложить (значит срезы 01–04 приняты неверно).

## 7. Must-preserve invariants

- Mock/fixture e2e — только test-only слой (`page.route`), по канону UI contract.
- Тест опирается на публичный DOM: `data-testid` `auth-loading` / `auth-error` / `auth-retry`,
  `today-screen`/`data-screen-state`; не на CSS-классы и тексты LLM.
- GRACE-маркеры в файле spec (AI_HEADER, MODULE_CONTRACT, MODULE_MAP с owned_tests: self).

## Техническое задание

Playwright, dev-server `http://localhost:3000` (поднять `npx next dev --webpack -p 3000`
перед прогоном, после — убить; nohup-сирот не оставлять). Инъекция
`window.Telegram.WebApp` stub с initData через `addInitScript` (паттерн `e2e/fixtures.ts`),
дальше `page.route` на `/api/auth/telegram`:

1. **Медленный auth**: задержка ответа 4.5 с (при бюджете 12 с) → `auth-error` НЕ
   появляется, приложение доходит до контента (ждать `auth-loading` исчезнет).
2. **Заблокированный telegram.org**: `page.route('https://telegram.org/**', abort)` →
   вход всё равно проходит (SDK self-hosted с `/telegram-web-app.js`); auth POST ушёл,
   контент загрузился.
3. **Ошибка + retry**: первый POST → 500, → виден `auth-error` и кнопка `auth-retry`;
   клик по `auth-retry` (route переключён на 200) → `auth-error` исчезает, контент грузится.
   Дополнительно: в сценарии 3 убедиться, что экран ошибки виден и когда stub
   `inTelegram=false` (второй прогон с пустым initData и заблокированным dev-auth —
   если это требует хитростей, достаточно основного прогона; упростить, не расширять).

В каждом сценарии проверить отсутствие «пустого окна»: либо `auth-loading`, либо
`auth-error`, либо контент — всегда что-то одно видимо.

## 8. Verification (одна команда)

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/auth-resilience.spec.ts
```

## 9. Expected evidence

Файл spec; вывод playwright (3 passed); подтверждение, что dev-server остановлен.

## 10. Escalation rule

Нужна правка рантайма/фикстур ядра e2e → стоп, доложить, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
