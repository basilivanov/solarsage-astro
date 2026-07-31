# 02_TZ: Синастрия — Pydantic schemas

## 1. Packet title
Синастрия / Совместимость — Pydantic schemas (срез 2 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 2: Pydantic schemas

## 3. Modules
- M-SCHEMAS-SYNASTRY (apps/api/app/schemas/synastry.py)

## 4. Goal
Создать Pydantic schemas для синастрии: Capabilities, PartnerCreate, ListRead, GenerationRead, Report, Aspect, AspectDrilldown, FeedbackWrite/Read. Использовать CamelModel как в соседних фичах.

## 5. Exact write scope
- `apps/api/app/schemas/synastry.py` — все schemas из ТЗ п. 3.4

## 6. Frozen / Out of scope
- Не трогать existing schemas
- Не трогать API endpoints, services, frontend
- Не трогать models (уже готовы)

## 7. Must-preserve invariants
- Все schemas используют CamelModel
- camelCase wire format через CamelModel
- snake_case внутри через Field alias

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -c "from app.schemas.synastry import SynastryCapabilitiesRead, PartnerCreate, SynastryListRead, SynastryGenerationRead, SynastryReport, SynastryAspect, AspectDrilldown, SynastryFeedbackWrite, SynastryFeedbackRead; print('schemas OK')"
python -c "from app.schemas.synastry import PartnerCreate; p = PartnerCreate(name='Максим', relation='romantic', birth_date='1987-09-09', birth_time='08:15', birth_city='Москва', birth_lat=55.7558, birth_lon=37.6173, birth_tz='Europe/Moscow', birth_time_precision='exact', idempotency_key='550e8400-e29b-41d4-a716-446655440000'); print(p.model_dump_json())"
```

## 9. Expected evidence
- `git diff --name-only` — только 1 файл
- Импорт schemas — успешно
- PartnerCreate serialization — успешно, camelCase output

## 10. Escalation rule
Нужен соседний scope (API, services, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
