# S14 TZ — boundary: GET /api/day/{past_date} без снапшота отдаёт 200 unavailable, не 500

## packet title
S14-day-past-date-boundary

## Phase / Wave
W-SPHERES-FACETS-REWORK

## Modules
- M-API-DAY

## Контекст (найдено ревьюером на dev после S13)

`GET /api/day/{past_date}` для даты в прошлом, по которой у пользователя нет
снапшота, падает с HTTP 500:

```
app.services.today_snapshot_service.TodaySnapshotLineageError: today_snapshot:past_target
```

Механика: `load_current` miss → расчёт → `publish_or_load` /
`publish_superseding` → lineage-инвариант «снапшоты публикуются только для
сегодня/будущего» → исключение улетает в 500. До S13 это маскировалось
selection-багом (расчёт падал раньше). Маршрут `/day/[date]` публичный,
календарь ведёт на него по клику (`components/calendar/calendar-screen.tsx`
→ `app/(grace)/calendar/page.tsx` onOpenDay → `router.push(/day/{date})`),
прошлые даты кликабельны.

Желаемое поведение: прошлая дата без снапшота — честный
`state=unavailable` (HTTP 200), тот же payload что при calculation failure
(`project_empty_payload(unavailable=True)`). Прошлая дата С существующим
снапшотом — рендерится как раньше (не ломать).

## goal

`GET /api/day/{date}` для локальной прошлой даты пользователя без снапшота
возвращает 200 `state=unavailable`; 500 `today_snapshot:past_target`
недостижим через публичный endpoint.

## exact write scope

- `apps/api/app/api/day.py`
- `apps/api/tests/test_day_convergence_api.py`

## frozen / out-of-scope

- `today_snapshot_service.py` и lineage-инвариант — НЕ трогать (инвариант
  правильный, меняем границу endpoint'а).
- selection/runtime/projection/frontend — НЕ трогать.
- Запрос прошлой даты с существующим снапшотом — поведение не менять.

## Требования к реализации

1. В `_serve_day` (или уровень оркестрации GET/retry) после `load_current`:
   если снапшота нет (или требуется supersede) И `target_date` раньше
   локальной текущей даты пользователя — вернуть
   `project_empty_payload(..., unavailable=True)` с `_viewed_payload`, как на
   ветке calculation failure. Локальную «сегодняшнюю» дату брать тем же
   resolver'ом, что уже используется в этом модуле (user local date).
2. Никаких новых типов ошибок наружу; лог — существующий `day.viewed`
   (state=unavailable), без system.error (это не сбой, а ожидаемая граница).
3. Retry-ветка (`retry_day`) для прошлых дат — то же поведение (не 500).
4. GRACE-разметка: обновить FUNCTION_CONTRACT затронутых функций
   (`error_behavior` больше не «calculation failure is HTTP 200 unavailable»
   только — добавить past-date boundary).

## must-preserve invariants

- Снапшоты по-прежнему не публикуются для прошлых дат.
- Сегодня/будущее — поведение байт-в-байт (snapshot publish, narrative lease).
- Прошлая дата со снапшотом — рендерится из снапшота.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_day_convergence_api.py -q
```

Ручной smoke на dev после рестарта (делает ревьюер): свежий пользователь,
`GET /api/day/<вчера>` → 200 `state=unavailable`, `GET /api/day/<сегодня>` →
200 `quiet_day|convergence_today`.

## expected evidence

- Дифф двух файлов.
- Тесты: (а) прошлая дата без снапшота → 200 unavailable, без публикации;
  (б) прошлая дата со снапшотом → рендер из снапшота; (в) сегодня без
  снапшота → publish как раньше.
- Вывод pytest.

## escalation rule

Если граница оказывается не в day.py (например, resolver локальной даты не
отдаёт «сегодня» для сравнения) — СТОП, доложить, новый packet.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
