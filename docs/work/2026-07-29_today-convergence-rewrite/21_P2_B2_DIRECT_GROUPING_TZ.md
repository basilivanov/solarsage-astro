# P2-B2 CONTROLLER PACKET — Direct grouping, independence, hero and spheres

Phase / Wave: **P2 · W2-S2 deterministic convergence pipeline**

Modules: `M-TODAY-CONVERGENCE-GROUPS`, `M-TODAY-CONVERGENCE-LEDGER`,
`M-TODAY-CONVERGENCE-UNITS`, `M-TODAY-CONVERGENCE-CANON`, `M-TESTS`,
`M-GRACE-PROJECT-ADAPTER`.

## Goal

Добавить pure слой физической группировки поверх принятого canonical ledger:
anchor-seeded direct stars без транзитивных мостов, независимость только по
`driver_key`, норматив C1 для hero и проекция каждой физической группы ровно в
одну primary и максимум одну secondary sphere.

Результат packet — все deterministic medium/hero groups и immutable audit. Он
не выбирает публичные 0..3 карточки, не считает polarity/dayTone, не строит
quiet/mainEvent/impulses и не интегрируется с legacy Today.

## Authoritative inputs

- `00_MASTER_TZ.md` D7, §4.3–4.6, T1 и mutation fixtures 1/3/4/5;
- `grace/canon/today_convergence.v1.yml::independence/grouping/hero_rule/sphere_projection`;
- P2-A/P2-B0/P2-B1 production records;
- frozen reference `analysis/ablation_harness.py::_connected`,
  `_star_groups`, `_hero_anchor_and_confirmation`, `project_group_spheres`;
- `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` P2.

## Exact write scope

Кодер может создавать/изменять только:

1. `apps/api/app/services/today_convergence_groups.py` (new);
2. `apps/api/tests/test_today_convergence_groups.py` (new);
3. `grace/verification-matrix.md`;
4. `grace/knowledge-graph.xml`.

Файл этого packet не редактировать. Нужен иной файл — остановиться и доложить.

## Required implementation

### 1. Typed immutable result

Ввести frozen records:

- `CanonicalConvergenceGroup` — `group_id` (`cvg_v1_…`), selected anchor ID,
  sorted unique member `CanonicalUnit` tuple, sorted independent driver keys,
  optional hero anchor/confirmation IDs, `hero_eligible`, `evidence_level`
  (`high|medium`), primary sphere и optional secondary sphere;
- `CanonicalGroupingResult` — deterministic tuple групп + audit;
- `CanonicalGroupingAudit` — минимум: ledger unit count, public evidence pool
  count, today-anchor count, candidate-star count, duplicate-star count,
  group count, hero/medium counts, background/ineligible exclusions,
  insufficient-independence count и group-without-sphere count;
- `TodayConvergenceGroupingError` только для programming misuse или нарушения
  уже гарантированных ledger invariants.

`group_id` — versioned deterministic hash canonical member-ID set. Producer,
provenance, sphere fan-out и input order в identity группы не входят. Одинаковый
набор физических members означает одну группу.

### 2. Public member pool and direct relation

- В member pool входят только `evidence_eligible=true`,
  `exclusion_reason=null`, `temporal_role!=background`.
- Audit-only/background/time-sensitive/insignificant units сохраняются в
  ledger, но не входят в группу, не свидетельствуют и не соединяют её.
- Seed — каждый unit member pool с `temporal_role=anchor_today`.
- Прямая связь двух units: одинаковый непустой `target_key` **ИЛИ** непустое
  пересечение canonical `theme_keys`.
- Star seed содержит seed + только units, прямо связанные с seed. Запрещено
  добавлять C через мост A→B→C, если C не связан напрямую с seed A.
- Идентичные member-ID star sets дедуплицируются до одной группы независимо от
  порядка ledger units/anchors.

### 3. Independence and group validity

- Независимость — только distinct non-empty `driver_key` из canon rule B.
- Валидная medium group требует минимум один `anchor_today` и минимум два
  независимых driver keys.
- Два raw/producer дубля уже сведены ledger и не могут повысить independence.
- Две единицы одного driver/horizon не становятся двумя свидетельствами.
- Group anchor выбирается детерминированно: hero anchor, если C1 выполнен;
  иначе strongest today's anchor; tie-break `target_salience` затем event ID.

### 4. Hero C1

Hero только если внутри одной direct star найдена пара:

