# Slice 20 — promo operations, detection and incident runbook

## Локальная цель

Сделать campaign observable и операционно обратимой в допустимых границах:
дать владельцу exact create/status/disable/canary/log/DB checks без raw token в
командах и logs. Product behavior не менять.

## Preconditions

CLI/events/release acceptance slices приняты. Production команды используют
только active immutable API container, не mutable host checkout/manual uvicorn.

## Разрешённые файлы

- новый `docs/PROMO_CAMPAIGN_RUNBOOK.md`;
- `docs/PRODUCTION_RUNBOOK.md` — только короткая ссылка/section;
- новый `apps/api/tests/test_promo_runbook_contract.py`.

## Runbook content

### Pre-create

- active API image/release identity verified;
- DB migration head verified;
- Nginx installed hash/privacy proof verified;
- `NATAL_REPORT_ENABLED`, `YOOKASSA_ENABLED` and product row checked when
  `unlock_natal=true`;
- worst-case bonus/natal/access totals reviewed;
- first campaign canary `max_redemptions <= 5`.

### Canonical CLI invocation

Use fixed argv in active `solarsage-api` container, no shell/eval and no host
Python checkout. Create token генерируется process и появляется только в secure
operator stdout. Runbook не содержит real token/example resembling a live
token; placeholder `<OUTPUT_TOKEN>` only.

Canonical command shape:

```bash
docker exec -i solarsage-api python -m app.cli.promo_campaign create \
  --name "<CAMPAIGN_NAME>" --max-redemptions 5
docker exec -i solarsage-api python -m app.cli.promo_campaign status \
  --campaign-id <CAMPAIGN_UUID>
docker exec -i solarsage-api python -m app.cli.promo_campaign disable \
  --campaign-id <CAMPAIGN_UUID>
```

Перед mutation runbook сверяет running container image digest с active release
record; mismatch — stop, command не запускать.

### Detection queries

Structured event queries/counts:

```text
promo.campaign_created
promo.offer_viewed
promo.redemption_succeeded
promo.redemption_rejected grouped by error_code
promo.redemption_failed grouped by error_kind
promo.campaign_disabled
```

SQL/status checks by campaign UUID only:

```text
redemptions_used
COUNT(PromoRedemption)
counter consistency
grant FK non-null according to benefits
duplicate grants absent
```

Do not query/search logs by raw token/hash/display name/user profile.

### Alert/action thresholds

- any `promo.redemption_failed` during canary -> stop distribution, inspect,
  normally disable campaign;
- counter mismatch -> immediate disable and NO manual counter edit;
- 5xx > 0 during canary -> disable pending review;
- `RATE_LIMITED` > 5% valid-flow attempts or multiple user hashes behind one
  IP -> inspect limiter, do not raise campaign capacity;
- `INVALID_CODE` spike -> possible link corruption/abuse; no token logging;
- unexpected LLM/credit burn -> stop distribution and recalculate max.

### Incident/rollback

1. Disable campaign first.
2. Confirm new user gets safe INVALID_CODE and counter stops.
3. Preserve existing grants per product contract.
4. Frontend rollback not below Slice 01 compatibility floor.
5. Keep Nginx privacy config.
6. Never down-migrate after first redemption.
7. Any compensating grant removal requires separate owner-approved TZ; runbook
   explicitly forbids ad-hoc DELETE/UPDATE.

## Tests

Static runbook contract proves:

- exact event names/error codes/thresholds present;
- active-container invocation, no manual uvicorn/port 8001/mutable checkout;
- no live-looking token, code hash, session secret or shell `eval/source`;
- disable-before-rollback and no-down-migration rules present;
- Production Runbook links to the dedicated document.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_runbook_contract.py -q
```

## Out of scope

Live production commands, campaign creation, automatic grant revocation,
dashboard vendor/infrastructure. Не коммитить и не пушить.
