# S7 TZ — sphere context service: synthesis/note + тексты + drilldown endpoint removal

## packet title
S7-sphere-context

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- sphere page service (`apps/api/app/services/today_sphere_page_service.py`)
- drilldown endpoint (`apps/api/app/api/today_sphere_drilldown.py` + схема)
- генератор натальных абзацев (найти: тексты «в prefixes у знака», «в знак Страсти»)

## goal
`GET /api/spheres/<key>` отдаёт содержательный контекст на НОВЫХ 12 ключах:
`periodSynthesis` (сумма одновременных периодов сферы), per-period `note`
(человеческое объяснение планеты/техники применительно к сфере), натальные
абзацы без шаблонных глитчей. Неиспользуемый drilldown endpoint удалён.

## exact write scope
- `apps/api/app/services/today_sphere_page_service.py`
- `apps/api/app/api/today_sphere_drilldown.py` (удаление) +
  `apps/api/app/schemas/today_sphere_drilldown.py` (удаление) + его тесты
- генератор/шаблоны натальных текстов сферы (найти по «prefixes»/«Страсти»)
- schemas для sphere page payload (добавить periodSynthesis/note)
- тесты sphere page/context

## frozen / out-of-scope
- convergence units/groups/selection/canon (S2–S4)
- narrative service (S6), check-in (S8), frontend (S9)
- физическая формула и scoring

## must-preserve invariants
- Endpoint `/api/spheres/<key>` продолжает отдавать 200 для всех НОВЫХ 12 keys
  (finance, home_family, friends_goals; старые money/decisions/shopping → 422/404
  по существующему поведению валидации).
- Существующие поля payload (natal, period, periodIdentity, birthTimeMode,
  housesAvailable) не ломать — frontend их уже потребляет.
- Новые поля additive: `periodSynthesis: str | null`, `period[].note: str | null`.

## Требования
1. Новые ключи сфер в sphere page service (маппинг технических кластеров
   `spheres.v1.yml` → продуктовые 12 по мастер-ТЗ §4: дома и смысл).
2. `periodSynthesis`: когда активных периодов сферы ≥2 — генерировать 1-2
   предложения, что их сумма даёт; 0-1 период — допустим короткий синтез или null
   (правило зафиксировать в коде).
3. `period.note`: человеческое объяснение планеты/техники периода применительно
   к сфере (см. примеры в `__tests__/fixtures/today_convergence_v2/17_spheres_facets_finance.json`
   → `__sandboxSphereContext` — это одобренные владельцем формулировки, брать за
   образец тона; LLM или детерминированные шаблоны — по существующей архитектуре
   сервиса).
4. Починить шаблонные глитчи натальных текстов: «в prefixes у знака»,
   «в знак Страсти со Сагитария», «Четвёртая часть домов», «ответственой».
   Добавить регрессионный тест: сгенерированные тексты не содержат английских
   шаблонных остатков (prefixes, «знак Страсти», «часть домов» паттерны).
5. Удалить `today_sphere_drilldown.py` endpoint + его Pydantic-схему + тесты
   (frontend его не вызывает — проверить grep'ом перед удалением и приложить
   доказательство в отчёт). Убрать route registration и OpenAPI-схему.

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/ -q -k "sphere"
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence
- diff; pytest вывод; пример JSON фрагмента с periodSynthesis и note для finance;
  grep-доказательство, что drilldown endpoint не используется фронтендом.

## escalation rule
Если генерация synthesis/note требует нового LLM-пайплайна (а не расширения
существующего) — стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
