# Stage B2A — typed horizon canon, timing and coherent selection

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Parent scope: `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`, B2
Wave plan: `51_STAGE_B_AND_MAIN_RELEASE_WAVE_PLAN.md`

## 0. Роль этой подволны

B2 делится на две внутренние принимаемые подволны:

```text
B2A: typed selection canon + timing + product-sphere mapping + coherent triple
B2B: personal fact pack + tone + deterministic guidance + claim validator + coverage
```

B2A не строит публичный `TodayV2HorizonsBlock` и не подключается к
`TodayService`/`SemanticV2Service`. Её результат — чистый внутренний selection
result, достаточный для B2B.

Кодер выполняет реализацию. Архитектор проводит ревью. Не запускать субагентов.
До отдельной architect acceptance запрещены `git add`, commit и push.

## 1. Preflight

До изменений выполнить:

```bash
git status --short --branch
git diff --cached --name-only
git log -1 --format='%H %s'
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
pnpm contracts:check
```

Ожидание:

```text
branch: preview/solarsage-v2-human-first-navigator-ux
HEAD: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin feature: same SHA
index: empty
contracts:check: PASS
```

Допустимые unrelated untracked paths, которые нельзя трогать:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 2. Жёсткие границы B2A

### Входит

- один versioned selection canon;
- typed strict schema/loader для него;
- strict startup validation через существующий canon path;
- отдельная horizon-canon version identity без изменения текущего cache hash;
- pure timing classification из `ActivationEvidence` и request target clock;
- deterministic mapping scoring spheres -> 12 product spheres + theme keys;
- bounded deterministic candidate ranking;
- coherent long/medium/fast triple selection;
- typed honesty fallback/reasons;
- focused tests, full API regression и micro-benchmark.

### Не входит

- `TodayService`, `SemanticV2Service`, `CalendarService` integration;
- заполнение `TodayV2Block.horizons`;
- cache identity/hash/version bump;
- language/action/personal-pattern canons — это B2B;
- natal/profile fact extraction;
- tone aggregation;
- public guidance copy/actions/manifestations;
- claim validator;
- LLM;
- frontend/contracts/OpenAPI changes;
- sidecar changes;
- logging events/config/env/systemd/nginx/ports.

Production behavior после B2A должен остаться прежним: публичные horizons всё
ещё `None/absent`, frontend работает через B1 consumer/legacy fallback.

## 3. Exact allowlist

Разрешены только:

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
```

Не менять `apps/api/app/schemas/__init__.py`: B2A schemas internal, не public API
barrel. Не менять existing canon YAML. Не менять package/lock files.

## 4. GRACE и privacy

Все новые code files получают полный:

```text
AI_HEADER
START_MODULE_CONTRACT / END_MODULE_CONTRACT
START_MODULE_MAP / END_MODULE_MAP
START_BLOCK / END_BLOCK
START_FUNCTION_CONTRACT / END_FUNCTION_CONTRACT
```

для public/non-trivial functions и methods.

Selection/timing models и errors не должны содержать:

- `ActivationEvidence.evidence` human string;
- raw `debug` object;
- имя, город, координаты, gender, user ID;
- profile/natal data;
- LLM text.

Допустимы только stable activation IDs, technique/family, target/source keys,
machine timing, numeric scores, technical/product sphere keys и theme keys.

Новые модули pure: no DB, HTTP, subprocess, environment, server clock, random,
logging side effects.

## 5. Typed selection canon

Создать `grace/canon/horizon_selection.v1.yml`.

### 5.1 Обязательная структура и значения

```yaml
schema_version: horizon_selection.v1
version: v1

limits:
  max_input_activations: 256
  max_candidates_per_horizon: 12
  max_product_spheres_per_candidate: 3
  max_theme_keys_per_candidate: 4
  max_anchor_combinations: 1728

duration_bands:
  long:
    eligible_min_days: 120
    eligible_max_days: null
    preferred_min_days: 180
    preferred_max_days: null
  medium:
    eligible_min_days: 14
    eligible_max_days: 240
    preferred_min_days: 45
    preferred_max_days: 210
  fast:
    eligible_min_days: 0
    eligible_max_days: 21
    preferred_min_days: 0
    preferred_max_days: 21

