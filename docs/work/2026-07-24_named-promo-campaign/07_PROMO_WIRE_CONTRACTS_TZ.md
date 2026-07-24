# Slice 07 — Pydantic/OpenAPI/generated promo wire contracts

## Локальная цель

Добавить единственный wire source of truth и generated frontend schemas без
HTTP route/client/UI behavior.

## Preconditions

Promo service internal dataclasses приняты, но frontend не импортирует их.

## Разрешённые файлы

- новый `apps/api/app/schemas/promo.py`;
- `apps/api/app/schemas/contract_registry.py`;
- generated `packages/contracts/openapi.json`;
- generated `packages/contracts/_generated.ts`;
- generated `packages/contracts/_generated.zod.ts`;
- `packages/contracts/index.ts`;
- `packages/contracts/runtime.ts`;
- узкие contract registry/runtime tests.

Generated artifacts изменять только командой generator, не вручную.

## Pydantic models

Все модели наследуют `CamelModel`, `extra=forbid` по repo contract:

```text
PromoCodeRequest
  token: SecretStr, writeOnly/password schema; no min/max/pattern validators

PromoOffer
  display_name: str
  access_days: int
  bonus_credits: int
  unlock_natal: bool

PromoPreviewResponse
  offer: PromoOffer
  profile_complete: bool

PromoGrantSummary
  access_starts_at: date | None
  access_until: date | None
  bonus_credits: int
  bonus_credits_expires_at: datetime | None
  natal_unlocked: bool
  natal_already_owned: bool

PromoRedeemResponse
  status: Literal["redeemed"]
  offer: PromoOffer
  grants: PromoGrantSummary

PromoErrorDetail
  code: Literal[
    INVALID_CODE, CAMPAIGN_EXPIRED, CAMPAIGN_FULL,
    ALREADY_REDEEMED, PROFILE_INCOMPLETE, RATE_LIMITED
  ]
  message: str
```

Add field bounds consistent with DB for safe response/admin values, but do not
add `min_length`, `max_length` or `pattern` to the token field. Pydantic 2
validation errors include raw `input`; exact regex/length validation remains
domain service-owned so invalid string maps to stable `INVALID_CODE`, not
FastAPI 422. Malformed JSON/type redaction belongs to the HTTP slice.

## Registry/generation

- Add public roots alphabetically to `PUBLIC_CONTRACT_ROOTS`.
- Run `pnpm contracts:generate`.
- Export promo types from `packages/contracts/index.ts`.
- Export runtime schemas needed by client from `packages/contracts/runtime.ts`:
  preview response, redeem response and error detail. Request runtime schema is
  optional; token must never be parsed/logged for diagnostics.
- No hand-written duplicate TypeScript/Zod wire shapes.

## Tests

- contract registry remains sorted and valid;
- `PromoCodeRequest` JSON schema marks token writeOnly/password, never has an
  example/default token and не содержит min/max/pattern constraints;
- generated Zod accepts canonical response and rejects missing/wrong fields;
- generated type aliases compile through public barrel;
- generation is byte-idempotent.

## Targeted verification

```bash
pnpm contracts:generate && pnpm contracts:check
```

## Out of scope

No router mounting, service calls, API fetch, sheet or CLI. Не коммитить и не
пушить.
