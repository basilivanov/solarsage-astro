# 06_TZ: Синастрия — Service orchestration

## 1. Packet title
Синастрия / Совместимость — Service orchestration (срез 6 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 6: Service orchestration

## 3. Modules
- M-SYNASTRY-SERVICE (apps/api/app/services/synastry_service.py)

## 4. Goal
Создать service orchestration: sidecar → scoring → LLM → персист. Координация всех компонентов.

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py` — оркестрация по ТЗ п. 3.1, 10.2

## 6. Frozen / Out of scope
- Не трогать existing services
- Не трогать API endpoints (уже готовы)
- Не трогать models, schemas, scoring, LLM (уже готовы)

## 7. Must-preserve invariants
- Owner cache → sidecar facts → API overlays/scoring
- State machine: PENDING → CALCULATING → NARRATING → READY
- Credit spend: one DB transaction
- External calls after commit, no row lock
- LLM attempt limit: 2 через все claims

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -c "from app.services.synastry_service import SynastryService; print('service OK')"
python -m pytest apps/api/tests/test_synastry_service.py -q 2>/dev/null || echo "tests not yet written"
```

## 9. Expected evidence
- `git diff --name-only` — только 1 файл (+ опционально тесты)
- Импорт service — успешно

## 10. Escalation rule
Нужен соседний scope (frontend, sidecar) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