timing:
  instant_exact_tolerance_seconds: 3600
  peaked_min_seconds: 43200
  peaked_post_exact_fraction: 0.25
  date_exact_tolerance_days: 0
  completeness_with_exact: 1.0
  completeness_without_exact: 0.8
  state_relevance:
    upcoming: 0.0
    building: 0.95
    active: 0.80
    exact: 1.0
    peaked: 0.90
    fading: 0.65
    background: 0.75

impact_weights:
  strength: 0.28
  sphere_rank: 0.18
  contribution: 0.14
  convergence: 0.12
  timing_relevance: 0.12
  timing_completeness: 0.08
  technique_priority: 0.08

min_candidate_impact:
  long: 0.44
  medium: 0.46
  fast: 0.42

story_overlap_weights:
  same_target: 0.35
  shared_theme: 0.25
  shared_product_sphere: 0.20
  same_planet_or_house: 0.10
  shared_technical_sphere: 0.10

min_pair_overlap:
  long_medium: 0.20
  medium_fast: 0.18
  long_fast: 0.10
  triple_mean: 0.18

triple_score_weights:
  mean_impact: 0.65
  mean_overlap: 0.30
  family_diversity: 0.05
```

Все weight groups, которые логически являются convex combination, должны
суммироваться к `1.0 ± 1e-9`. Negative/NaN/inf запрещены.

### 5.2 Planet speed groups

```yaml
planet_speed_groups:
  fast: [SUN, MOON, MERCURY, VENUS, MARS]
  medium: [JUPITER, SATURN]
  slow: [URANUS, NEPTUNE, PLUTO, CHIRON, NORTH_NODE, SOUTH_NODE]

transit_speed_eligibility:
  long: [slow]
  medium: [medium, slow]
  fast: [fast]
```

Normalize input planet names only for comparison: strip known `Transit_`/
`Natal_` prefixes, uppercase, preserve wire value elsewhere.

### 5.3 Technique rules

Every rule has:

```text
allowed_horizons
preferred_horizon
timing_mode: peak|period|window
priority_by_horizon
```

Exact initial intent:

```yaml
technique_rules:
  annual_profection:
    allowed_horizons: [long]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 1.00}
  monthly_profection:
    allowed_horizons: [medium]
    preferred_horizon: medium
    timing_mode: period
    priority_by_horizon: {medium: 0.86}
  firdar_major:
    allowed_horizons: [long]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 0.96}
  firdar_minor:
    allowed_horizons: [long, medium]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 0.82, medium: 0.74}
  solar_return:
    allowed_horizons: [long]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 0.92}
  lunar_return:
    allowed_horizons: [medium]
    preferred_horizon: medium
    timing_mode: period
    priority_by_horizon: {medium: 0.84}
  solar_arc:
    allowed_horizons: [long, medium]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 0.82, medium: 0.76}
  secondary_progression:
    allowed_horizons: [long, medium]
    preferred_horizon: long
    timing_mode: period
    priority_by_horizon: {long: 0.80, medium: 0.76}
  eclipse_window:
    allowed_horizons: [medium]
    preferred_horizon: medium
    timing_mode: window
    priority_by_horizon: {medium: 0.88}
  transit_to_natal:
    allowed_horizons: [long, medium, fast]
    preferred_horizon: medium
    timing_mode: peak
    priority_by_horizon: {long: 0.85, medium: 0.95, fast: 0.90}
  transit_to_angle:
    allowed_horizons: [long, medium, fast]
    preferred_horizon: medium
    timing_mode: peak
    priority_by_horizon: {long: 0.90, medium: 0.98, fast: 0.95}
  transit_to_lot:
    allowed_horizons: [long, medium, fast]
    preferred_horizon: medium
    timing_mode: peak
    priority_by_horizon: {long: 0.75, medium: 0.82, fast: 0.80}
  transit_planet_in_house:
    allowed_horizons: [long, medium, fast]
    preferred_horizon: medium
    timing_mode: window
    priority_by_horizon: {long: 0.60, medium: 0.68, fast: 0.62}
