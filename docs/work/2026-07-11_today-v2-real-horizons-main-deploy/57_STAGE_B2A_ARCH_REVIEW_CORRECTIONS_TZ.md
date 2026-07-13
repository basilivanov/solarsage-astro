# Stage B2A — architect review corrections R1

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Parent TZ: `56_STAGE_B2A_CANON_TIMING_SELECTION_TZ.md`
Решение архитектора: **B2A не принят; commit/push запрещены до повторного review**

## 0. Роль и режим работы

Кодер исправляет только B2A. Архитектор не пишет product code и повторно
проверяет результат. Не запускать субагентов.

До отдельного acceptance запрещены:

- `git add`;
- commit;
- push;
- B2B;
- public contract/OpenAPI/frontend/sidecar/Today integration;
- изменения портов, env, systemd, nginx или preview runtime.

Preview на `3003`/`18092` оставить работающим и не перезапускать без
необходимости: эта подволна backend-internal и production behavior не меняет.

## 1. Exact allowlist correction wave

Разрешено менять только уже открытый B2A scope:

```text
grace/canon/horizon_selection.v1.yml

apps/api/app/schemas/horizon_canon.py
apps/api/app/schemas/horizon_selection.py

apps/api/app/services/canon_service.py
apps/api/app/services/horizon_canon_service.py
apps/api/app/services/horizon_timing_service.py
apps/api/app/services/horizon_sphere_mapping_service.py
apps/api/app/services/horizon_selection_service.py

apps/api/tests/test_canon_service.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_timing_service.py
apps/api/tests/test_horizon_sphere_mapping_service.py
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_horizon_selection_benchmark.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/56_STAGE_B2A_CANON_TIMING_SELECTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/57_STAGE_B2A_ARCH_REVIEW_CORRECTIONS_TZ.md
```

Файл `56_...` менять только если это необходимо для исправления собственной
ошибки/неоднозначности документа; иначе не трогать.

Всегда игнорировать и не добавлять в index:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 2. Review findings, которые обязаны быть закрыты

### R1. Canon допускает runtime `KeyError`

Сейчас `TechniqueRule.validate_rule()` разрешает
`priority_by_horizon` быть строгим подмножеством `allowed_horizons`, но selector
выполняет прямой индекс:

```py
rule.priority_by_horizon[horizon]
```

Исполняемая негативная проверка показала, что canon без `fast` priority для
`transit_to_natal` успешно валидируется. Это нарушает fail-fast canon boundary:
ошибка конфигурации проходит startup и падает только при конкретных данных.

Исправить:

```text
set(priority_by_horizon) == set(allowed_horizons)
```

Порядок `allowed_horizons` должен быть canonical subsequence от
`long, medium, fast`, без перестановок и дубликатов. Все priority values finite
и в `0..1`.

Добавить negative tests как минимум для:

- missing allowed priority;
- extra non-allowed priority;
- reordered allowed horizons;
- duplicate allowed horizon;
- priority `<0`, `>1`, `nan`, `inf`.

### R2. Нормализованные canon values принимают значения больше 1

Review подтвердил, что startup принимает:

```text
timing.state_relevance.exact = 9.0
timing.completeness_with_exact = 2.0
min_pair_overlap.long_medium = 3.0
```

При этом downstream models и формулы трактуют эти поля как normalized
`0..1`. Получается либо поздний Pydantic failure, либо заведомо невозможный
selection вместо startup failure.

Обязательные unit-interval validators (`finite && 0 <= x <= 1`) для:

- всех `timing.state_relevance.*`;
- `timing.completeness_with_exact`;
- `timing.completeness_without_exact`;
- `timing.peaked_post_exact_fraction`;
- всех `min_candidate_impact.*`;
- всех `min_pair_overlap.*`;
- technique priorities.

Convex weight groups по-прежнему отдельно обязаны суммироваться к
`1.0 ± 1e-9`.

### R3. Selected anchor теряет данные, обязательные для B2B

Сейчас `SelectedHorizonAnchor` сохраняет только `timing_state` и `impact_score`.
Из результата исчезают:

- raw `active_from/exact_at/active_until`;
- precision/timezone/target clock;
- duration and relative position;
- exact timing completeness and warnings;
- normalized seven candidate features;
- target-family convergence count.

Это противоречит цели B2A: internal selection result должен быть достаточен для
B2B. B2B обязан построить реальные сроки, peak label, tone и grounded actions,
не повторяя timing classification и candidate math и не разыскивая выбранный
candidate по ID.

Исправить `SelectedHorizonAnchor`:

```py
class SelectedHorizonAnchor(...):
    horizon: TodayV2HorizonId
    activation_id: str
    technique: str
    technique_family: str
    polarity: ...
    target_type: ...
    target_key_normalized: str
    source_planet_normalized: str | None
    target_planet_normalized: str | None
    house_target_key: str | None
    timing: HorizonTimingAssessment
    technical_spheres: list[str]
    product_spheres: list[TodayV2ProductSphereKey]
    theme_keys: list[str]
    target_family_convergence_count: int
    feature_scores: HorizonCandidateFeatureScores
    impact_score: float
```

Не хранить параллельный самостоятельный `timing_state`: единственный источник
истины — `anchor.timing.timing_state`. `_to_anchor()` копирует exact selected
candidate data, не recompute.

Tests должны доказать для всех трёх anchors:

- timing object byte-identical соответствующему selected candidate assessment;
- raw timing сохранился;
- feature scores/convergence сохранились;
- human `evidence`, `debug`, имя/город/PII отсутствуют.

### R4. Internal strict schemas сейчас недостаточно strict

Выполнить validators, чтобы невозможное состояние нельзя было сконструировать
в обход service.

#### `HorizonTimingAssessment`

- `duration_seconds`/`duration_days`: либо оба `None`, либо оба finite и `>=0`;
- `eligible_horizons` и `preferred_horizons`: unique canonical subsequences в
  порядке `long, medium, fast`;
- preferred is subset of eligible;
- `is_anchor_eligible=True` требует:
  - `relative_position="inside"`;
  - non-empty eligible horizons;
  - precision `date|instant`;
  - `active_from` и `active_until`;
  - non-null timing state;
- `relative_position=before|after` всегда anchor-ineligible;
- warnings unique и typed.

#### `HorizonSphereMapping`

- lists unique;
- `linked_abs_amount` finite and `>=0`;
- `best_technical_rank` is `None` or `>=1`;
- empty technical mapping requires empty product/theme lists, zero amount and
  null rank;
- product spheres max 3, theme keys max 4 in v1 result.

#### `HorizonCandidate`

- `candidate.activation_id == candidate.timing.activation_id`;
- candidate horizon is in timing eligible horizons;
- timing is anchor eligible;
- all lists unique; product max 3, themes max 4;
- impact finite `0..1` and rounded to six decimals.

#### `SelectedHorizonAnchor`

- same timing identity/horizon eligibility invariants as candidate;
- lists unique/bounded;
- convergence count `>=1`;
- impact finite `0..1`, six decimals;
- feature scores normalized.

#### `SelectedHorizonTriple`

- exact item order `long, medium, fast`;
- three unique activation IDs and exact identity with ordered items;
- `pair_overlap_scores` has exactly:
  `long_medium`, `medium_fast`, `long_fast`;
- every pair/mean/impact/diversity/total score finite in `0..1`;
- serialized computed scores rounded to six decimals;
- unique family count equals actual item family count;
- shared theme/product lists unique and bounded;
- no empty/extra arbitrary pair keys.

#### `HorizonSelectionDiagnostics`

- both per-horizon dicts have exactly `long, medium, fast`;
- values non-negative;
- `input_count >= active_count >= classified_count`;
- post-bound count never exceeds pre-bound count or canon max;
- define `candidate_count` exactly as sum of pre-bound candidate counts;
- `combinations_evaluated <= 1728` for `horizon_selection.v1`;
- excluded reason keys typed, counts positive/non-negative consistently.

#### `HorizonSelectionResult`

- `warnings: list[HorizonTimingWarningCode]`, not `list[str]`;
- excluded-count keys use a Literal/typed alias, not arbitrary `str`;
- selected/null reason consistency remains enforced.

Validation errors must keep `hide_input_in_errors=True`; add a test with a
unique secret marker and prove it is absent from `str(ValidationError)`.

### R5. Preferred horizon semantics реализованы неверно

Observed case:

```text
technique=transit_to_natal
source=PLUTO
duration=180 days
eligible=[long, medium]
current preferred=[long, medium]
```

Canon technique preference is `medium`. Required algorithm:

1. Build all eligible horizons in canonical order.
2. If `rule.preferred_horizon` is eligible, return exactly that one preferred
   horizon.
3. Otherwise return eligible horizons whose duration falls in their preferred
   band, canonical order.
4. If none matched but eligible is non-empty, deterministic fallback to all
   eligible horizons in canonical order.

Tests:

- slow 180-day transit -> eligible long+medium, preferred medium only;
- firdar minor long duration -> preferred long only;
- firdar minor duration that cannot enter long but enters medium -> medium;
- arrays always canonical.

### R6. Broad `except Exception` скрывает programming errors

Failure policy B2A: ordinary malformed evidence/target clock becomes typed
fallback; invalid canon/programming invariant raises.

Исправить broad catches:

- `HorizonSelectionService.select()` target clock precheck catches only the
  documented parse/timezone exception classes;
- `HorizonTimingService.classify()` parse block catches only expected evidence
  parse/order/conversion exceptions (`ValueError`, `TypeError`, `OverflowError`
  where actually applicable), not arbitrary `Exception`.

Добавить monkeypatch test: unexpected `RuntimeError`/`AssertionError` from an
internal helper must propagate, а не превращаться в `invalid_timing` или
`invalid_target_clock`.

### R7. Sphere mapping должен fail fast на противоречивом scoring identity

`ScoringV2Result` содержит redundant identity:

```text
sphere_scores dict key
SphereScoreV2.key
SphereContribution.sphere
```

Текущая реализация суммирует по `contribution.sphere` и может silently assign
вклад не той сфере, если outer key и contribution disagree.

Required:

- outer `sphere_key` is authoritative for traversal/rank;
- assert/raise programming-invariant error if
  `SphereScoreV2.key != outer sphere_key`;
- for a matching activation contribution assert/raise if
  `SphereContribution.sphere != outer sphere_key`;
- linked amount and every final score used for ordering must be finite;
- no human evidence value in the exception.

Tests cover mismatched score key, mismatched contribution sphere, `nan/inf`
amount/final score, and normal ordering.

### R8. Pair overlap must be rounded before threshold comparison

TZ requires pair score to be summed, clamped and rounded to six decimals.
Current code compares an unrounded value to threshold and rounds only when
building the result.

Required:

```text
pair_overlap = round6(clamp(sum(weights), 0, 1))
threshold checks use that exact rounded value
stored pair score is the same exact value
mean is calculated from stored rounded pair scores
```

Add a boundary test using an explicit test canon/path or monkeypatch where the
seventh decimal changes the threshold outcome. Не менять production canon
weights ради теста.

### R9. Mandatory test matrix из TZ 56 фактически не закрыта

Существующие tests слишком агрегированы. Например test с названием
`unknown_technique_source_speed_low_impact_and_bounds_diagnostics` допускает
почти любой result reason и не доказывает отдельные exclusions; часть special
signals может быть отрезана input pre-bound.

Добавить изолированные assertions, не только broad combined scenarios.

#### Canon tests

- missing/malformed/extra/wrong version;
- every normalized unit interval boundary and NaN/inf;
- every convex sum;
- duration order;
- limit/combinations relation;
- missing/extra priority key;
- reordered/duplicate horizon arrays;
- unknown technique/horizon/speed group;
- duplicate transit speed group;
- overlapping/empty/non-canonical planet member handling;
- missing technical sphere;
- empty/duplicate/unknown product mapping and exact 12-key union;
- invalid/duplicate/empty theme mapping;
- target planet keys are normalized consistently with runtime lookup;
- default cache/clear and explicit-path behavior;
- core version map unchanged and separate horizon map exact;
- error privacy.

Canon extensibility rule: do not hardcode arbitrary Russian copy. It is allowed
to support future canonical planet/theme entries, but values used by runtime
must be normalized consistently and cannot silently become unreachable.

#### Timing tests

- date inclusive duration and leap day;
- instant offset equivalence;
- actual target timezone date/UTC boundary;
- HH:MM and HH:MM:SS;
- malformed date/time/timezone;
- all-null, each partial boundary variant, mixed, invalid, order,
  exact-outside;
- before/start/exact/end/after inclusivity;
- building/exact tolerance/peaked boundary/fading;
- period background/active and window without exact;
- overlapping duration bands and preferred semantics from R5;
- every transit speed eligibility path and unknown source speed;
- no server clock dependency;
- unexpected programming error propagates.

#### Sphere mapping tests

- only exact matching activation contributions;
- amount desc, final score desc, key lex independently;
- stable dedupe and truncation;
- all nine technical/all twelve product reachability;
- technical then target then source theme order;
- empty linkage;
- R7 invariant failures;
- serialization privacy.

#### Selection tests

- coherent triple beats individually stronger unrelated facts;
- each of five pair-overlap components isolated;
- pair overlap added once per category;
- rounded threshold boundary R8;
- family diversity affects tie/bonus but cannot bypass overlap threshold;
- low impact is actually excluded and counted;
- unknown technique actually excluded and counted;
- unknown source speed actually excluded and counted;
- `no_product_sphere` actually excluded and counted;
- inactive evidence ignored;
- exact `missing_long`, `missing_medium`, `missing_fast`,
  `no_coherent_triple`, `invalid_target_clock`;
