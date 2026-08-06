# S8 TZ — check-in persisted migration + schemas

## packet title
S8-checkin-migration

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- checkin schemas/service (`apps/api/app/schemas/checkin.py`, service, db model)
- frontend checkin (`components/checkin/checkin-screen.tsx`)

## goal
`evening_checkins.observed_spheres` (JSON) переезжает на новые ключи:
`money→finance`, `shopping→finance`, `decisions` удаляется из списка, дедуп.
Pydantic/frontend — новый union.

## exact write scope
- `apps/api/alembic/versions/` новая data-migration
- `apps/api/app/schemas/checkin.py`
- check-in service/endpoint при необходимости
- `components/checkin/checkin-screen.tsx` (убрать временный cast из прототипа)
- тесты checkin (unit + postgres)

## frozen / out-of-scope
- convergence services, narrative, sphere page, contracts generation (S5)
- другие таблицы и миграции

## must-preserve invariants
- Миграция идемпотентна и безопасна на пустой таблице (no-op).
- Неизвестные ключи: НЕ угадывать — миграция считает их и падает с отчётом
  (fail), чтобы владелец решил; в тестах это покрыть.
- Дедуп после mapping: ["money","shopping"] → ["finance"].
- max_length=12 и unique-валидация сохраняются.

## Требования
1. Preflight: SQL/count по значениям money/decisions/shopping в
   `evening_checkins.observed_spheres` на dev БД — выполнить и приложить вывод
   (через DATABASE_URL из .env; psql или python). Если таблица пуста — миграция
   всё равно создаётся как безопасный no-op.
2. Alembic data-migration: money→finance; shopping→finance; decisions —
   удалить из массива; дедуп; неизвестные ключи → fail с count.
3. `CanonicalSphere` использование в checkin.py — новый union (после S4 он уже
   обновлён в today_convergence.py; если checkin имеет свой union — обновить).
4. `checkin-screen.tsx`: убрать prototype cast; observedSpheres типизируются
   новым union напрямую.
5. Тесты: mapping/dedup/unknown-fail (unit + postgres lineage suites зелёные).

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/ -q -k "checkin"
cd /opt/solarsage-astro && npx vitest run __tests__/components/checkin 2>/dev/null || true
```

## expected evidence
- preflight count вывод; diff; pytest вывод; SQL миграции в отчёте.

## escalation rule
Если observed_spheres используется ещё где-то (checkin summary/insight
генерация) и там старые ключи — стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