```

Unknown technique is not guessed: anchor candidate is ineligible with typed
reason. Do not silently fall back to generic priority.

For `transit_*`, duration band and `transit_speed_eligibility` must both pass.
For non-transit technique only duration band + allowed horizon apply. Period
technique is not allowed to bypass malformed/missing timing.

### 5.4 Technical -> product sphere mapping

Canon owns exact ordered mapping:

```yaml
technical_to_product_spheres:
  thinking_speech_learning: [communication, study, documents]
  work_status_achievement: [work, decisions]
  relationships_partnership: [relationships]
  money_security_resources: [money, shopping, documents]
  body_energy_health: [health, sport]
  home_family_roots: [relationships]
  inner_background_unconscious: [health, creativity]
  crisis_transformation_control: [decisions, money]
  meaning_expansion_vector: [travel, study, decisions]
```

Union must cover all 12 public product keys exactly from B1; unknown product key
fails canon validation.

### 5.5 Theme mapping

Theme keys are internal stable IDs, not Russian text:

```yaml
technical_sphere_themes:
  thinking_speech_learning: [communication_learning_documents]
  work_status_achievement: [structure_boundaries_control]
  relationships_partnership: [relationships_values_closeness]
  money_security_resources: [resources_security]
  body_energy_health: [energy_body_pacing]
  home_family_roots: [home_belonging]
  inner_background_unconscious: [inner_clarity_recovery]
  crisis_transformation_control: [structure_boundaries_control]
  meaning_expansion_vector: [direction_growth_meaning]

target_planet_themes:
  SATURN: [structure_boundaries_control]
  PLUTO: [structure_boundaries_control]
  MERCURY: [communication_learning_documents]
  VENUS: [relationships_values_closeness, resources_security]
  MOON: [relationships_values_closeness, energy_body_pacing]
  MARS: [energy_body_pacing, structure_boundaries_control]
  SUN: [creativity_visibility]
  JUPITER: [direction_growth_meaning, resources_security]
  URANUS: [change_innovation]
  NEPTUNE: [inner_clarity_recovery, creativity_visibility]
  CHIRON: [inner_clarity_recovery]
  NORTH_NODE: [direction_growth_meaning]
  SOUTH_NODE: [inner_clarity_recovery]
```

Candidate theme order:

1. themes from ranked technical spheres;
2. target planet theme;
3. source planet theme;
4. stable dedupe preserving order;
5. truncate to canon max.

### 5.6 Typed canon validation

Create strict frozen Pydantic models in
`apps/api/app/schemas/horizon_canon.py` with `extra="forbid"`.

Validate at minimum:

- exact schema/version;
- positive limits;
- `max_candidates_per_horizon ** 3 <= max_anchor_combinations`;
- duration bounds ordered/non-negative;
- all weights finite/non-negative and sums correct;
- all public horizon IDs exact;
- every technique rule uses known activation technique;
- priority keys subset/equal allowed horizons and values `0..1`;
- all three planet groups disjoint;
- transit speed eligibility contains known groups;
- exactly nine technical scoring keys are mapped;
- union of product mapping covers all 12 B1 product keys;
- theme IDs match opaque lower snake-case ID pattern;
- no duplicate members after normalization.

## 6. Canon loader/startup integration

Create `apps/api/app/services/horizon_canon_service.py`:

```py
load_horizon_selection_canon(path: Path | None = None) -> HorizonSelectionCanon
get_horizon_canon_versions() -> dict[str, str]
clear_horizon_canon_cache_for_tests() -> None
```

Rules:

- repo path resolved from module location, never cwd;
- `@lru_cache(maxsize=1)` only for default repo file;
- explicit test path is validated every call or cached by exact resolved path;
- missing/malformed/invalid canon raises `CanonValidationError`;
- no silent/default fallback;
- error contains path + structural field, not YAML body.

Extend existing `canon_service.py` so `validate_canon_bundle()` at application
startup also requires and typed-validates `horizon_selection.v1.yml`.

Important cache boundary:

- existing `CANON_VERSIONS` and `get_canon_versions()` remain byte-for-byte
  semantically unchanged in B2A;
- add/use separate `get_horizon_canon_versions()`;
- current Today cache identity/hash must not change until B3;
- `load_canon_bundle()` may expose the additional raw filename, but existing
  callers and keys remain valid.

Update temp-dir canon tests to include a valid horizon selection file when the
test intends to reach another validation branch.

## 7. Internal selection schemas

Create `apps/api/app/schemas/horizon_selection.py` using strict frozen internal
models (`extra="forbid"`). Do not export through public schema barrel/OpenAPI.

### 7.1 Literals

Reuse public B1 aliases for horizon/timing/polarity where applicable. Add:

```text
HorizonTimingWarningCode:
  missing_timing
  partial_timing
  mixed_precision
  invalid_timing
  invalid_target_clock
  target_before_window
  target_after_window
  unknown_technique
  unknown_source_speed
  no_product_sphere
  below_impact_threshold

