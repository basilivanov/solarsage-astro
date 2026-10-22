# TZ 07: paySandboxCheckout — починка под текущий UI ЮKassa sandbox

1. **Packet title**: SLICE-07 fix paySandboxCheckout for current YooKassa sandbox
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 07 (deploy unblock)
3. **Modules**: M-TEST-E2E-FIXTURES (`e2e/fixtures.ts`, функция `paySandboxCheckout`)
4. **Goal**: `payment-sandbox.spec.ts` и `natal-report.spec.ts` снова проходят
   sandbox-checkout на актуальном UI ЮKassa — локально на dev-стеке зелёные,
   затем готовы к deploy-гейту real-e2e.

## Контекст (доказано артефактами GH run 39737371864)

- Деплой auth-фикса заблокирован real-e2e: обе спеки падают в `paySandboxCheckout`
  (`e2e/fixtures.ts:521`): popup открывается, но за 12 с не появляется ни карточная
  форма, ни chooser (`[data-qa="bankcard-show-other-cards-payment-option"]` / текст
  «Новая карта»). Один ретрай — то же место ⇒ устойчивый дрейф UI sandbox ЮKassa,
  не флейка. Наше приложение при этом работает корректно (скриншот: «Ждём
  подтверждения оплаты»), auth-спеки все зелёные.
- Видео прогона: checkout-флоу доходит до клика «Подписка» и ожидания подтверждения —
  значит платёж создаётся, проблема именно в содержимом popup checkout-страницы.

## 5. Exact write scope

- `e2e/fixtures.ts` (только `paySandboxCheckout` и его прямые helpers/селекторы)

## 6. Frozen / out-of-scope

- Любой product/runtime код (`app/`, `components/`, `lib/`, `apps/api/`) — запрещён.
- Другие e2e-спеки — не трогать.
- Секреты не печатать (ни .env, ни тела ответов ЮKassa с токенами платежа).

## 7. Must-preserve invariants

- Хелпер остаётся fail-closed: никаких blind-fill, без partial payment attempts,
  без бесконечных ожиданий; границы попыток/таймауты сохранить.
- Платежи — только test-shop ЮKassa sandbox; реальных денег нет.
- Локальный прогон не оставляет nohup-сиротов (dev-server после проверки убить).

## Техническое задание

1. **Воспроизвести локально**: прогнать `e2e/payment-sandbox.spec.ts` на dev-стеке
   (`E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/payment-sandbox.spec.ts --project=chromium`;
   dev-server `npx next dev --webpack -p 3000`, backend :8000 уже работает;
   initData — штатный генератор). Проверить наличие нужных env-ключей ТОЛЬКО по именам
   (`grep -oE '^[A-Z_0-9]+=' .env | grep -iE 'yookassa|telegram|openrouter|geonames'`),
   значения не выводить.
2. **Снять улику**: в точке падения временно (не коммитить) сдампить
   `popup.url()`, `popup.content()` и скриншот popup в /tmp — понять, что сейчас
   рендерит sandbox checkout: новая DOM-структура формы, interstitial, капча, ошибка
   магазина или редирект. Зафиксировать корневую причину в отчёте (без секретов).
3. **Починить** `paySandboxCheckout` под текущую страницу: обновить селекторы формы/
   chooser и/или шаги флоу (например новый interstitial-шаг), сохранив fail-closed
   семантику и верификацию полей перед оплатой.
4. **Проверить**: `payment-sandbox.spec.ts` (оба теста) и `natal-report.spec.ts`
   зелёные локально по одному чистому прогону каждой. Убить dev-server.
5. Отчёт: корневая причина (что изменилось в checkout), diff fixtures.ts, вывод
   двух прогонов. Временные дампы из /tmp не коммитить.

## 8. Verification (одна команда)

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/payment-sandbox.spec.ts e2e/natal-report.spec.ts --project=chromium
```

## 9. Expected evidence

diff `e2e/fixtures.ts`; корневая причина; обе спеки passed локально; подтверждение,
что :3000 свободен после прогона.

## 10. Escalation rule

Если checkout магазина отвечает ошибкой конфигурации (магазин/ключи), а не новым UI —
стоп, доложить: это уровень владельца/провайдера, не test-fix. Если починка требует
правок вне `e2e/fixtures.ts` — стоп, доложить.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
