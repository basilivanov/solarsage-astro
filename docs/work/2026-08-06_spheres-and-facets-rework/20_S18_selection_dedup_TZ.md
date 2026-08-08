# S18 TZ — selection: дедупликация дублирующихся convergence-групп

## packet title
S18-selection-duplicate-presentation-dedup

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-CONVERGENCE-SELECTION (`apps/api/app/services/today_convergence_selection.py`)

## Контекст

Живой кейс (08-30, аккаунт владельца): день convergence_today, выбраны 3
группы, у всех троих `sphere=work, facet=daily_work`, у всех одна и та же
evidence-пара (`evt_…294` + `evt_…35877`). Различаются только member-наборы
(9/15/16 событий — перекрывающиеся звёзды вокруг одного локуса). Итог: три
почти одинаковые карточки с одинаковым текстом — мусор для пользователя.

Механика: `_star_candidates` строит звезду на каждый anchor_today;
перекрывающиеся (но не идентичные) звёзды дают разные group_id;
`_selected_convergences` (today_convergence_selection.py:373-415) берёт top-3
по рангу без какого-либо diversity-правила.

## goal

В `selected.convergences` не может попасть две группы:
1. с одинаковой парой `(sphere, facet)`;
2. с одинаковой evidence-парой (сравнение как множеств, порядок не важен).

Дедупликация идёт до расходования слота cap-3: отброшенный дубль не занимает
место, следующая по рангу разнообразная группа поднимается.

## exact write scope

- `apps/api/app/services/today_convergence_selection.py`
- `apps/api/tests/test_today_convergence_selection.py`
- другие тесты convergence-контура, если упадут на новом поле audit
  (только обновление shape-assertions, без ослабления поведенческих проверок)

## frozen / out-of-scope

- grouping (`today_convergence_groups.py`), tone, pipeline, snapshot,
  projection, narrative, frontend — без изменений;
- `_group_rank`, `_evidence_pair`, hero-first ordering, quiet-path —
  семантика без изменений;
- wire-контракт (`selected` payload shape) — без изменений; audit JSON
  получает одно новое поле (см. ниже) — это audit-only, не публичный контракт.

## Требования к реализации

1. В цикле отбора `_selected_convergences` завести
   `selected_facet_keys: set[tuple[str, str | None]]` и
   `selected_evidence_pairs: set[frozenset[str]]`; кандидат пропускается
   (continue), если его `(group.sphere, group.facet)` уже в set'е или
   `frozenset(pair)` уже в set'е. Пропуск считается отдельным счётчиком,
   НЕ `selection_cap_exclusions`.
2. `CanonicalSelectionAudit`: новое поле
   `duplicate_presentation_exclusion_count: int` (заполнить в обоих местах
   конструирования — convergence и quiet ветках; в quiet всегда 0).
   Сериализация в deterministic_result идёт через
   `_safe_json_value(selection.audit)` (today_convergence_snapshot.py:421) —
   поле протечёт автоматически, snapshot-код не трогаем.
3. Порядок проверок в цикле: сначала дедуп, потом cap (дубль не ест слот).
4. GRACE-разметка: обновить FUNCTION_CONTRACT `_selected_convergences`
   (purpose/audit) и MODULE_CONTRACT invariants при необходимости.
5. Тесты (минимум):
   - две группы с одинаковым (sphere, facet), разный ранг → выбрана только
     лучшая, `duplicate_presentation_exclusion_count == 1`, третий слот
     заняла следующая разнообразная группа;
   - две группы с разным facet, но идентичной evidence-парой → вторая
     отброшена (crafted fixtures допустимы);
   - группы с разными (sphere, facet) и разными evidence-парами → все
     выбраны, счётчик 0 (существующее поведение не сломано);
   - quiet-day путь: счётчик 0, поведение без изменений;
   - существующие selection-тесты зелёные.

## must-preserve invariants

- `hero_without_public_polarity` fail-closed без изменений;
- состояние `convergence_today` требует ≥1 hero среди выбранных — без изменений;
- детерминизм: одинаковый вход → одинаковый выход (дедуп детерминирован
  порядком `ordered`);
- evidence pair в payload сохраняет порядок anchor → confirmation;
- audit JSON: только добавление одного поля, существующие ключи не переименовывать.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_today_convergence_selection.py tests/test_today_convergence_snapshot.py tests/test_today_convergence_pipeline.py tests/test_today_convergence_runtime.py tests/test_day_convergence_api.py -q
python3 scripts/grace_lint.py apps/api/app
```

Если падают replay/fingerprint тесты на новом audit-поле — СТОП, доложить
ревьюеру (baseline regeneration — решение ревьюера, не кодера).

## expected evidence

- diff scope-файлов; вывод pytest (зелёный); список новых тест-кейсов;
  явное подтверждение, что audit получил ровно одно новое поле.

## escalation rule

Потребовалось менять grouping/tone/pipeline/snapshot/projection или
replay-baseline — СТОП, доложить ревьюеру.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