HorizonSelectionReason:
  selected
  invalid_target_clock
  missing_long
  missing_medium
  missing_fast
  no_coherent_triple

RelativeTargetPosition: before|inside|after
```

### 7.2 Required models

Names may be exactly:

```text
HorizonTimingAssessment
HorizonCandidateFeatureScores
HorizonCandidate
SelectedHorizonAnchor
SelectedHorizonTriple
HorizonSelectionDiagnostics
HorizonSelectionResult
```

Required information:

`HorizonTimingAssessment`:

- activation_id;
- precision nullable for rejected evidence;
- raw active_from/exact_at/active_until preserved;
- timezone;
- target_local and target_utc machine strings;
- duration_seconds and duration_days;
- relative position;
- public-compatible timing state nullable;
- timing completeness `0..1`;
- eligible/preferred horizons in canonical long/medium/fast order;
- typed warning codes;
- `is_anchor_eligible`.

`HorizonCandidateFeatureScores`:

- all seven normalized features `0..1`;
- impact score is stored on candidate, not recomputed in consumers.

`HorizonCandidate`:

- activation_id;
- candidate horizon;
- technique/family/polarity;
- normalized source/target identity fields;
- timing assessment;
- technical spheres ordered;
- product spheres ordered max 3;
- theme keys ordered max 4;
- target family convergence count;
- feature scores;
- impact score rounded to 6 decimals;
- deterministic tie-break tuple exposed as fields or pure method.

No human evidence/debug field.

`SelectedHorizonAnchor`:

- horizon;
- anchor activation ID;
- exact selected candidate facts needed by B2B;
- no additional invented support IDs in B2A.

`SelectedHorizonTriple`:

- items exactly three and exact order long/medium/fast;
- pair overlap scores;
- mean overlap;
- mean impact;
- family diversity score/count;
- total score;
- stable shared theme/product-sphere intersection/union fields;
- unique anchor activation IDs.

`HorizonSelectionDiagnostics`:

- input/active/classified/candidate counts;
- per-horizon pre-bound/post-bound counts;
- excluded counts by typed reason;
- combinations evaluated, never above canon limit;
- input_truncated bool.

`HorizonSelectionResult`:

- `selection: SelectedHorizonTriple | None`;
- exact reason;
- diagnostics;
- warnings as typed machine strings only.

Validators enforce ranges/order/uniqueness and must hide raw input values in
`str(ValidationError)`.

## 8. HorizonTimingService

Create `apps/api/app/services/horizon_timing_service.py`.

Public pure API:

```py
class HorizonTimingService:
    def classify(
        self,
        evidence: ActivationEvidence,
        *,
        target_date: str,
        target_time: str,
        target_tz: str,
    ) -> HorizonTimingAssessment: ...
