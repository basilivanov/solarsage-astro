# 03 TZ: frontend — pending promo token из sessionStorage в localStorage

- **Packet**: PROMO-PERSIST-03
- **Phase / Wave**: W-NAMED-PROMO-CAMPAIGN (расширение)
- **Modules**: M-TELEGRAM-START-PARAM

## Goal

Pending promo token переживает перезапуск Telegram webview: хранилище
`savePendingPromoToken` / `getPendingPromoToken` / `clearPendingPromoToken`
переводится с sessionStorage на localStorage. Имена функций, ключ
`PROMO_PENDING_SESSION_KEY` = `"__astro_pending_promo_token"` и сигнатуры
НЕ меняются (потребители не трогаем).

## Exact write scope

- `lib/telegram/start-param.ts` — блок STORAGE_HELPERS: sessionStorage →
  localStorage; синхронно обновить AI_HEADER / MODULE_CONTRACT /
  FUNCTION_CONTRACT-комментарии (сейчас там явно написано sessionStorage).
- `__tests__/lib/start-param.test.ts` — обновить моки/expect'ы под
  localStorage.

## Frozen / out-of-scope

- НЕ менять `components/promo/promo-campaign-gate.tsx`, `hooks/use-telegram-auth.ts`
  и прочих потребителей — публичный API модуля неизменен.
- НЕ менять CONSUMED_MARKER (он уже на localStorage) и CLASSIFIER.
- Backend не трогать.

## Must-preserve invariants

- Storage-функции никогда не throw (fail-closed catch → false/null).
- Валидация токена по PROMO_REGEX при save/get сохранена.
- Поведение promo gate и e2e-контракты не меняются.

## Verification

```bash
npx vitest run __tests__/lib/start-param.test.ts __tests__/components/PromoCampaignGate.test.tsx __tests__/hooks/useTelegramAuth.test.ts
```

## Expected evidence

- Список изменённых файлов, вывод vitest, `git diff --stat`.

## Escalation

Понадобилось менять потребителей или backend → стоп, доложить, ждать новый
packet.

## No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
