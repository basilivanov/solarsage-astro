# C5_TZ: sidecar-owned planet.house + API fallback (Release A)

## 1. Packet title
Corrective wave, срез C5: sidecar `/v1/natal` отдаёт house каждой планеты; API fallback с честным house=null; cache version bump.

## 2. Phase / Wave
Post-synastry-live corrective, Release A. Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (§10, §13 S12-S16 — читать обязательно). Закрывает известный баг #2 из AGENTS.md.

## 3. Modules
- `apps/solarsage/solarsage/utils/houses.py` (новый)
- `apps/solarsage/solarsage/services/natal.py`
- `apps/solarsage/solarsage/schemas/natal.py`
- `apps/api/app/services/natal_context_service.py`
- `apps/api/app/services/normalization_service.py`

## 4. Goal

### 4.1. Sidecar (§10.1)
- `apps/solarsage/solarsage/utils/houses.py::find_house(longitude, cusps) -> int | None`: сортировка по cusp, wrap-around, `[cusp, next)` — планета ТОЧНО на cusp принадлежит начинающемуся дому; пустые/невалидные → None; только 1..12. GRACE-разметка + owned tests (S14 кейсы: точный cusp, wrap interval, пустой список).
- `NatalService.calculate_natal_chart()`: после расчёта houses добавить `house` в КАЖДУЮ позицию планеты (копии, исходные ephemeris dict не мутировать). Если houses не рассчитаны/невалидны — house=None, НЕ выдумывать 1.
- `schemas/natal.py::Planet`: `house: int | None = Field(default=None, ge=1, le=12)` (optional для rolling compat; boundary test `/v1/natal` через реальный service path проверяет дом каждой планеты, БЕЗ fixture-подмешивания).

### 4.2. API compatibility (§10.2)
- `SolarSagePlanetPosition.house` — оставить optional.
- `NatalContextService`: предпочитать emitted `p.house`; fallback — вычислить через API `find_house` из validated cusp (существующий `_find_house` в normalization_service; house=None → НЕ создавать ложный `planet_in_house` signal).
- `NormalizationService._planets_in_houses()`: тот же порядок (emitted → fallback), УБРАТЬ `or 1` (баг: выдуманный 1-й дом).
- Bump `CALCULATION_VERSION` natal context → старые contexts с house=null не попадают в cache hit.
- Regression: существующий paid natal entitlement по неизменному profile hash НЕ требует повторной покупки после bump (S16).

## 5. Exact write scope
- `apps/solarsage/solarsage/utils/houses.py` (новый)
- `apps/solarsage/solarsage/services/natal.py`
- `apps/solarsage/solarsage/schemas/natal.py`
- `apps/solarsage/tests/test_houses.py` (новый), `apps/solarsage/tests/test_natal.py`
- `apps/api/app/services/natal_context_service.py`
- `apps/api/app/services/normalization_service.py`
- `apps/api/tests/test_natal_context_service.py`

## 6. Frozen / Out of scope
- Credit/billing срезы (C1-C4), frontend, synastry wheel (использует свой house для partner-планет — уже есть).
- Массовая консолидация всех приватных `_find_house()` — НЕ делать (§4 master).
- Удаление API fallback — НЕ делать (будущий cleanup).

## 7. Must-preserve invariants
- House system (Placidus/Whole Sign) сохраняется (S13).
- `house=1` никогда не выдумывается при невалидных cusp.
- Старые тесты sidecar/API зелёные; GRACE-разметка; lint PASS.

## 8. Verification commands
```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_houses.py tests/test_natal.py -q
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_natal_context_service.py -q
python3 scripts/grace_lint.py apps/api/app
```

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; boundary: реальный `/v1/natal` расчёт — у всех планет house 1..12.

## 10. Escalation rule
Нужен frontend/credit scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