```

The selection service passes identity from `ActivationLayer`; never
`datetime.now()`, `date.today()` or server timezone.

### 8.1 Parsing

- Target timezone through `zoneinfo.ZoneInfo`.
- Accept target time exact `HH:MM` or `HH:MM:SS`; reject otherwise.
- Date-only evidence: all non-null timing values exact `YYYY-MM-DD`.
- Instant evidence: all non-null values RFC3339 with explicit `Z`/offset.
- `active_from` and `active_until` are both mandatory for anchor eligibility.
- All three null -> `missing_timing`.
- One boundary missing -> `partial_timing`.
- Mixed date/instant -> `mixed_precision`.
- Parse/order/exact-outside error -> `invalid_timing`.
- Preserve wire strings; normalize only comparison values.

No exception for evidence data problems: return ineligible assessment. Invalid
canon is an exception; invalid target clock yields typed ineligible assessment
and selection fallback.

### 8.2 Duration/containment

- Date precision duration days inclusive: `(until - from).days + 1`.
- Instant duration seconds exact UTC delta; duration days seconds/86400.
- Date target containment inclusive by target local date.
- Instant containment inclusive by target datetime converted to UTC.
- Before range: state `upcoming`, relative `before`, ineligible warning.
- After range: state `fading`, relative `after`, ineligible warning.
- Only relative `inside` can be anchor eligible.

### 8.3 State

Read technique `timing_mode` from typed canon:

- `period`: ignore exact for state; long preferred -> `background`, otherwise
  `active`;
- `window` without exact -> `active` (long may be `background`);
- `peak`:
  - target before exact -> `building`;
  - within exact tolerance -> `exact`;
  - after exact and elapsed <= max(`peaked_min_seconds`, post-window *
    `peaked_post_exact_fraction`) -> `peaked`;
  - later but still inside -> `fading`;
  - missing exact -> `active`.

Date exact uses exact calendar-day equality with canon tolerance.

### 8.4 Horizon eligibility

- Must be active, timing-valid and target-contained.
- Technique allowed horizons intersect duration eligible bands.
- For transit techniques, source speed group must be allowed for horizon.
- Unknown transit source speed -> no transit anchor eligibility and warning.
- Preferred horizon is technique preference if eligible and duration is at
  least eligible; otherwise preferred band matches.
- Result horizon arrays always canonical `long, medium, fast` order.

## 9. HorizonSphereMappingService

Create `apps/api/app/services/horizon_sphere_mapping_service.py`.

Pure API concept:

```py
map_activation(
    activation_id: str,
    scoring_result: ScoringV2Result,
    *,
    source_planet: str | None,
    target_planet_or_key: str | None,
) -> HorizonSphereMapping
```

The helper model may live internal in `horizon_selection.py`.

Algorithm:

1. Inspect only `SphereContribution` where
   `source == "activation" && source_id == activation_id`.
2. Technical sphere relevance order:
   - sum absolute contribution amount desc;
   - sphere final_score desc;
   - technical key lexicographic.
3. Convert through canon ordered technical->product mapping.
4. Stable dedupe and truncate product spheres to 3.
5. Resolve theme keys using section 5.5 and truncate to 4.
6. No linked contribution -> empty mapping; candidate later excluded with
   `no_product_sphere`. Do not guess from evidence prose/debug.

Tests prove all nine technical keys and all twelve product keys are reachable.

## 10. Candidate feature calculation

Create in `HorizonSelectionService`, using only canon-driven weights.

For all active evidence, precompute:

- target family count: unique `technique_family` for exact normalized
  `(target_type, target_key)`;
- global maximum absolute linked activation contribution;
- technical sphere rank by `final_score desc, key lex`;
- known technique priority and timing assessment.

Normalized features:

```text
strength:
  clamp evidence.strength to 0..1

sphere_rank:
  one sphere -> 1
  otherwise 1 - (best_linked_rank - 1) / (sphere_count - 1)

contribution:
  linked_abs_amount / global_max_linked_abs_amount; 0 if denominator 0

convergence:
  clamp((family_count - 1) / 2, 0, 1)

