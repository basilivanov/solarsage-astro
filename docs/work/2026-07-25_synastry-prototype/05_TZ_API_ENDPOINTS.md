# 05_TZ: Синастрия — API endpoints

## 1. Packet title
Синастрия / Совместимость — API endpoints (срез 5 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 5: API endpoints

## 3. Modules
- M-API-SYNASTRY (apps/api/app/api/synastry.py)

## 4. Goal
Создать API endpoints: capabilities, list, quota, partners, status, detail, aspect, feedback, delete. Использовать паттерн apps/api/app/api/natal.py.

## 5. Exact write scope
- `apps/api/app/api/synastry.py` — все endpoints из ТЗ п. 3.3

## 6. Frozen / Out of scope
- Не трогать existing API endpoints
- Не трогать services (service orchestration — следующий срез)
- Не трогать models, schemas, scoring, LLM (уже готовы)

## 7. Must-preserve invariants
- Static routes (/capabilities, /quota) registered before dynamic (/{partner_id})
- Owner-scoped: чужой partner_id → 404
- Idempotency: UUID key + request hash
- Credit spend: one DB transaction
- Validation: name, birth_date, city, lat/lon, tz, precision

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -c "from app.api.synastry import router; print('api OK')"
python -m pytest apps/api/tests/test_synastry_api.py -q 2>/dev/null || echo "tests not yet written"
```

## 9. Expected evidence
- `git diff --name-only` — только 1 файл (+ опционально тесты)
- Импорт router — успешно

## 10. Escalation rule
Нужен соседний scope (service orchestration, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
