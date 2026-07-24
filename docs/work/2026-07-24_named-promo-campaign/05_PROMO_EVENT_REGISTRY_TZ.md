# Slice 05 — closed promo event registry

## Локальная цель

Открыть минимальный typed logging contract до появления promo emitters. Только
registry parity; не добавлять business code или ложные события.

## Разрешённые файлы

- `grace/canon/observability.xml`;
- `apps/api/app/core/logging_events.py`;
- `lib/log/events.gen.ts`.

## События

Добавить owner/wave `W-PROMO-CAMPAIGN`:

```text
promo.offer_viewed
promo.redemption_succeeded
promo.redemption_rejected
promo.redemption_failed
promo.campaign_created
promo.campaign_disabled
```

Safe payload vocabulary документируется в canon:

```text
campaign_id
error_code
access_days
bonus_credits
unlock_natal
natal_already_owned
redemptions_used
max_redemptions
error_kind
```

Explicit forbidden fields:

```text
token, start_param, code_hash, display_name, initData,
request/response body, Telegram ID, birth/profile data
```

`promo.offer_viewed` — frontend sheet actually shown, не backend preview request.
`promo.redemption_rejected` — only stable error code, raw exception/message не
нужны. `promo.redemption_failed` — unexpected rollback/500, safe exception type
only; success event разрешён только после commit. Admin events never include
campaign name/hash/token.

## Acceptance

- XML/Python/TypeScript exact set parity;
- event names находятся в правильной domain section;
- никакие существующие event names не удалены/переименованы;
- guardrail script green.

## Targeted verification

```bash
python3 scripts/check_logging_guardrails.py
```

## Out of scope

Не добавлять emitters, payload TypedDict overengineering, promo service/UI/API.
Не коммитить и не пушить.