timing_relevance:
  canon state_relevance[state]

timing_completeness:
  canon exact/no-exact value

technique_priority:
  exact rule value for candidate horizon
```

Impact = weighted sum, round to 6 decimals after the full sum. Do not round
intermediate comparison values except serialized model fields.

Candidate below its horizon threshold is excluded. Stable candidate sort:

```text
impact desc
timing_completeness desc
strength desc
technique_priority desc
activation_id lexicographic
```

## 11. Coherent triple selection

Create `apps/api/app/services/horizon_selection_service.py`.

Public API:

```py
class HorizonSelectionService:
    def select(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
    ) -> HorizonSelectionResult: ...
```

### 11.1 Input bounding

- Ignore `active is False`.
- If active input count > 256, pre-bound deterministically by:
  `strength desc`, technique priority maximum desc, activation ID lex;
  set `input_truncated=true`.
- Build candidates for every eligible horizon.
- Sort and truncate each horizon list to 12 before triple enumeration.
- Never evaluate over 1728 combinations; assert diagnostics.

### 11.2 Pair overlap

Each boolean/category contribution uses canon weight once:

- exact normalized target type+key match;
- at least one shared theme;
- at least one shared product sphere;
- source/target planet intersection or same house target;
- at least one shared technical sphere.

Score is sum of applicable weights, clamped/rounded to 6 decimals.

### 11.3 Triple rules

- anchors have unique activation IDs;
- each pair meets its exact min overlap;
- mean of three pair overlaps meets triple min;
- all three timing assessments anchor-eligible;
- exact horizon order long/medium/fast.

Triple score:

```text
0.65 * mean anchor impact
+ 0.30 * mean pair overlap
+ 0.05 * family diversity score
```

Family diversity score:

```text
clamp((unique_family_count - 1) / 2, 0, 1)
```

Stable triple tie-break:

```text
total score desc
mean overlap desc
mean impact desc
unique family count desc
(long_id, medium_id, fast_id) lexicographic
```

### 11.4 Story summary fields

Selected triple stores, deterministically:

- shared theme intersection in first-anchor order;
- if intersection empty, top union ordered by frequency desc then first
  occurrence then key;
- same for product spheres;
- no Russian copy.

### 11.5 Honesty fallback

Never force weak/unrelated triple.

Return `selection=None` with exact first applicable reason:

1. invalid_target_clock;
2. missing_long;
3. missing_medium;
4. missing_fast;
5. no_coherent_triple.

No exception for ordinary lack of evidence. Invalid canon/programming invariant
raises and fails tests.

## 12. Golden selection corpus for B2A

`test_horizon_selection_service.py` must define synthetic typed evidence/scoring
builders, no production fixture import and no real user data.

Mandatory control story:

```text
long coherent: annual/profection -> SATURN or work/structure
medium coherent: slow transit PLUTO -> natal SATURN
fast coherent: MOON -> natal PLUTO
```

Also add individually stronger but unrelated Venus/Jupiter alternatives. The
coherent control/responsibility triple must win because documented overlap,
not hardcoded IDs.

At least three goldens:

1. `structure_boundaries_control` coherent triple;
2. `communication_learning_documents` coherent triple;
3. `relationships_values_closeness` coherent triple.

Repeated selection and JSON dump must be byte-identical.

## 13. Tests

### 13.1 Canon

- real canon validates;
- missing file;
- malformed YAML;
- extra key;
- wrong version;
- non-finite/negative weights;
- weight sums;
- invalid duration order;
- invalid limit/combinations relation;
- unknown technique/horizon/speed group;
- overlapping planet groups;
- missing technical sphere;
- invalid/duplicate product sphere;
- product union not all 12;
- invalid theme ID;
- default cache returns same object; cache clear works;
- existing `get_canon_versions()` unchanged;
- separate horizon version map exact.

### 13.2 Timing

- date inclusive duration;
- leap day;
- instant offset equivalence;
- target timezone boundary;
- HH:MM and HH:MM:SS;
- malformed target clock;
- all-null/partial/mixed/invalid/order/exact-outside;
- before/inside/after containment;
- building/exact/peaked/fading boundaries;
- period background/active;
- duration overlaps;
- transit planet speed eligibility;
- no server clock dependency (patching `datetime.now` must be irrelevant).

### 13.3 Sphere mapping

- only matching activation contributions;
- amount/rank/key ordering;
- stable dedupe/truncation;
- all 9 technical keys;
- all 12 product keys;
- themes technical then target then source;
- no contribution -> empty;
- serialization has no evidence/debug/raw text.

### 13.4 Selection

- coherent triple beats stronger unrelated facts;
- every overlap component isolated;
- family diversity only tie/bonus, not threshold bypass;
- low impact excluded;
- unknown technique/source speed excluded;
- each missing horizon reason;
- no coherent triple reason;
- exact order and unique IDs;
- stable candidate/triple tie-break;
- bounds/diagnostics exact;
- input >256 deterministic truncation;
- repeated result byte-identical;
- no raw evidence/debug/PII in model dump;
- three different goldens select different story keys.

### 13.5 Benchmark

`test_horizon_selection_benchmark.py`:

- deterministic synthetic 120-activation input;
- 3 warmups + 20 measured runs;
- use `time.perf_counter_ns`;
- p95 calculation is sorted sample index `ceil(0.95*n)-1`;
- assert p95 < 100 ms on this service alone;
- assert combinations <=1728;
- print one concise benchmark line for callback evidence;
- no test output file and no network/DB.

## 14. Baseline safety

Current known API baseline after B1:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

B2A must not change/fix those incidentally. Full API may be red only on the same
six; all new B2A tests green.

No public contract change expected:

```bash
pnpm contracts:check
git diff --name-only -- packages/contracts
```

Generated contract diff must be empty.

## 15. Mandatory gates

### Focused

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_benchmark.py \
  -q
```

