# S15 TZ — hotfix: пустые quiet-дни и коллапс сфер (target-house + resolver)

## packet title
S15-target-house-resolver-hotfix

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-ACTIVATION-BUILDER (sidecar, `apps/solarsage/solarsage/services/activation_builder.py`)
- M-TODAY-BIRTH-TIME-FACTS (`apps/api/app/services/today_birth_time_facts.py`)
- M-TODAY-CONVERGENCE-CANON (`apps/api/app/services/today_convergence_canon.py`)
- M-TODAY-CONVERGENCE-GROUPS (`apps/api/app/services/today_convergence_groups.py`)
- `grace/canon/product_spheres.v1.yml`

## Диагностика (воспроизведено на dev, аккаунт владельца tg 833478509)

Симптом: за август 2026 ни одного дня с сигналами; все дни `quiet_day` с
пустым main/impulses, хотя физика богатая (31–41 accepted unit, 1–8 групп/день).

Аудит selection по 24 свежим снапшотам (canon bbba505b):
`candidate_convergence_count` 1–8 каждый день, `selected_convergence_count` = 0
везде, кроме 2026-08-30 (hero-день, 3 конвергенции). Quiet-path:
`selected_event_count` 0–2, при том что свежие (anchor_today) юниты есть
ежедневно (Луна/Солнце/Меркурий exact сегодня).

Три независимых корня:

### B1. Resolver house-path мёртв для транзитных юнитов
Sidecar (`activation_builder.py`) заполняет `house` только для
`transit_planet_in_house` и return/profection event-class'ов. Для
`transit_to_natal` / `transit_to_angle` / `transit_to_lot` поле `house=None`,
хотя натальные дома и долготы целей в builder'е доступны (`natal_houses_raw`,
`natal_by_name`, lots[].house). Приоритет №1 resolver'а (мастер-ТЗ §5:
house → technical → context → planets) не работает: юниты падают в
context-path. Доказательство what-if симуляции: после подстановки натального
дома цели quiet-импульсы появляются каждый день (2–4/день) в разных сферах
(sport, relationships, home_family, documents).

### B2. Resolver: planet-modifier перебивает house-derived сферу
Ветка `not contextual and planets` в `resolve_product_sphere`
(`today_convergence_canon.py`) выбирает facet из base, чья сфера НЕ входит в
eligible (`item[0] not in eligible_spheres`), по совпадению planet-modifier'а.
Это нарушает мастер-ТЗ §5 (планеты — только tie-break): дом 4 + Луна →
`documents/None` (property_documents modifier MOON) вместо
`home_family/family_roots`; дом 5 + Солнце → `sport/None` вместо
`creativity/self_expression`. Ветка подлежит удалению; tie-break планет
остаётся только внутри уже выбранных кандидатов (существующий блок
`len(selected) > 1 and planets`).

### B3. Theme→facet мост почти пустой
`map_factor_to_theme_keys` испускает 10 узких тем
(`today_convergence_themes.v1.yml`), но в `product_spheres.v1.yml` только
`direction_growth_meaning` реально присутствует в `required_context` фасета
(study/higher_education_worldview). `communication_learning_documents` и
`resources_security` висят в `allowed_context_keys` без единого фасета;
остальные 7 тем не упомянуты вообще. Следствия: (а) unit-level resolution для
режимов bucket/unknown (дома запрещены каноном) почти всегда None → quiet-день
пустой; (б) group-level resolution (union тем членов) срабатывает только через
`direction_growth_meaning` → все группы владельца коллапсируют в
`study/higher_education_worldview`.

### Out of scope (заморожено, НЕ трогать)
- D1/T5: `convergence_today` только при hero-eligible группе; medium-группы
  (2+ независимых драйвера) остаются невидимыми для state. Это owner-frozen
  решение (hero_rate ~5–10%). После фикса B1/B2 quiet-дни перестают быть
  пустыми; вопрос «показывать ли medium-группы» — отдельное продуктовое
  решение владельца, не этого пакета.
- significance/eligibility/grouping link/hero C1/tone/birth-time — без изменений.

## goal

1. Каждый transit-юнит к натальной цели несёт натальный дом цели (exact-режим;
   для control-grid режимов — только единогласный дом, иначе None).
2. Resolver следует приоритету §5: планета не может переопределить сферу,
   выбранную по дому/контексту.
3. Group sphere = дом якоря (если есть), иначе union тем членов (текущее
   поведение) — разнообразие сфер вместо коллапса в study.
4. Минимальные theme-мосты в `product_spheres.v1.yml` (только семантически
   точные), чтобы house-less режимы тоже резолвились.

## exact write scope