- same activation cannot occupy two horizons in selected triple;
- item order and unique IDs;
- candidate and triple tie-breaks with equal scores;
- exact pre/post/candidate diagnostics;
- deterministic >256 truncation and exact survivors;
- combinations 0/expected/1728 boundary;
- repeated result JSON byte-identical;
- selected anchor carries timing/features from R3;
- no raw evidence/debug/PII;
- three goldens still select three different story themes.

Assertions вида `reason in {...}` не считаются proof для exact behavior, если
test заявляет конкретный invariant.

### R10. GRACE gate сейчас красный

Independent review command:

```bash
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_selection.py \
  apps/api/app/services/horizon_canon_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/horizon_sphere_mapping_service.py \
  apps/api/app/services/horizon_selection_service.py
```

Current result: **14 violations**, все missing function contracts в validators.

Все новые test code files также созданы без AI_HEADER/module contract/module map.
TZ 56 и repository AGENTS требуют GRACE для новых code files.

Required:

- все B2A app files проходят `scripts/grace_lint.py`;
- все пять новых B2A test files также проходят тот же lint;
- добавить paired function contracts к test functions и public shim methods,
  которые lint считает public;
- не подавлять/не изменять linter и не добавлять exclusions.

## 3. Canon normalization details

Чтобы runtime lookup и typed validation совпадали:

- planet speed member is non-empty and either stored in canonical normalized
  form or normalized once into the typed model; duplicate detection and runtime
  lookup use the same representation;
- `target_planet_themes` keys follow the same normalized representation;
- transit speed eligibility arrays non-empty and unique;
- every technical-to-product list non-empty and unique;
- every technical theme list non-empty and unique;
- every target planet theme list non-empty and unique;
- all exact current YAML values/order from TZ 56 stay unchanged.

Не вводить automatic fallback priority, generic product sphere или guessed
theme. Invalid canon fails startup.

## 4. Exact score and diagnostics semantics

Зафиксировать в code/tests:

```text
pre_bound_count[h]  = all valid above-threshold candidates for horizon h
post_bound_count[h] = first min(pre_bound_count[h], 12) after stable sort
candidate_count     = sum(pre_bound_count.values())
combinations        = post_long * post_medium * post_fast
```

`combinations_evaluated` counts cartesian tuples visited, including tuples later
rejected for duplicate activation ID or overlap. It never exceeds 1728.

`excluded_counts_by_reason` counts candidate/evidence rejection at the stage
where it occurs. Не добавлять one warning per eligible horizon unless that is
the real rejected unit; document/test the chosen unit. Repeated public result
serialization must remain deterministic, including warning/reason order.

## 5. Mandatory gates after corrections

Run from repository root unless command says otherwise.

### 5.1 Diff and GRACE

```bash
git diff --check

python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_selection.py \
  apps/api/app/services/horizon_canon_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/horizon_sphere_mapping_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_benchmark.py
```

Expected: zero violations.

### 5.2 Focused backend

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_benchmark.py -q
```

Expected: all pass.

### 5.3 Benchmark evidence

```bash
cd apps/api
.venv/bin/python -m pytest tests/test_horizon_selection_benchmark.py -q -s
```

Expected: p95 `<100 ms`, 20 measured runs, combinations `<=1728`.

### 5.4 Contract safety

```bash
pnpm contracts:check
git diff --exit-code -- packages/contracts/src/generated apps/api/openapi.json
```

Expected: PASS and zero generated/public diff.

### 5.5 Full API regression

```bash
cd apps/api
.venv/bin/python -m pytest tests -q
```

Expected exact baseline class: only the same six pre-existing failures:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

No new failure. Pass count may increase because tests are added.

### 5.6 Scope/index

```bash
git diff --cached --name-only
git status --short
git diff --name-only
git ls-files --others --exclude-standard
```

Expected:

- index empty;
- only exact B2A allowlist plus known unrelated untracked paths;
- no frontend/public contracts/OpenAPI/sidecar/Today integration changes;
- no commit/push.

## 6. Required callback and stop point

После всех corrections/gates вернуть exact evidence block и остановиться:

```text
READY_STAGE_B2A_REVIEW_R1
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
canon_fail_closed: PASS <negative cases count>
priority_coverage: PASS
normalized_ranges: PASS
timing_preference: PASS
programming_errors_propagate: PASS
sphere_identity_invariants: PASS
selected_anchor_b2b_complete: PASS
typed_internal_contracts: PASS
pair_rounding_boundary: PASS
selection_goldens: PASS stories=3
selection_matrix: PASS <cases count>
determinism: BYTE_IDENTICAL
diagnostics: PASS pre/post/counts/combinations
privacy: PASS
grace_lint: PASS app=<files> tests=<files>
benchmark: p95=<ms> runs=20 combinations=<n>
focused: <passed>
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
diff_paths: <exact paths>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

Не начинать B2B и не делать commit/push до нового architect acceptance.
