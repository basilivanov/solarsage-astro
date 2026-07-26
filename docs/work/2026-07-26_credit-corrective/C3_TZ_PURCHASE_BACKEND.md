# C3_TZ: purchase backend — synastry credit за 39900 (Release B)

## 1. Packet title
Corrective wave, срез C3: catalog + migration активации продукта, purchase contract (election_1 + synastry), fulfill attribution, webhook idempotency.

## 2. Phase / Wave
Post-synastry-live corrective, Release B. Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (§8.1, §8.2, §13 S8-S11 — читать обязательно). Деплоится ПОСЛЕ Release A.

## 3. Modules
- `apps/api/alembic/versions/0027_synastry_product_live.py` (новая)
- `apps/api/app/services/product_catalog.py`
- `apps/api/app/schemas/payment.py`
- `apps/api/app/services/billing_service.py`
- `lib/api/payment.ts`

## 4. Goal

### 4.1. Catalog и migration (§8.1)
- `0027_synastry_product_live.py`: UPDATE существующей строки `products.slug='synastry'` → `is_active=true, product_type='one_time', price_kopecks=39900, currency='RUB', horary_quota=1`; fail-closed: строка обязана существовать ровно одна (иначе migration падает); downgrade — ТОЛЬКО деактивация (`is_active=false`), purchase/credit rows не трогать. Один parent = 0026.
- `product_catalog.py`: синхронизировать (убрать «fail-closed until real fulfillment», is_active=True с теми же полями).

### 4.2. Public purchase contract (§8.2)
- `PurchaseStartRequest.product_slug`: принимать `election_1` и `synastry` (оба one-time slugs из каталога).
- `lib/api/payment.ts::OneTimeProductSlug`: добавить `synastry`; union backend/frontend — contract test.
- `BillingService._fulfill_one_time()`: выдаёт один `HoraryCredit` (horary_quota=1) с `metadata_json` минимум `{product_slug, purchase_id}` (без PII/платёжных деталей); повторный webhook — НЕ создаёт второй credit (проверка по purchase id).
- Деактивированный product → `PRODUCT_NOT_FOUND`, provider payment не создаётся.
- Buy-flow test для каждого активного one-time slug (`election_1`, `synastry`).

## 5. Exact write scope
- `apps/api/alembic/versions/0027_synastry_product_live.py`
- `apps/api/app/services/product_catalog.py`
- `apps/api/app/schemas/payment.py`
- `apps/api/app/services/billing_service.py`
- `lib/api/payment.ts`
- `apps/api/tests/test_billing_products.py`, `apps/api/tests/test_billing_start_endpoints.py`, `apps/api/tests/test_billing_service.py`
- `__tests__/billing/` (contract union test, если паттерн существует — иначе lib test рядом)

## 6. Frozen / Out of scope
- Credit logic (C1/C2), purchase sheet UI (C4), sidecar (C5).
- YooKassa config — не менять.
- Массовый рефакторинг billing_service — только перечисленное.

## 7. Must-preserve invariants
- Повторный webhook не дублирует credit (S11).
- election_1 покупка не 422 (S10) и ровно один credit после verified fulfillment.
- Деньги: только verified webhook выдаёт credit; frontend-redirect не доказательство.
- Миграция reversible, один parent; GRACE-разметка; grace_lint PASS.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m alembic upgrade head && python -m alembic downgrade -1 && python -m alembic upgrade head
python -m pytest tests/test_billing_products.py tests/test_billing_start_endpoints.py tests/test_billing_service.py -q
python3 scripts/grace_lint.py apps/api/app
npx vitest run __tests__
```
После upgrade: `SELECT slug,is_active,price_kopecks,horary_quota FROM products WHERE slug='synastry'` = t/39900/1; после downgrade — f и исторические rows на месте.

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок + alembic up/down/up.

## 10. Escalation rule
Нужен frontend purchase sheet / credit scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
