# C1_TZ: weekly-free race + refund lock + observability events (Release A)

## 1. Packet title
Corrective wave, срез C1: concurrency-safe weekly-free create, refund под lock, события credit_spent/credit_refunded.

## 2. Phase / Wave
Post-synastry-live corrective, Release A. Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (§7.1, §7.4, §11 — читать обязательно). Plan: `docs/work/2026-07-26_credit-corrective/00_PLAN.md`.

## 3. Modules
- `apps/api/app/services/horary_credit_service.py`
- `apps/api/app/services/synastry_service.py` (только `_fail_and_refund` + spend-success событие)
- `grace/canon/observability.xml` + generated registries (sync, не руками переписывать логику — только добавить события)

## 4. Goal

### 4.1. Weekly-free race (§7.1)
`HoraryCreditService.get_or_create_current_weekly_free()`:
- insert обернуть в savepoint/nested transaction (`async with db.begin_nested()`);
- при `IntegrityError` (unique `uq_horary_credits_weekly_free`) — перечитать существующую строку и вернуть её;
- НЕ откатывать внешнюю транзакцию бизнес-операции;
- оба конкурентных caller получают ровно одну canonical row.

### 4.2. Refund (§7.4)
`SynastryService._fail_and_refund()`:
- spend выбирается `SELECT ... FOR UPDATE` (`.with_for_update()`);
- если `refunded_at IS NOT NULL` → no-op (НО state=failed всё равно выставляется, без второго refund);
- credit row лочится перед decrement (`with_for_update` на HoraryCredit);
- `used_amount` не может уйти < 0 (guard);
- state fail + refund в ОДНОМ commit;
- событие `synastry.credit_refunded` эмитится ровно один раз (при фактическом refund).

### 4.3. Observability (§11)
- Добавить в `grace/canon/observability.xml` события `synastry.credit_spent` (payload: report_id_hash, credit_source) и `synastry.credit_refunded` (payload: report_id_hash, error_code);
- синхронизировать generated registries (`apps/api/app/core/logging_events.py`, `lib/log/events.gen.ts`) с XML (drift-checker `python3 scripts/check_logging_guardrails.py` обязан пройти);
- `synastry.credit_spent` эмитить в `create_partner_and_report` ПОСЛЕ успешного commit (payload: report_id_hash, credit_source=тип/источник кредита — weekly_free/bonus/paid по полям кредита);
- идентификаторы в payload — только через `hash_log_identifier` (сырой report_id запрещён guardrails).

## 5. Exact write scope
- `apps/api/app/services/horary_credit_service.py`
- `apps/api/app/services/synastry_service.py`
- `grace/canon/observability.xml`
- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`
- `apps/api/tests/test_horary_credit_race_pg.py` (новый)
- `apps/api/tests/test_synastry_service.py` (refund кейсы)

## 6. Frozen / Out of scope
- НЕ трогать: `SynastryService.create_partner_and_report` логику выбора кредита (срез C2), api endpoints, frontend, billing.
- НЕ менять сигнатуры публичных методов кроме описанного.
- НЕ добавлять миграций.

## 7. Must-preserve invariants
- `select_spendable_credit`, `get_balance` — не менять (используются horary/election).
- Refund идемпотентен при любом числе повторных вызовов (S7).
- Все существующие тесты зелёные; GRACE-разметка; `python3 scripts/grace_lint.py apps/api/app` PASS; `python3 scripts/check_logging_guardrails.py` PASS.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_horary_credit_race_pg.py tests/test_synastry_service.py tests/test_horary_service.py -q
python3 scripts/grace_lint.py apps/api/app
python3 scripts/check_logging_guardrails.py
```

**Обязателен real-Postgres concurrency test** (§7.1): disposable БД `astro_test` на инстансе `localhost:5433` (создать/дропнуть в fixture через `docker exec solarsage-db psql -U astro -d postgres -c "CREATE DATABASE astro_test"` / DROP; DATABASE_URL override в engine фикстуры; alembic upgrade head в setUp). Два `asyncio.gather` конкурентных `get_or_create_current_weekly_free` → ровно одна row, оба вернули её же, никакого 500. Тест маркировать `@pytest.mark.integration` и прогнать явно (это доказательство; SQLite unit НЕ принимается).

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод всех проверок; отдельно вывод integration race-теста.
- Diff observability.xml (2 события).

## 10. Escalation rule
Нужен scope C2+ (spend logic, capabilities, billing) → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
