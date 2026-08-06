# S4 TZ — selection + wire validators + schema v2

## packet title
S4-selection-wire

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-CONVERGENCE-SELECTION (`apps/api/app/services/today_convergence_selection.py`)
- M-TODAY-CONVERGENCE-PROJECTION (`apps/api/app/services/today_convergence_projection.py`)
- schemas (`apps/api/app/schemas/today_convergence.py`)

## goal
Selector больше не отбрасывает группу из-за повторной sphere; wire-контракт
принимает repeated sphere; payload несёт `sphere`/`facet` вместо
`primarySphere`/`secondarySphere`; schema_version 1→2.

## exact write scope
- `apps/api/app/services/today_convergence_selection.py`
- `apps/api/app/services/today_convergence_projection.py`
- `apps/api/app/schemas/today_convergence.py`
- связанные тесты selection/projection/wire (apps/api/tests/test_today_convergence_*)

## frozen / out-of-scope
- units/groups/canon (S2/S3), narrative (S6), frontend (S9), fixtures (S5)
- ранжирование по evidence/strength/time — не менять
- quiet-day лимиты: main 0..1 + impulses 0..3 (до 4 блоков) — сохранить
- convergence cap = 3 группы — сохранить

## must-preserve invariants
- group polarity и dayTone не меняются (формула tone не трогается).
- `selected_spheres` — уникальный упорядоченный список сфер выбранных сигналов
  (finance дважды → finance один раз в списке).
- Остальные fail-closed wire validators (event-reference, content-state,
  time-precision) сохранить.

## Требования
1. `today_convergence_selection.py`: удалить sphere-diversity gate
   (`group_sphere_set.difference(selected_sphere_set)` → continue) и cap на
   3 distinct spheres; то же для quiet-day path (`_presentation_sphere` и
   quiet caps по сферам); quiet-day events получают sphere/facet тем же
   resolver'ом (S2), а не `min(product_spheres)`; `sphere_cap_exclusion_count`
   удалить/переосмыслить в audit.
2. `apps/api/app/schemas/today_convergence.py`: удалить `primarySphere`/
   `secondarySphere` из всех моделей; добавить `sphere: CanonicalSphere`,
   `facet: str | None`; `CanonicalSphere` = новый union 12 ключей (finance,
   home_family, friends_goals; без money/decisions/shopping); удалить
   валидаторы `group_sphere_distinct` и `sphere_union_cap`;
   `schema_version: Literal[2]`; `formula_version` оставить;
   `calculation_version` bump.
3. `today_convergence_projection.py`: wire-проекция групп/событий с
   sphere/facet; `selected_spheres` как уникальный список.
4. Тесты (мастер-ТЗ §9.2): supportive personal_money + tense
   financial_obligations выбираются одновременно; repeated finance не
   исключается; cap=3 convergence групп; quiet main+3; selected_spheres
   уникален; wire принимает repeated sphere; tone не изменился.

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/test_today_convergence_selection.py tests/test_today_convergence_projection.py -q 2>/dev/null || .venv/bin/python -m pytest tests/ -q -k "selection or projection or wire"
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence
- diff; pytest вывод; фрагмент теста, доказывающего coexist двух finance-сигналов.

## escalation rule
Изменение ранжирования или tone — стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
