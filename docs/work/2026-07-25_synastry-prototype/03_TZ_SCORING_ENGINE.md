# 03_TZ: Синастрия — Scoring engine

## 1. Packet title
Синастрия / Совместимость — Scoring engine (срез 3 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 3: Scoring engine

## 3. Modules
- M-SYNASTRY-SCORING (apps/api/app/services/synastry_scoring.py)

## 4. Goal
Создать pure scoring engine: tone-mapping, балл 0–100, счётчики, precision-инварианты. Без LLM, без API, без sidecar — только engine.

## 5. Exact write scope
- `apps/api/app/services/synastry_scoring.py` — scoring engine по ТЗ п. 3.2 и `03_SCORING_AND_TONE_CONTRACT.md`

## 6. Frozen / Out of scope
- Не трогать existing services
- Не трогать API endpoints, frontend, sidecar
- Не трогать models, schemas (уже готовы)

## 7. Must-preserve invariants
- Engine чистый (no side effects, no LLM calls)
- Precision-инварианты: unknown time → partner houses/ASC unavailable, Moon approximate, Moon weight=0
- Tone mapping: supportive/mixed/tense по орбисам и аспектам
- Балл 0–100, округление по нормативному контракту

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -c "from app.services.synastry_scoring import SynastryScoringEngine; print('scoring OK')"
python -m pytest apps/api/tests/test_synastry_scoring.py -q 2>/dev/null || echo "tests not yet written"
```

## 9. Expected evidence
- `git diff --name-only` — только 1 файл (+ опционально тесты)
- Импорт engine — успешно

## 10. Escalation rule
Нужен соседний scope (API, LLM, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
