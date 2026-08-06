# S3 TZ — units + group projection sphere/facet

## packet title
S3-units-group-projection

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-CONVERGENCE-UNITS (`apps/api/app/services/today_convergence_units.py`)
- M-TODAY-CONVERGENCE-GROUPS (`apps/api/app/services/today_convergence_groups.py`)

## goal
`CanonicalUnit` хранит `technical_spheres` (новое поле) и больше не хранит
`product_spheres`; после формирования physical group resolver из S2 записывает
в неё `sphere`/`facet`; `primary_sphere`/`secondary_sphere` удалены. Физическая
группировка, identity, hero — без изменений.

## exact write scope
- `apps/api/app/services/today_convergence_units.py`
- `apps/api/app/services/today_convergence_groups.py`
- `apps/api/tests/test_today_convergence_units.py`
- `apps/api/tests/test_today_convergence_groups.py`
- при необходимости минимальная правка вызовов в `today_convergence_projection.py`
  ТОЛЬКО чтобы код компилировался/тесты шли (семантика selection — S4)

## frozen / out-of-scope
- `today_convergence_selection.py` (S4), `today_convergence_tone.py`, narrative,
  schemas, frontend
- significance/eligibility/orb/birth-time rules; canonical_event_id; group_id
  (только member IDs); direct-star/independence/hero C1
- `grace/canon/**` (готово в S2)

## must-preserve invariants
- canonical event IDs и group IDs байт-в-байт не меняются на одинаковых входах.
- Producer duplicate не создаёт дополнительный голос.
- Перестановка входных фактов не меняет результат (детерминизм).
- Unmapped factor → исключается на unit-этапе как сейчас (fail-closed).

## Требования
1. `CanonicalUnit`: удалить `product_spheres`; добавить `technical_spheres: tuple[str, ...]`
   (нормализованные, как в RawPhysicalFact); сохранить house/source/target/theme keys
   и physical fields; не вычислять product sphere на unit-build boundary.
   Обновить MODULE_CONTRACT в шапке.
2. `today_convergence_groups.py`: после формирования валидной physical group —
   вызов resolver'а (S2, из canon-модуля) по агрегированным данным группы;
   в `CanonicalConvergenceGroup` записать `sphere: str` и `facet: str | None`;
   удалить `primary_sphere`/`secondary_sphere` и `_project_spheres` majority-логику;
   unresolved → группа не публикуется, инкремент существующего
   `group_without_sphere_count`; группа не клонируется.
3. Тесты (мастер-ТЗ §9.1): unit хранит technical_spheres без product sphere;
   sphere/facet не входят в identity; 2 дом → finance/personal_money;
   8 дом без контекста ≠ obligation; 3/9 по контексту (travel/study/documents/communication);
   Уран без 3/9 ≠ travel; Нептун/Уран без 5 ≠ creativity; две группы одной sphere
   остаются двумя; все существующие direct-star/C1/permutation/duplicate тесты зелёные.

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/test_today_convergence_units.py tests/test_today_convergence_groups.py -q
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence
- diff; вывод pytest; подтверждение, что group_id не изменился на существующих
  тестовых кейсах (детерминизм-тесты зелёные без ослабления assert'ов).

## escalation rule
Нужны изменения в selection/schemas, чтобы собрать тесты — стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