1. rare anchor: `temporal_role=anchor_today`,
   `rare_anchor_eligible=true`, `target_type` входит в
   `canon.hero_target_types`;
2. прямое к нему подтверждение: другой physical unit,
   `hero_confirmation_eligible=true`, non-background, другой `driver_key`;
3. confirmer должен быть связан прямо с rare anchor, а не только с другим
   member группы.

Rare anchors сортируются `strength desc → target_salience desc → event ID`;
confirmers так же. Первая пара — canonical. Fast Moon/Mercury/Venus могут быть
medium evidence/member, но C1 v1 не могут занять confirmation slot. Lot-target
rare anchor остаётся medium, не hero. Два обычных лунных аспекта не hero.

`hero_eligible=true` ↔ `evidence_level=high`; иная валидная group ↔ `medium`.
Не вводить квоты/frequency heuristics.

### 5. Group-level sphere projection

- Каждый member даёт максимум один vote каждой своей `product_spheres`; один
  physical unit не дублируется по producer или presentation sphere.
- Primary: большинство votes; tie → sphere выбранного anchor; затем порядок
  `canon.canonical_spheres`.
- Secondary: следующий по тому же ranking, только если имеет минимум два
  member votes; максимум один, не равен primary.
- Результат группы всегда содержит 1..2 сферы. Если ledger invariant нарушен и
  votes нет — группа не публикуется, растёт `group_without_sphere_count`.
- Одна группа не клонируется отдельно под каждую сферу.

### 6. Determinism and validation

- Members внутри группы sorted unique by `canonical_event_id`; группы sorted
  by `group_id`.
- Перестановка ledger units даёт byte-equivalent result.
- Дубликат canonical event ID в переданном `CanonicalLedger` — typed misuse,
  а не тихий второй vote.
- Public entrypoint принимает только `CanonicalLedger` и optional validated
  `TodayConvergenceCanon`; default canon загружается strict loader.

## Frozen / out of scope

- Не менять canon/YAML, unit или ledger semantics.
- Не считать unit/group polarity или dayTone.
- Не ранжировать/обрезать groups до 0..3 и не строить presentation state,
  mainEvent, impulses, context или wire models.
- Не реализовывать producer adapter, replay parity, snapshots, DB, API, LLM,
  pregen или frontend.
- Не использовать connected components/transitive closure и не группировать
  сначала по сферам.
- Не импортировать legacy Today, analysis, DB, logger, HTTP или sidecar.

## Tests / acceptance

Тесты обязаны доказать:

1. shared target создаёт medium group только при двух distinct drivers;
2. theme intersection связывает, disjoint themes не связывают;
3. background/ineligible unit не member, witness или bridge;
4. supporting B не протаскивает C в seed A через A→B→C;
5. producer duplicate не повышает independence, удаление второго независимого
   unit разрушает ровно двух-unit group;
6. rare today's planet/angle anchor + direct slow confirmation → hero/high;
7. fast confirmation и lot-target rare anchor остаются medium, не hero;
8. hero confirmer обязан быть прямым к rare anchor;
9. sphere majority, anchor tie-break, canonical-order tie-break, secondary
   threshold и cap ≤2 работают per group;
10. один multi-sphere member не клонирует physical group;
11. input permutation, identical-star dedup, stable group IDs/order и frozen
    records;
12. duplicate ledger ID/malformed API дают typed error;
13. P2-A/B0/B1 focused suites остаются зелёными.

## GRACE sync

- Register `M-TODAY-CONVERGENCE-GROUPS` и edges к ledger/canon.
- Add `UC-TODAY-CONVERGENCE-W2-GROUPS` с direct-star, C1, independence и
  per-group sphere gates. Не выдавать packet за tone/presentation completion.

## Verification commands

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py \
  tests/test_today_convergence_ledger.py \
  tests/test_today_convergence_groups.py -q

cd /tmp/solarsage-convergence-impl
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_groups.py \
  apps/api/tests/test_today_convergence_groups.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## Expected evidence

Exact changed paths; focused test count; direct-star bridge-negative example;
hero fast-confirmation negative; per-group sphere-vote example; permutation and
duplicate-ID evidence; audit example; Ruff/GRACE/markers/diff/status results.

## Escalation and no-commit rule

Если W1 canon недостаточен для C1/direct link/sphere tie-break либо требуется
изменить ledger/unit/canon — **остановиться** и доложить, не изобретать новую
формулу.

**Ничего не коммить и не пушить — коммит и push делает ревьюер.**
