# 04_TZ: Синастрия — LLM module

## 1. Packet title
Синастрия / Совместимость — LLM module (срез 4 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 4: LLM module

## 3. Modules
- M-LLM-SYNASTRY (apps/api/app/services/synastry_llm.py)

## 4. Goal
Создать pure LLM module: prompts, schema, static dictionaries, local validator. Без network calls — только prompts/schema/validator. Network entrypoints остаются в llm_service.py.

## 5. Exact write scope
- `apps/api/app/services/synastry_llm.py` — pure prompts/schema/validator по ТЗ п. 4

## 6. Frozen / Out of scope
- Не трогать existing llm_service.py (network entrypoints)
- Не трогать API endpoints, frontend, sidecar
- Не трогать models, schemas, scoring (уже готовы)

## 7. Must-preserve invariants
- Pure module (no network calls, no side effects)
- Static dictionaries: PLANET_MEANINGS, ASPECT_MEANINGS (verbatim from prototype)
- Local validator: JSON-schema strict, length limits, blocklist, approximate reject
- PII not in prompts: no partner name, no birth data

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -c "from app.services.synastry_llm import PLANET_MEANINGS, ASPECT_MEANINGS, build_report_prompt, validate_llm_output; print('llm OK')"
python -m pytest apps/api/tests/test_synastry_llm.py -q 2>/dev/null || echo "tests not yet written"
```

## 9. Expected evidence
- `git diff --name-only` — только 1 файл (+ опционально тесты)
- Импорт module — успешно

## 10. Escalation rule
Нужен соседний scope (API, scoring, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