### API full

```bash
cd apps/api
.venv/bin/python -m pytest tests -q
```

Expected: same exact six baseline failures only; pass count increases.

### Existing critical regression

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_semantic_v2_service.py \
  -q
```

Semantic V2 subset may contain the same known baseline failures; scoring tests
must remain green.

### Contracts/static/scope

```bash
cd ../..
pnpm contracts:check

apps/api/.venv/bin/python -m compileall -q \
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

git diff --check
git diff --cached --name-only
git diff --name-only
git status --short --branch
```

Index empty. Diff only exact allowlist. No public generated files.

## 16. Architect review checklist

Coder не отмечает это сам как acceptance. Архитектор отдельно проверит:

- typed canon fails closed;
- core cache identity untouched;
- no server clock/random/LLM/DB/network;
- timezones and inclusive boundaries;
- period vs peak state semantics;
- candidate math matches canon exactly;
- coherent triple not merely strongest three;
- no unbounded cubic work;
- honest null reasons;
- byte determinism;
- selection dump contains no human evidence/debug/PII;
- production Today population remains absent.

## 17. Callback

После всех gates вернуть exact block и остановиться без commit/push/B2B:

```text
READY_STAGE_B2A_CANON_TIMING_SELECTION
branch: preview/solarsage-v2-human-first-navigator-ux
head: 3a58c581bbe010e98e78b2295a135f138d32bd88
origin_feature: 3a58c581bbe010e98e78b2295a135f138d32bd88
horizon_canon: PASS version=v1
core_canon_versions_unchanged: PASS
timing_matrix: PASS <count>
sphere_mapping: PASS technical=9 product=12
selection_goldens: PASS stories=3
coherence_over_raw_strength: PASS
honesty_fallback: PASS
determinism: BYTE_IDENTICAL
bounds: input=256 candidates_per_horizon=12 combinations<=1728
privacy: PASS
benchmark: p95=<ms> runs=20
focused: <counts>
contracts_check: PASS generated_diff=ZERO
api_full: BASELINE_RED_IDENTICAL <counts>
diff_paths: ...
index: EMPTY
commit: NOT_YET
push: NOT_YET
```
