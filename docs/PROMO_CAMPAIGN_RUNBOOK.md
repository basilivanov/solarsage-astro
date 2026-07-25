# ############################################################################
# AI_HEADER: DOC_PROMO_CAMPAIGN_RUNBOOK
# ROLE: Operational runbook for named promo campaigns, CLI invocation, detection, and incident response.
# DEPENDENCIES: docs/PRODUCTION_RUNBOOK.md
# ############################################################################

# START_MODULE_CONTRACT: M-DOC-PROMO-CAMPAIGN-RUNBOOK
# purpose: Operator guide for promo campaign creation, verification, status monitoring, detection queries, alert thresholds, and incident rollback.
# owns:
#   - docs/PROMO_CAMPAIGN_RUNBOOK.md
# inputs: none
# outputs: none
# dependencies: none
# invariants:
#   - No real tokens, code hashes, or session secrets in document (only <OUTPUT_TOKEN> placeholder).
#   - Canonical CLI invocation strictly via docker exec -i solarsage-api python -m app.cli.promo_campaign.
#   - Disable campaign before any rollback; no down-migrations after redemption.
# failure_policy: none.
# END_MODULE_CONTRACT: M-DOC-PROMO-CAMPAIGN-RUNBOOK

# START_MODULE_MAP: M-DOC-PROMO-CAMPAIGN-RUNBOOK
# public_entrypoints: none
# semantic_blocks: none
# END_MODULE_MAP: M-DOC-PROMO-CAMPAIGN-RUNBOOK

# Named Promo Campaign Operations & Incident Runbook — SolarSage Astro

This document is the canonical operator runbook for managing, creating, monitoring, disabling, and handling incidents with named promo campaigns on `astro.vasiliy-ivanov.ru`.

---

## 1. Pre-Create Verification Checklist

Before creating a new promo campaign, the operator must verify the following pre-conditions:

1. **Active Container & Release Identity:** Verify running `solarsage-api` container image digest matches the active release record (`/var/lib/solarsage/orchestrator/release-record`).
2. **Database Migration Head:** Confirm database schema is migrated to head (includes Alembic migration `0024_named_promo_campaign`).
3. **Nginx Privacy & Hash Proof:** Verify `/etc/nginx/sites-enabled/astro.vasiliy-ivanov.ru.conf` matches repository hash, `log_format astro_privacy` is enabled without raw `tgWebAppStartParam` or `$http_referer`, and `Referrer-Policy` is `strict-origin`.
4. **Feature Flags & Products (when `unlock_natal=true`):** Check `/etc/solarsage/app.env`:
   - `NATAL_REPORT_ENABLED=true`
   - `YOOKASSA_ENABLED=true`
   - Verify `natal_full_report` product row exists in `products` DB table.
5. **Worst-Case Totals Review:** Calculate maximum potential access days, bonus credits, and natal unlocks (`max_redemptions * bonus_credits`).
6. **Canary Campaign Rule:** The first campaign for any new promo pattern must set `max_redemptions <= 5`.

---

## 2. Canonical CLI Invocation

All promo campaign management commands must be executed **strictly inside the active `solarsage-api` container** using fixed command arguments.

- **Forbidden:** Host Python checkouts, manual process execution, port 8001 direct calls, or shell script wrapping.
- **Token Output:** The raw promo token is generated in-process by cryptographically secure `secrets` and appears **exactly once in secure operator `stdout`**. `<OUTPUT_TOKEN>` placeholder is used in documentation.

### 2.1 Campaign Creation

```bash
docker exec -i solarsage-api python -m app.cli.promo_campaign create \
  --name "<CAMPAIGN_NAME>" \
  --max-redemptions 5 \
  --activation-days 7 \
  --access-days 30 \
  --bonus-credits 50 \
  --unlock-natal
```

### 2.2 Status Check

```bash
docker exec -i solarsage-api python -m app.cli.promo_campaign status \
  --campaign-id <CAMPAIGN_UUID>
```

