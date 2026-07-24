# Slice 19 — PostgreSQL concurrency proof and release gate

## Локальная цель

Доказать то, чего не может SQLite: campaign row locking, capacity,
idempotency и shared-credit concurrency на реальном PostgreSQL. Этот slice не
добавляет product behavior.

## Preconditions

Все backend/frontend/infra slices приняты по отдельности. Тестовая БД
изолирована; production DB не используется.

## Разрешённые файлы

- новый `apps/api/tests/test_promo_postgres_acceptance.py`;
- при необходимости минимальная CI test invocation wiring, только после
  отдельного architect approval.

## Environment contract

```text
PROMO_TEST_POSTGRES_URL=postgresql+asyncpg://.../<isolated test db>
```

Test fail-closed проверяет dialect `postgresql`; SQLite URL не превращается в
skip/pass. Alembic upgrade head выполняется до test. Каждая case использует
unique users/campaigns и cleanup/transaction isolation.

## Required concurrency proofs

1. Same campaign, same user, two simultaneous redeems:
   - one 200/effect;
   - second ALREADY;
   - exactly one ledger/credit/Purchase/redemption;
   - counter=1.
2. `max_redemptions=1`, two users:
   - one success, one CAMPAIGN_FULL;
   - exactly one grant set/counter=1.
3. Existing/concurrent fulfilled natal Purchase:
   - no duplicate entitlement;
   - promo transaction not left aborted;
   - redemption points to fulfilled Purchase.
4. One remaining gift credit, concurrent election+horary:
   - exactly one spend succeeds;
   - `used_amount <= amount`;
   - loser gets domain no-credit outcome, not DB 500.
5. Injected final commit failure:
   - zero partial grants/counter;
   - no success log.

## Release gate

До создания production campaign архитектор фиксирует evidence:

```text
all targeted unit slices green
contracts:check green
Alembic roundtrip green
PostgreSQL concurrency proof green
frontend build green
repo/live Nginx hash equal + nginx -t
synthetic token absent from all logs
production NATAL_REPORT_ENABLED/YOOKASSA_ENABLED/product row verified
rollback compatibility build identified
```

Первый canary:

```text
max_redemptions <= 5
default 30/50/natal package
observe success/reject/failed/429 and LLM usage
no mass distribution before canary review
```

## Rollback acceptance

- disable campaign first;
- frontend rollback не ниже Slice 01 compatibility floor;
- backend image may roll back, new DB tables stay;
- after any real redemption no down-migration;
- existing grants never auto-revoked;
- privacy Nginx config remains installed.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && \
PROMO_TEST_POSTGRES_URL="$PROMO_TEST_POSTGRES_URL" \
python -m pytest tests/test_promo_postgres_acceptance.py -q
```

## Out of scope

Production mutations, campaign creation/distribution, commit/push/deploy by
coder. Финальный release выполняет архитектор/владелец отдельно.
