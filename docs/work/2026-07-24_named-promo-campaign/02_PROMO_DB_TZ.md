# Slice 02 — PromoCampaign/PromoRedemption database foundation

## Локальная цель

Добавить только ORM/migration foundation двух promo entities с DB-level
constraints. Никаких routes, services, CLI или frontend.

## Разрешённые файлы

- `apps/api/app/db/models.py`;
- новый `apps/api/alembic/versions/0024_named_promo_campaign.py`;
- новый `apps/api/tests/test_promo_models.py`;
- при необходимости только assertions в `apps/api/tests/test_alembic_roundtrip.py`.

## Модель `PromoCampaign`

Обязательные fields:

```text
id UUID PK
display_name String(120) not null
code_hash String(64) not null unique
active bool not null default true
activation_starts_at DateTime(timezone=True) not null
activation_ends_at DateTime(timezone=True) not null
max_redemptions int not null
redemptions_used int not null default 0
access_days int not null default 30
bonus_credits int not null default 50
unlock_natal bool not null default true
created_at / updated_at DateTime(timezone=True) not null server defaults
```

Named check constraints exactly cover:

- end strictly after start;
- `max_redemptions > 0`;
- `0 <= redemptions_used <= max_redemptions`;
- nonnegative access/credits;
- credits require positive access days;
- at least one benefit enabled.

Do not add raw token, token prefix, plaintext code, owner notes or campaign type.

## Модель `PromoRedemption`

```text
id UUID PK
campaign_id UUID FK promo_campaigns.id not null
user_id UUID FK users.id not null
redeemed_at timezone datetime not null server default now
access_ledger_id UUID FK access_ledger.id ON DELETE SET NULL nullable
credit_id UUID FK horary_credits.id ON DELETE SET NULL nullable
natal_purchase_id UUID FK purchases.id ON DELETE SET NULL nullable
UNIQUE(campaign_id, user_id)
INDEX(campaign_id, redeemed_at)
INDEX(user_id)
```

Campaign FK is non-destructive/audit-oriented; no campaign delete path is added.
Relationships may be added only where they improve service typing; avoid a
large unrelated relationship rewrite.

## Migration

- revision: `0024_named_promo_campaign`;
- down revision: `0023_election`;
- upgrade creates campaign first, redemption second;
- downgrade drops redemption first, then campaign;
- PostgreSQL and SQLite test dialect must both work;
- no seed campaign/token in migration.

## Tests

Prove at ORM/DB level:

- valid campaign/redemption inserts;
- duplicate `code_hash` rejected;
- duplicate `(campaign_id,user_id)` rejected;
- invalid window/counters/empty benefit rejected;
- nullable grant references accepted where benefit is disabled;
- Alembic upgrade -> downgrade base -> upgrade head remains green.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_models.py tests/test_alembic_roundtrip.py -q
```

## Out of scope

Hash/token generation, business validation, grants, API, events, CLI, UI.
Не коммитить и не пушить.

