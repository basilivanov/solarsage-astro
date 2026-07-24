# Slice 06 — atomic promo preview/redemption domain service

## Локальная цель

Реализовать backend domain behavior поверх готовых models/helpers без HTTP,
Pydantic, CLI и frontend. Один service владеет validation order, grants,
transaction и state-level idempotency.

## Preconditions

Slices 02–05 приняты. Кодер получает только этот документ и изучает public
contracts `AccessService`, `NatalContextService`, `HoraryCredit`, `Purchase`.

## Разрешённые файлы

- новый `apps/api/app/services/promo_campaign_service.py`;
- новый `apps/api/tests/test_promo_campaign_service.py`.

Если для natal unique race нужен один узкий test helper, он остаётся в test
file. Не менять billing/referral/API modules.

## Public service contract

Создать internal typed dataclasses (или равноценные typed records) без wire
camelCase:

```text
PromoOfferData(display_name, access_days, bonus_credits, unlock_natal)
PromoPreviewData(offer, profile_complete)
PromoGrantData(access dates, credit expiry/count, natal flags)
PromoRedeemData(offer, grants)
PromoDomainError(code, safe_message)
```

Public methods:

```py
async def preview(user_id, token, *, now=None) -> PromoPreviewData
async def redeem(user_id, token, *, now=None) -> PromoRedeemData
```

`now` injection предназначен для deterministic tests; production default UTC.
Raw token не сохраняется в object fields/exceptions/logs.

## Token and campaign validation

- exact opaque regex из master;
- invalid format -> `INVALID_CODE`, без hash lookup;
- SHA-256 exact ASCII -> lowercase 64-char hex;
- preview uses ordinary select;
- redeem uses `SELECT ... FOR UPDATE` by `code_hash`;
- unknown row -> `INVALID_CODE`;
- immediately after resolving campaign, existing `(campaign,user)` ->
  `ALREADY_REDEEMED`, даже если row теперь inactive/expired/full;
- for users without redemption: inactive/not-yet-started -> `INVALID_CODE`;
- for users without redemption: end reached -> `CAMPAIGN_EXPIRED`;
- campaign `unlock_natal=false`: base readiness false ->
  `PROFILE_INCOMPLETE` on redeem;
- campaign `unlock_natal=true`: strict natal readiness false ->
  `PROFILE_INCOMPLETE` on redeem;
- capacity reached -> `CAMPAIGN_FULL`;
- preview returns `profile_complete=false`, not an error, for valid available
  campaign with incomplete profile.

Preview creates/updates nothing and never reserves capacity.

## Redemption transaction

`redeem` owns exactly one final `commit`:

1. Resolve/lock campaign.
2. Check existing redemption before availability validation.
3. Validate active/window for a new redemption.
4. Lock the internal `User` row with `SELECT ... FOR UPDATE` for every new
   redemption. Lock order is always campaign first, user second. This
   serializes additive access calculation across different promo campaigns for
   the same user.
5. Load profile and validate base/strict completeness according to campaign.
6. Check capacity.
7. If `access_days > 0`, use `AccessService.next_grant_start` and
   `grant_subscription(..., commit=False)`; retain returned ID.
8. If `bonus_credits > 0`, create one `HoraryCredit`:
   `source=gift`, exact amount, used=0, week fields null,
   `expires_at=UTC midnight(access_end+1 day)`.
9. If `unlock_natal`, compute current canonical profile hash, reuse existing
   fulfilled `natal_full_report` Purchase or insert `delivered`, payment null.
10. Insert one PromoRedemption with IDs.
11. Increment counter once.
12. Flush constraints and commit once.

Credit `metadata_json` may contain only stable `grant_type=promo` and campaign
UUID. No display name/hash/token.

No `Subscription`, `Payment`, provider call, natal generation or credit spend.

## Race/error policy

- Campaign row lock + UNIQUE redemption protect same-campaign concurrency.
- User row lock protects `next_grant_start` from overlapping access grants when
  two different promo campaigns are redeemed concurrently by the same user.
- Existing natal entitlement statuses: `succeeded|delivered`.
- Concurrent natal entitlement insert is handled through a savepoint or one
  full-transaction bounded retry. An IntegrityError must never leave session in
  failed state and then partially commit other grants.
- Any unexpected exception -> rollback all and re-raise sanitized at outer
  boundary; counter and every grant remain absent.
- Domain errors also rollback any active transaction before propagation.
- State-level duplicate returns `ALREADY_REDEEMED`; no duplicate grants.
- Нельзя вызывать `NatalContextService.get_or_build_natal_context`: он владеет
  commits/sidecar effects. Использовать только pure completeness helper и
  `compute_profile_hash`.
- Нельзя полагаться на `grant_subscription` default commit; передавать
  `commit=False` явно.

## Logging

- success: `promo.redemption_succeeded` with safe campaign ID/config and
  `natal_already_owned`, строго после successful final commit;
- domain rejection during redeem: `promo.redemption_rejected` with stable code
  and campaign ID only if already resolved;
- unexpected failure: сначала rollback, затем `promo.redemption_failed` с safe
  `error_kind` и campaign ID только если resolved;
- preview does not emit `promo.offer_viewed` (UI owns actual view);
- no raw token/hash/display name/profile fields in log or exception.

## Required tests

1. Default happy path creates exactly:
   - one subscription ledger for 30 days;
   - one gift credit 50/0 with exact exclusive expiry;
   - one delivered natal Purchase;
   - one redemption referencing all three;
   - counter 1.
2. Existing future/active access defers promo start after latest end.
3. Existing fulfilled natal entitlement is reused; no duplicate Purchase.
4. Campaign with selected zero/false benefits creates only enabled grants.
   Access/credits-only campaign accepts base-complete profile without exact
   birth time; natal campaign rejects it without mutation.
5. Invalid/inactive/not-started/expired/full/incomplete/already exact codes.
   Existing redemption remains ALREADY after disable/expiry/full.
6. Duplicate redeem changes neither counts nor grant rows.
7. Injected failure after each grant stage rolls back all effects and counter.
8. Preview has zero mutations and reports profile completeness.
9. Captured log envelopes contain no token/hash/display name.
10. Compiled PostgreSQL redeem select includes `FOR UPDATE` (SQLite execution
    alone is not proof).
11. Injected final commit failure не оставляет grants/counter и не пишет
    `promo.redemption_succeeded`; пишет ровно один safe failed event.
12. PostgreSQL-compiled new-redemption path includes `FOR UPDATE` for both the
    campaign and internal user row, with campaign-before-user lock order.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_campaign_service.py -q
```

## Out of scope

HTTP status mapping, OpenAPI, Nginx rate limit, CLI, UI, real PostgreSQL
concurrency acceptance. Не коммитить и не пушить.