### 2.3 List Redemptions

```bash
docker exec -i solarsage-api python -m app.cli.promo_campaign list-redemptions \
  --campaign-id <CAMPAIGN_UUID> \
  --limit 50
```

### 2.4 Disable Campaign

```bash
docker exec -i solarsage-api python -m app.cli.promo_campaign disable \
  --campaign-id <CAMPAIGN_UUID>
```

---

## 3. Detection Queries & Observability

### 3.1 Structured Event Logging

Monitor structured JSON logs emitted by the backend using these event names:

- `promo.campaign_created`: Emitted when campaign is created.
- `promo.offer_viewed`: Emitted when user opens confirmation sheet.
- `promo.redemption_succeeded`: Emitted after successful grant commit.
- `promo.redemption_rejected`: Emitted on expected domain/rate rejections, grouped by `error_code`:
  - `INVALID_CODE`
  - `CAMPAIGN_EXPIRED`
  - `CAMPAIGN_FULL`
  - `ALREADY_REDEEMED`
  - `PROFILE_INCOMPLETE`
  - `RATE_LIMITED`
- `promo.redemption_failed`: Emitted on unhandled DB/system exceptions, grouped by `error_kind`.
- `promo.campaign_disabled`: Emitted when operator disables campaign.

*Privacy Note:* Never search or query logs by raw token, code hash, display name, or user profile data.

### 3.2 SQL Verification Queries (by Campaign UUID Only)

Check campaign redemption consistency:

```sql
SELECT id, display_name, active, max_redemptions, redemptions_used,
       (SELECT COUNT(*) FROM promo_redemptions WHERE campaign_id = promo_campaigns.id) AS redemptions_count
FROM promo_campaigns
WHERE id = '<CAMPAIGN_UUID>';
```

Verify grant foreign keys and absence of duplicate grants:

```sql
SELECT id, user_id, redeemed_at, access_ledger_id, credit_id, natal_purchase_id
FROM promo_redemptions
WHERE campaign_id = '<CAMPAIGN_UUID>'
ORDER BY redeemed_at DESC;
```

---

## 4. Alert & Action Thresholds

- **`promo.redemption_failed` > 0 during canary:** Stop distribution immediately, inspect system logs, and disable campaign (`disable --campaign-id <CAMPAIGN_UUID>`).
- **Counter Mismatch (`redemptions_used != COUNT(PromoRedemption)`):** Immediately disable campaign. Ad-hoc manual SQL counter edits are strictly forbidden.
- **5xx HTTP Errors > 0:** Disable campaign pending investigation.
- **`RATE_LIMITED` > 5% of attempts:** Inspect per-user rate limiter (`promo_rate_limiter`). Do not increase campaign max redemptions.
- **`INVALID_CODE` Spike:** Indicates link corruption or brute-force scanning. Verify privacy logs contain no tokens.
- **Unexpected LLM / Credit Burn:** Disable campaign and recalculate maximum capacity.

---

## 5. Incident Response & Rollback Protocol

If a promo campaign issue occurs in production:

1. **Disable Campaign First:** Run `docker exec -i solarsage-api python -m app.cli.promo_campaign disable --campaign-id <CAMPAIGN_UUID>`.
2. **Verify Ingress Rejection:** Confirm new requests receive safe `INVALID_CODE` error (HTTP 400) and `redemptions_used` counter stops incrementing.
3. **Preserve Existing Grants:** Granted access ledgers, credits, and natal purchases remain valid per product contract.
4. **Frontend Rollback Boundary:** Any frontend rollback must stay above the Slice 01 compatibility floor (`start_param` classification and storage).
5. **Nginx Privacy:** Keep `astro_privacy` log format and `strict-origin` Referrer-Policy active.
6. **No Down-Migrations:** Database schema down-migrations are strictly forbidden after the first redemption.
7. **No Ad-Hoc SQL Mutations:** Direct SQL `DELETE` or `UPDATE` operations on user grants or redemptions are prohibited without a separate owner-approved specification.
