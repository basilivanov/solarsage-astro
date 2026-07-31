# 01_TZ: Синастрия — Database schema + models

## 1. Packet title
Синастрия / Совместимость — Database schema + models (срез 1 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 1: DB schema

## 3. Modules
- M-DB-MODELS (apps/api/app/db/models.py)
- M-ALEMBIC (apps/api/alembic/versions/0025_synastry_schema.py)

## 4. Goal
Создать additive таблицы синастрии и Alembic миграцию 0025. Без API, без бизнес-логики — только схема.

## 5. Exact write scope
- `apps/api/app/db/models.py` — добавить 5 таблиц:
  - `synastry_partners` — owner-scoped birth PII, relation, precision, partner_input_hash, timestamps
  - `synastry_reports` — owner/partner FK, owner profile hash, versions, state/stage/attempt/lease, deterministic JSON, narrative JSON, errors, invalidated_at
  - `synastry_aspect_details` — (report_id, aspect_id, prompt_version) unique, state/attempt/lease/payload/error
  - `synastry_feedback` — (user_id, report_id) unique, value, time
  - `synastry_credit_spends` — credit_id FK, nullable report_id UNIQUE ON DELETE SET NULL, idempotency_key UNIQUE, refunded_at, amount=1
- `apps/api/alembic/versions/0025_synastry_schema.py` — миграция create tables + indexes, обновить products.synastry до quota=1 (is_active=false)

## 6. Frozen / Out of scope
- Не трогать существующие таблицы (users, horary_credits, products и т.д.)
- Не трогать API endpoints, services, frontend
- Не трогать sidecar
- Не трогать existing migrations

## 7. Must-preserve invariants
- Все существующие таблицы и их данные не изменяются
- Миграция additive (только CREATE, никаких DROP/ALTER для существующих таблиц)
- products.synastry обновляется, но остаётся is_active=false

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -c "from app.db.models import SynastryPartner, SynastryReport, SynastryAspectDetail, SynastryFeedback, SynastryCreditSpend; print('models OK')"
```

## 9. Expected evidence
- `git diff --name-only` — только 2 файла
- `alembic upgrade head` — успешно
- `alembic downgrade -1` — успешно
- `alembic upgrade head` — успешно
- Импорт моделей — успешно

## 10. Escalation rule
Нужен соседний scope (API, services, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
