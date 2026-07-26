# C2_TZ: synastry spend correctness + idempotency + capabilities (Release A)

## 1. Packet title
Corrective wave, срез C2: правильный выбор кредита, idempotency с request_hash, единый баланс в quota/capabilities.

## 2. Phase / Wave
Post-synastry-live corrective, Release A. Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (§7.2, §7.3, §5.1 — читать обязательно). Зависит от C1 (weekly race fix, credit_spent событие).

## 3. Modules
- `apps/api/app/services/synastry_service.py` (только `create_partner_and_report`)
- `apps/api/app/db/models.py` (SynastryCreditSpend + request_hash)
- `apps/api/alembic/versions/0026_synastry_spend_request_hash.py` (новая)
- `apps/api/app/api/synastry.py` (quota/capabilities)
- `apps/api/app/schemas/synastry.py` (capabilities additive)
- `lib/api/synastry.ts` + `components/synastry/synastry-add-sheet.tsx` (idempotency key lifecycle)

## 4. Goal

### 4.1. Spend (§7.2) — переписать `create_partner_and_report` по порядку:
1. **Idempotency**: по `body.idempotency_key` искать spend; нашёлся и `request_hash` совпал → вернуть существующие partner/report (200-семантика повтора, без новых mutations); нашёлся и hash НЕ совпал → 409 `IDEMPOTENCY_CONFLICT`. Hash = sha256 нормализованных значимых полей (name strip-lower, birth_date, birth_time|"", birth_city|"", birth_lat/lon, birth_tz|"", relation, precision); в логах hash не содержит PII.
2. **Dedup** по partner_input_hash (уже есть, сохранить).
3. **Weekly-free resolve** через `get_or_create_current_weekly_free` (из C1 concurrency-safe).
4. **Кредит**: `select_spendable_credit(user_id, now, lock=True)` — правильный порядок (weekly → bonus по expiry → paid FIFO) и FOR UPDATE. Нет → 402 `NO_CREDITS` (стабильный domain error, не строка), БЕЗ создания rows.
5. Создать partner/report/spend (`used_amount += 1` на выбранном кредите, `request_hash` в spend), ОДИН commit до background task (task уже запускается в endpoint).
6. `IntegrityError` на уникальных ограничениях (race) → 409, без частичного spend.
7. `synastry.credit_spent` — после commit (из C1).

### 4.2. Migration `0026_synastry_spend_request_hash`
- `synastry_credit_spends.request_hash VARCHAR(64) NULL` (additive, backward-compatible: старые rows NULL);
- index на `idempotency_key` уже unique — достаточно;
- downgrade — drop column. Один parent = 0025.

### 4.3. Balance/capabilities (§7.3)
- `GET /api/synastry/quota` и `/capabilities` — баланс ТОЛЬКО через `HoraryCreditService.get_balance()`; `credit_balance = weeklyFreeAvailable + bonus + paid` (одна pure-функция агрегации, использовать в обоих).
- Capabilities additive: `creditBalance: int`, `canPurchase: bool` (из billing runtime — YooKassa enabled), `canCalculate: bool` (credit + partner limit), `blockedReason: null | "no_credits" | "partner_limit"`. Ничего не удалять из ответа.

### 4.4. Frontend idempotency key
- `synastry-add-sheet.tsx`: `crypto.randomUUID()` один раз при открытии формы; тот же key на retry; ЛЮБОЕ изменение значимого поля → новый key. `PartnerCreatePayload.idempotencyKey` уже есть в lib (проверить; если нет — добавить).

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py`
- `apps/api/app/db/models.py`
- `apps/api/alembic/versions/0026_synastry_spend_request_hash.py`
- `apps/api/app/api/synastry.py` (только quota/capabilities + 402 mapping)
- `apps/api/app/schemas/synastry.py`
- `lib/api/synastry.ts`
- `components/synastry/synastry-add-sheet.tsx`
- `apps/api/tests/test_synastry_service.py`, `apps/api/tests/test_synastry_api.py`
- `__tests__/synastry/synastry-add-sheet.test.tsx`

## 6. Frozen / Out of scope
- Refund (C1), weekly race impl (C1), billing/purchase (C3), purchase sheet (C4), sidecar (C5).
- НЕ менять horary/election spend paths (shared service — только читать).
- НЕ трогать product row / is_active (Release B).

## 7. Must-preserve invariants
- S1-S7 из §13 (replay, conflict, expired bonus untouched, порядок weekly→bonus→paid, double-spend невозможен).
- Один commit на всё; race → 409 без частичных данных.
- Баланс в quota и capabilities — одинаковое число из одного источника.
- GRACE-разметка; grace_lint PASS; check_logging_guardrails PASS.
- Миграция additive, reversible, один parent.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m alembic upgrade head   # на dev БД astro (проверить применение)
python -m pytest tests/test_synastry_service.py tests/test_synastry_api.py tests/test_horary_service.py -q
python3 scripts/grace_lint.py apps/api/app
python3 scripts/check_logging_guardrails.py
npx vitest run __tests__/synastry
```
Тесты: replay тот же key+payload → те же IDs, 0 новых spend; тот же key другой payload → 409; expired bonus + paid → тратится paid; порядок weekly→bonus→paid; no credits → 402 NO_CREDITS без rows; capabilities содержат creditBalance/canPurchase/blockedReason.

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; `alembic heads` = 0026.

## 10. Escalation rule
Нужен billing/purchase/frontend за пределами add-sheet → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
