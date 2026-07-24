# Slice 09 — validated frontend promo API client

## Локальная цель

Добавить browser API facade для preview/redeem поверх generated contracts и
`instrumentedFetch`. Без UI, storage и routing.

## Preconditions

Promo generated type/runtime exports и HTTP endpoints приняты.

## Разрешённые файлы

- новый `lib/api/promo.ts`;
- новый `__tests__/api/promo-client.test.ts`.

## Public API

```ts
previewPromo(token: string): Promise<PromoPreviewResponse>
redeemPromo(token: string): Promise<PromoRedeemResponse>

class PromoApiError extends Error {
  status: number
  code: PromoErrorCode | "UNKNOWN"
}
```

Token argument живёт только до сериализации request body. Не сохранять его в
class fields, Error, module cache, operation ID или logs.

## Network contract

Использовать `instrumentedFetch`:

```text
operation=promo.preview, routeTemplate=POST /api/promo/preview
operation=promo.redeem,  routeTemplate=POST /api/promo/redeem
credentials=include, JSON content type
```

Wrapper уже запрещает logging URL/body/headers. Не добавлять собственный
logger вокруг request.

Success responses валидируются generated:

```text
PromoPreviewResponseWireSchema
PromoRedeemResponseWireSchema
```

Non-ok body parsed once, `detail` validated/normalized against generated
`PromoErrorDetail` when possible. Unknown/invalid body -> safe generic
`PromoApiError(status,"UNKNOWN","Не удалось проверить промокод.")`.

Client сохраняет typed `ALREADY_REDEEMED`; он не превращает его сам в success.
Gate slice использует этот code как recovered completed outcome и выполняет
clear+reload. Такое разделение сохраняет честный HTTP contract.

Не включать raw backend response, token или JSON body в Error message/cause.

## Tests

- correct URLs/method/credentials and body on the mocked fetch boundary;
- neither log mocks nor thrown errors include token;
- valid preview/redeem parsed;
- invalid success response triggers existing contract failure behavior;
- every stable backend code preserved;
- malformed/non-JSON error becomes UNKNOWN safe error;
- network exception propagates without decorating it with token.

## Targeted verification

```bash
npx vitest run __tests__/api/promo-client.test.ts
```

## Out of scope

Storage, start-param, sheet, onboarding, `window.location.reload`, Nginx/CLI.
Не коммитить и не пушить.
