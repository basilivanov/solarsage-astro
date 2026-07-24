# Slice 10 — payment response contract wiring

## Цель

Добавить diagnostic contracts в уже schema-validated payment client, сохранив
строгие billing/error semantics.

## Разрешённые файлы

- `lib/api/payment.ts`
- `__tests__/api/payment-client.test.ts`

## Требования

1. Response contracts для schema-bearing success endpoints:
   - products -> `ProductsListResponseWireSchema.safeParse`;
   - subscription start -> `SubscriptionStartResponseWireSchema.safeParse`;
   - subscription status -> `SubscriptionStatusResponseWireSchema.safeParse`;
   - purchase start -> `PurchaseStartResponseWireSchema.safeParse`;
   - purchase status -> `PurchaseStatusResponseWireSchema.safeParse`.
2. `cancelSubscription` обычно пустой success response — не добавлять фиктивный
   JSON contract, только сохранить instrumentation.
3. Stable contract names/version `v1`, safe issue paths без values/messages.
4. Authoritative `.parse`, PaymentApiError/status/code mapping, RU copy, exact
   slugs/reason/purchase ID bodies/URLs не менять.
5. Обновить GRACE dependencies/emitted logs/function blocks, import держать в
   обычном import section, не внутри semantic block.

## Tests

Расширить существующий typed-client test:

- mock instrumentedFetch вместо global raw fetch;
- сохранить все текущие catalog/error/RU/schema assertions;
- проверить operations/routes/init всех 6 functions (включая cancel);
- пять validators принимают valid fixture и отвергают `{}`;
- cancel не имеет responseContract;
- dynamic purchase ID только в URL, template `{id}`;
- cleanup mocks/globals.

Проверка:

```bash
npx vitest run __tests__/api/payment-client.test.ts __tests__/billing/purchase-flow.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
