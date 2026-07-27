# V1 TZ: canon day_valence.v1.yml + схемы M-SCHEMAS-DAY-VALENCE + no-drift baseline

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V1
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §5–6, 9.1
Modules: новые `M-SCHEMAS-DAY-VALENCE`, canon loader
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Константы и типы valence v1 существуют как валидируемый canon и pydantic
схемы; параллельно захвачен golden текущего horizon selection (baseline
no-drift до любых scoring-изменений).

## 2. Exact write scope

- `grace/canon/day_valence.v1.yml` — **новый canon** (константы §6
  нормативного ТЗ): aspect_weight, planets weights (из `spheres.v1.yml`,
  значения эквивалентны), technique_families independence_weight (из
  `activation_rules.v1.yml`), polarity maps (§6.1), family decay
  [1.0, 0.5, 0.25], technical→product mapping (таблица §6.5, значения
  эквивалентны текущему horizon mapping), verdict thresholds §6.6,
  confidence thresholds, day status thresholds §6.7.
- `apps/api/app/schemas/day_valence.py` — **новый**
  `M-SCHEMAS-DAY-VALENCE`: `DayValenceFactor`, `ProductSphereAssessment`,
  `SphereValenceRead`, `DayStatusBreakdown` (точно по §5.1/6.6/6.7/9.1).
- `apps/api/app/services/canon_service.py` (или существующий loader) —
  загрузка/валидация нового canon при startup, fail-closed при отсутствии
  констант. Hidden fallback запрещён.
- `apps/api/tests/test_day_valence_schemas.py` — schema/loader unit tests.
- `apps/api/tests/fixtures/day_valence/` — директория для fixtures (пока пустая или README).
- **No-drift baseline**: скрипт/тест, фиксирующий текущий horizon selection
  (selected IDs + timing ranges + impact) на существующей mapping-equivalent
  fixture → golden в `apps/api/tests/fixtures/day_valence/horizon_selection_baseline.json`.
  Использовать существующую horizon fixture из текущих тестов
  (`rg -l "HorizonSelectionService" apps/api/tests` — взять её входы).

## 3. Frozen / out-of-scope

- Никакой логики valence (это V2/V3), никаких изменений runtime-сервисов.
- `spheres.v1.yml`, `activation_rules.v1.yml` — не править (canon-ссылки,
  не дубликаты значений в новом файле, если loader умеет compose; иначе
  скопировать значения с комментарием-источником).
- Frontend, contracts regen (пока не нужен — public payload не меняется).

## 4. Must-preserve

- Startup validation fail-closed; `grace_lint` PASS; GRACE-разметка.
- Эквивалентность значений существующим canons (тест сравнения с
  `spheres.v1.yml` / horizon mapping, если compose не используется).

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_valence_schemas.py -q
```

## 6. Expected evidence

- Файлы, вывод verification, путь к horizon_selection_baseline.json
  и его selected IDs.

## 7. Escalation rule

Нужен runtime-файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
