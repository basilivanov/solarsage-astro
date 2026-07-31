# P1 CONTRACT FIX TZ — legal `mainEvent + impulses` quiet composition

Дата: 2026-07-31
Статус: implementation packet
Depends on: `04_W2_W3_RUNTIME_CONTRACT_TZ.md`,
`03_W7_FRONTEND_DESIGN_TZ.md`, commit `5fe2ff3a`.

## 1. Причина

Новый wire root уже принят, но текущий `TodayConvergencePayload` содержит
лишний validator `quiet_main_impulses_exclusive`. Он противоречит утверждённой
presentation-композиции: W7 fixture 8 определяет
`main_event + 3 impulses + lookahead` как максимальный legal quiet payload.

Runtime §3.3 запрещает `mainEvent` только вместе с `convergences`; запрета на
одновременные `mainEvent` и `impulses` нет. `mainEvent` — отдельное редкое
событие, импульсы — дополнительные строки того же quiet-day. Это не меняет W1
формулу, caps, event ledger, sphere union или narrative rules.

`convergence_today` по-прежнему не принимает `mainEvent` и wire-массив
`impulses`: его детальные строки принадлежат convergence/event evidence.

## 2. Exact write scope

Разрешено менять только:

1. `apps/api/app/schemas/today_convergence.py`;
2. `apps/api/tests/test_today_convergence_contract.py`;
3. `grace/verification-matrix.md`;
4. этот packet — reviewer-owned, не редактировать.

Нужен иной файл — остановиться и доложить. Commit/push запрещены кодеру.

## 3. Required change

1. Удалить только fail-closed ветку
   `quiet_main_impulses_exclusive` из root validator.
2. Сохранить все остальные инварианты:
   - quiet не содержит `convergences`;
   - caps: `mainEvent <= 1`, `impulses <= 3`;
   - union presentation spheres `<=3`;
   - каждый referenced event существует, а `events` не содержит лишних строк;
   - `lookahead` разрешён только quiet;
   - narrative claims ссылаются только на selected events;
   - unavailable/preview/locked ничего не раскрывают;
   - hero по-прежнему запрещает `mainEvent`, `impulses`, `lookahead`.
3. Переименовать существующий test, который объявляет exclusivity, и заменить
   отрицательную проверку положительной максимальной композицией:
   `mainEvent + 3 impulses + lookahead`. Использовать четыре уникальных event
   IDs, не более трёх сфер и valid exact-time records.
4. Добавить отдельную отрицательную mutation-проверку: тот же payload с
   четвёртой сферой обязан fail-closed по `sphere_union_cap`. Это доказывает,
   что снята только ошибочная exclusivity, а не presentation guardrail.
5. Обновить соответствующую W2 contract-строку verification matrix короткой
   фразой о legal maximum quiet composition.

Generated OpenAPI/TS/Zod вручную не редактировать: model shape не меняется,
меняется только semantic validator. `contracts:check` обязан подтвердить 0 drift.

## 4. Acceptance

Обязательные команды:

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_contract.py -q
cd ../..
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/schemas/today_convergence.py \
  apps/api/tests/test_today_convergence_contract.py
pnpm contracts:check
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

Acceptance:

- maximum legal quiet payload валиден;
- mutation с четвёртой presentation sphere отклоняется;
- старые state/access/content/event/narrative tests зелёные;
- generated contracts не изменились;
- exact scope соблюдён, commit/push не выполнены.

## 5. Out of scope

- selector, units, groups, tone, adapter, snapshot и DB;
- изменение hero composition;
- новое wire-поле или compatibility alias;
- изменение W1 canon/formula;
- ручная правка generated contracts.