- `apps/solarsage/solarsage/services/activation_builder.py`
- `apps/solarsage/tests/test_activation_*.py` (соответствующие файлы)
- `apps/api/app/services/today_birth_time_facts.py`
- `apps/api/app/services/today_convergence_canon.py` (только resolve_product_sphere)
- `apps/api/app/services/today_convergence_groups.py` (только _group_house/_project_sphere_facet)
- `grace/canon/product_spheres.v1.yml` (required_context/allowed_context_keys)
- тесты: `apps/api/tests/test_today_birth_time_facts.py`,
  `apps/api/tests/test_today_convergence_canon.py`,
  `apps/api/tests/test_today_convergence_groups.py`

## frozen / out-of-scope

- hero gate, state machine, tone, grouping links, identity payload'ов
  (house остаётся частью evt_v1 identity — значения изменятся, структура нет);
- frontend, narrative, snapshots API-контракты;
- `today_convergence_themes.v1.yml` (состав тем не меняется).

## Требования к реализации

### F1 (sidecar). Аннотация дома цели
В цикле транзитов `build_activation_layer`:
- `transit_to_natal` (target_type planet): `house = _find_house(tlon_target, natal_houses_raw)`;
- `transit_to_angle`: ASC→1, DSC→7, MC→10, IC→4 (только эти четыре; прочие — None);
- `transit_to_lot`: дом лота из `lots[]` (уже вычисляется в debug).
Поля `id` активаций не меняются; `house` — additive-поле контракта
(`ActivationEvidenceContract.house` уже существует). ACTIVATION_LAYER_VERSION
не бампим? — НЕТ: содержимое ответа меняется → бампить согласно
`solarsage_contracts.versions` правилам (проверить потребителей версии).

### F2 (API facts). House robustness
В `build_birth_time_facts` при сборе `RawPhysicalFact.house` из observations:
единогласное значение по всем merged observations → публикуем; расхождение →
None. Exact-режим (1 sample) тривиально совпадает. Контракт gate канона:
«sparse может потерять, не может опубликовать неустойчивое».

### F3 (API canon). Resolver
Удалить ветку `if not contextual and planets:` cross-sphere override
(`today_convergence_canon.py`, resolve_product_sphere). Поведение после:
house/technical/context выбирают base/eligible; при отсутствии contextual —
`selected = eligible` (facet может быть None через ранние ветки); планеты —
только tie-break внутри selected. Обновить docstring/contract.

### G1 (API groups). Anchor-house проекция группы
`_project_sphere_facet`: сначала дом якоря группы (anchor unit.house, если
задан), иначе прежний union `_group_house` (все члены делят один дом), иначе
None → theme-union как сейчас. anchor передаётся в helper — сигнатура
расширяется, вызов из `build_canonical_groups` уже имеет anchor.
Group ID/membership/hero/tone/state не затрагиваются — меняются только
проецируемые sphere/facet.

### F4 (canon). Theme-мосты (минимум, семантически точные)
В `product_spheres.v1.yml`:
- `communication_learning_documents` → `everyday_contacts.required_context`
  и `skills_courses.required_context`;
- `relationships_values_closeness` → `partnership.required_context`;
- `inner_clarity_recovery` → `recovery_isolation.required_context`;
Все три ключа уже есть в `allowed_context_keys`. Пустые `required_context`
фасетов НЕ трогаем (иначе ломается house-path eligibility). Остальные темы
осознанно не мостим в v1 (diffuse) — документировать в audit-поле канона
комментарием.

## must-preserve invariants

- state/dayTone/hero/membership для фиксированного корпуса юнитов не меняются
  (меняются только house-поля юнитов, sphere/facet проекции и event IDs);
- fail-closed loader/resolver сохраняются;
- permutation-determinism resolver'а и grouping;
- bucket/unknown: дома не публикуются без единогласия (канон gate).

## verification commands

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
cd apps/api && .venv/bin/python -m pytest tests/test_today_birth_time_facts.py tests/test_today_convergence_canon.py tests/test_today_convergence_groups.py tests/test_today_convergence_selection.py tests/test_today_convergence_pipeline.py -q
```

Живой repro (владелец, exact): для дат 2026-08-08..12 после деплоя
`calculate_today_convergence` даёт quiet_day с 2–4 impulses в ≥2 разных
сферах; 2026-08-30 остаётся convergence_today.

## expected evidence

- diff'ы по scope-файлам; вывод pytest (sidecar + api);
- таблица до/после по датам владельца: state, impulses (сфера/фасет/полярность);
- подтверждение, что 08-30 convergence не деградировал.

## escalation rule

Потребовалось менять identity payload, eligibility, hero, state-машину или
frontend-контракты — СТОП, доложить ревьюеру, новый packet.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
