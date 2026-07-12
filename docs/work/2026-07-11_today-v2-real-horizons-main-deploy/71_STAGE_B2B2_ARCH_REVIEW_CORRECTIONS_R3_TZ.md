# Stage B2B2 — architect review corrections R3

Дата: 2026-07-12  
Ветка: preview/solarsage-v2-human-first-navigator-ux  
Accepted HEAD/origin: c47863a0c4b2be2242c276bb610a262b4b91a737  
Parent documents: 68, 69, 70  
Статус: **NOT ACCEPTED — CORRECT R3, NO COMMIT/PUSH**

## 0. Режим

Продолжить текущий untracked B2B2 diff. Ничего не откатывать. Не начинать B3.

Сначала полностью перечитать документы 68, 69, 70 и затем этот документ 71.
Документы 68–70 остаются нормативными. R3 перечисляет остаточные дефекты,
независимо воспроизведённые после отчёта исполнителя.

Запрещено:

- субагенты;
- git add, commit, push;
- reset/clean/stash/checkout текущих B2B2 files;
- public/generated contract changes;
- accepted B1/B2A/B2B1 changes;
- Today/Semantic/Calendar/frontend/sidecar integration;
- threshold/scoring/canon/auth/runtime fixture changes;
- работа вне exact allowlist из section 2;
- исправление шести известных full-API baseline failures.

После всех gates вернуть callback section 12 и остановиться.

## 1. Что уже независимо подтверждено и должно сохраниться

Architect gates после R2:

~~~text
GRACE:             PASS 12/12
focused:           102 passed
upstream:          82 passed
contracts:         PASS, 110 focused contract tests
full API:          1144 passed, 4 skipped, exact 6 baseline failures
git diff --check:  PASS
index:             EMPTY
commit/push:       NOT CREATED
~~~

Current line counts:

~~~text
schema                         214
formatter                      553
builders                       481
guidance service               337
claim policy                   542
claim validator                392
testkit                        542
formatter tests                469
guidance tests                 635
claim validator tests          668
coverage tests                 260
benchmark tests                150
~~~

Все лимиты пока проходят, но validator/test file близки к максимуму. Новые
проверки добавлять через рефакторинг/shared helpers/параметризацию, не превышая:

~~~text
validator <=400
guidance service <=350
production file <=650
test file <=700
production line <=140 chars
~~~

Direct shifted selection теперь работает на трёх ранее падавших случаях:

~~~text
2028-02-29 America/New_York structure_boundaries_control
2026-03-29 Europe/Berlin communication_learning_documents
2026-07-08 Europe/Moscow relationships_values_closeness
~~~

Сохранить этот прогресс.

## 2. Exact allowlist

Можно менять только:

~~~text
apps/api/app/schemas/horizon_guidance.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/fixtures/horizon_guidance_coverage.v1.yml
apps/api/tests/test_horizon_guidance_formatter.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_pipeline_benchmark.py
~~~

Не создавать новые files.

Unrelated paths остаются untouched:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 3. Blocker R3-F1 — benchmark всё ещё false proof

Текущий benchmark печатает:

~~~text
horizon_pipeline_benchmark: p95=26.86ms runs=20 combinations=1728
~~~

Но source всё ещё:

- не asserts len(layer.activations) == 120;
- не asserts input groups 40/40/40;
- не asserts bounded candidates 12/12/12;
- не asserts combinations_evaluated == 1728 в каждом warmup;
- не asserts combinations_evaluated == 1728 в каждом measured run;
- проверяет только последний block и печатает diagnostics последнего run.

Совпадение последнего значения с 1728 не является regression gate.

### Required correction

До warmup проверить exact fixture shape:

~~~text
total activations = 120
long-capable      = 40
medium-capable    = 40
fast-capable      = 40
~~~

После каждого из 3 warmups и каждого из 20 measured runs:

~~~text
selection is not None
bounded candidates are exact 12/12/12
combinations_evaluated == 1728
validated block schema_version == today-horizons.v1
validated block guidance_mode == deterministic
~~~

Собрать counter runs_with_1728 и assert exact 23.

Не переносить fixture/service construction внутрь timed body. Full six-stage
pipeline оставить внутри каждого run.

Final print exact:

~~~text
horizon_pipeline_benchmark: p95=<ms> runs=20 combinations=1728 all_runs=23/23
~~~

## 4. Blocker R3-F2 — YAML loader не strict по требуемому contract

Текущие _CoverageProfile / _CoverageData проверяют только:

- extra=forbid;
- regex schema version;
- field presence/types.

Architect direct probes accepted invalid data:

~~~text
1 profile + 1 invalid date + invalid timezone + unknown story/natal -> ACCEPT_INVALID
5 duplicate profile IDs + 12 duplicate dates                     -> ACCEPT_INVALID
~~~

### Required strict validation

Fixture loader должен reject exact typed errors for:

- schema version not exact;
- profiles count not exact 5;
- target_dates count not exact 12;
- duplicate profile ID;
- duplicate target date;
- missing any accepted profile ID;
- extra/unexpected profile ID;
- invalid IANA timezone via ZoneInfo;
- unknown story;
- unknown natal case;
- invalid ISO calendar date;
- missing/extra date against accepted exact corpus;
- any extra field at top/profile level.

Accepted profile IDs:

~~~text
synthetic-structure-moscow
synthetic-communication-utc
synthetic-relationships-berlin
synthetic-empty-new-york
synthetic-mixed-tbilisi
~~~

Accepted date corpus is the exact 12 values currently listed in the YAML.
Python may hold invariant constants only for validation; all generated cases
must still come solely from parsed YAML. Do not duplicate the case loop as
hardcoded Python records.

Add explicit mutation tests of the strict loader. A build_coverage_cases()
happy-path test alone is insufficient.

## 5. Blocker R3-F3 — shifted timing не соответствует exact R1 contract

Current shifted_story_for preserves arbitrary offsets/durations from fixed
reference epoch. It now selects, but medium windows are not required ±90 days
around local noon.

Architect samples:

~~~text
New York medium:
2027-10-19T05:00:00Z -> exact 2028-02-29T17:00:00Z
                     -> 2028-05-19T05:00:00Z

Berlin medium:
2025-11-15T22:00:00Z -> exact 2026-03-29T10:00:00Z
                     -> 2026-06-16T22:00:00Z
~~~

Это не exact local-noon ±90 local calendar days.

### Required correction

For each supplied target date/timezone:

~~~text
target_local = aware local datetime at 12:00
target_utc   = exact UTC conversion
~~~

Build selected story timing by role, not by arbitrary old offset:

~~~text
long:
  active_from  = local calendar year YYYY-01-01, date precision
  exact_at     = null
  active_until = local calendar year YYYY-12-31, date precision

medium:
  active_from  = target local noon - 90 local calendar days
  exact_at     = target local noon
  active_until = target local noon + 90 local calendar days
  serialize each instant as explicit UTC Z

fast:
  active_from  = local start of target day
  exact_at     = target local noon
  active_until = local end of target day
  serialize each instant as explicit UTC Z
~~~

DST days may contain 23/25 UTC hours; local boundary semantics are authoritative.

Every eligible distractor must be shifted around the same case target without
fixed 2026 timing and without stealing selected IDs. Preserve story convergence
and expected anchor IDs.

Change helper return to expose HorizonSelectionResult with selection, reason,
and diagnostics. Do not assert non-null inside helper. Coverage must
count/report null selection rather than convert it to helper AssertionError.

Direct tests must assert exact UTC values for:

- New York leap day;
- Berlin DST transition day;
- Moscow normal day;
- UTC normal day.

## 6. Blocker R3-F4 — coverage loop неполный и может скрыть regressions

Текущий loop реально вызывает shifted helper, но не исполняет весь required
coverage pipeline из R1/R2.

Missing:

- strict case-layer assertions;
- selection reason/diagnostics handling;
- selected anchor exists exactly once in current layer;
- all timing boundaries complete;
- exact local/UTC target correspondence;
- loaded minimum impact threshold per horizon;
- complete product sphere provenance;
- explicit public validate_horizons_against_evidence defense-in-depth call;
- JSON dump/validate roundtrip;
- second guidance build byte identity;
- exact block equality after roundtrip;
- exact selected/contract-ready denominator semantics.

Current broad catch includes ValueError and AssertionError, which can turn a
test bug/invariant failure into a mere coverage counter and still allow >=95%.

### Required coverage loop

For each of the exact 60 cases:

1. Assert layer target date/time/tz equals case metadata.
2. Run selection and record null reason without helper assertion.
3. Assert selected anchor IDs each occur exactly once in current layer.
4. Assert timing target_local and target_utc correspond to case local 12:00.
5. Assert long/medium/fast raw boundaries match section 5 exact semantics.
6. Assert medium/fast exact peak non-null.
7. Assert anchor product spheres/provenance complete.
8. Assert anchor impact meets loaded min_candidate_impact[horizon].
9. Build fact pack.
10. Build tone.
11. Build HorizonGuidanceContext.
12. Build guidance.
13. Validate claims.
14. Explicitly call public cross-reference validator.
15. JSON dump and TodayV2HorizonsBlock.model_validate_json roundtrip.
16. Build guidance a second time.
17. Assert byte-identical canonical JSON for first/second/roundtrip blocks.

Do not catch AssertionError, Pydantic ValidationError, TypeError, or broad
ValueError as coverage failures. Those are test failures. Only expected typed
domain-not-ready errors may be classified into a breakdown.

Print exact:

~~~text
coverage: <valid>/60 <percent>
coverage_selected: <selected>/60
coverage_contract_ready: <ready>/<selected>
coverage_dates_timezones: 12 DATES / 5 TIMEZONES
coverage_failure_breakdown: <exact dict>
~~~

## 7. Blocker R3-F5 — validator remains fail-open

### 7.1 Architect residual matrix result

Original R2 18-case residual probe now gives:

~~~text
17/18 REJECT
strength_public_id -> ACCEPT_INVALID
~~~

_check_claims never checks exact public claim ID.

### 7.2 Additional independently accepted invalid mutations

All of these currently return successfully from
HorizonClaimValidator.validate():

~~~text
warnings_arbitrary
actions_heading_arbitrary
actions_heading_snake_case
action_natal_provenance
action_valid_subset
action_valid_reorder
manifestation_natal_provenance
manifestation_provenance_spheres
technique_nested_timing_peak_label
technique_nested_timing_state
~~~

Together with strength_public_id, there are at least 11 confirmed residual
fail-open paths.

### 7.3 Exact validator corrections

#### Whole block

Require exact:

~~~text
schema_version == today-horizons.v1
guidance_mode == deterministic
warnings == []
~~~

#### Strength/risk

Do not hand-check only some provenance fields. Reconstruct exact expected
strength/risk sequence across long -> medium -> fast using the same pure ranked
claim builder and one shared used_fact_ids set.

Compare exact expected vs public value including:

~~~text
None/non-None position
public id
kind
text
conditional
activation_ids
natal_fact_ids
profile_fact_ids
sphere_keys
~~~

This must reject:

- changed public ID;
- lower-ranked otherwise-valid fact;
- wrong statement kind/key/text;
- wrong horizon/theme/activation linkage;
- extra/missing/reused fact;
- every provenance list mutation.

#### Manifestations

Rebuild full expected ordered list with build_manifestations and compare full
typed value/model dump. This covers:

~~~text
id/title/condition/body/order/count
sphere_keys
activation_ids
natal_fact_ids == []
profile_fact_ids == []
provenance.sphere_keys
~~~

Do not swallow formatter exception with broad except Exception and fallback to
raw body. Formatter/canon corruption must fail closed.

#### Actions

Rebuild exact TodayV2HorizonActions using build_actions for each horizon and
compare full typed value:

~~~text
heading
valid_until
valid_until_label
do count/order/full item values
avoid count/order/full item values
all provenance lists
~~~

No valid subset, reorder or extra compatible canonical action may pass.

Policy checks still run separately to produce policy-specific codes for
forbidden/unsupported/leakage/intent mutations.

#### Technique

Rebuild exact single expected TodayV2TechniqueExplanation and compare full model
equality, including complete nested timing:

~~~text
active_from/exact_at/active_until
precision
state
range_label
peak_label
state_label
timezone
~~~

Do not compare only raw fields + range/state label.

#### Evidence and validation order

Duplicate evidence must reject exact code:

~~~text
evidence_duplicate
~~~

Current code uses public_cross_reference_invalid; correct it.

Required order:

1. evidence uniqueness and safe maps;
2. policy/leakage/numeric scan on all public strings;
3. exact deterministic alignment;
4. public cross-reference defense in depth.

Current implementation calls public cross-reference before policy despite the
comment saying policy is first. Move the actual call.

Never forward raw str(exc) from public validation into
HorizonClaimValidationError.

## 8. Blocker R3-F6 — policy scan is not actually all-field

Current check_no_raw_leakage omits at least:

- public timing range/peak/state labels;
- actions heading;
- actions valid-until label;
- technique nested timing range/peak/state labels;
- warnings.

Current conditional/unsupported/numeric lists also differ and omit fields.

Create one shared iterator of (stable_structural_path, text) and reuse it for
forbidden, unsupported, leakage and numeric policy as applicable.

It must cover every user-visible string:

~~~text
intro eyebrow/headline/body
horizon eyebrow/title/summary/plain explanation
horizon timing range/peak/state labels
manifestation title/condition/body
strength/risk text
actions heading/valid-until label/do/avoid text
technique label/what/why
technique nested timing range/peak/state labels
warnings if non-empty before exact warning rejection
~~~

Action heading containing structure_boundaries_control currently passes; add an
exact regression expecting internal_copy_leak.

Policy mutation tests must reach policy codes, not an earlier canonical action
text mismatch:

~~~text
forbidden_claim
unsupported_life_claim
internal_copy_leak
numeric_claim_not_grounded
conditional_policy_invalid
action_intent_conflict
action_verdict_conflict
~~~

Use a test-specific valid shape/canon override or mutate a field whose exact
alignment happens after policy. Do not label action_not_authorized as proof
that forbidden/unsupported policy ran.

If selected template intent is in forbidden_intents, reject it. Current code
continues and silently accepts it.

If referenced safety class is missing, reject. Current code skips verdict
validation when safety is None.

## 9. Blocker R3-F7 — sanitization claim is false

Architect direct formatter probes:

~~~text
entity_display(RAW_DEBUG_SENTINEL)
-> unsupported_entity_label | entity | id=RAW_DEBUG_SENTINEL

source_label(PROFILE_NAME_SENTINEL)
-> unsupported_entity_label | source_planet | id=PROFILE_NAME_SENTINE

target_label(planet, SESSION_SENTINEL)
-> unsupported_entity_label | planet | id=SESSION_SENTINEL
~~~

Raw sentinel/input is visibly leaked.

There are also many raw interpolations across validator/policy/builders/service:

~~~text
fact IDs
claim IDs
manifestation IDs
action IDs
technique keys
theme/sphere/entity keys
activation IDs
raw public cross-reference exception text
~~~

### Required correction

Every B2B2 exception string may contain only:

- stable closed error code;
- stable structural path;
- closed horizon name or numeric list index.

It may not contain source value, claim body, raw ID/key, sentinel or profile
fact. Remove raw values from every item_id and interpolated detail in allowlist.

If HorizonGuidanceError.item_id remains for type compatibility, callers in B2B2
must pass only a safe closed opaque index, never source input.

Replace test_sanitized_exception:

- current test checks unrelated words testimony/свидетельство;
- it does not inject those words or required sentinels;
- it has no else-fail if exception is not raised.

Create parametrized sentinel matrix across formatter, service, builder,
validator and policy paths. For every case:

~~~text
exception must be raised
exact error code/path asserted
sentinel absent from str(exc)
raw source ID/body absent from str(exc)
~~~

Required sentinels:

~~~text
RAW_EVIDENCE_SENTINEL
RAW_DEBUG_SENTINEL
PROFILE_NAME_SENTINEL
PROFILE_CITY_SENTINEL
COORDINATE_SENTINEL
SESSION_SENTINEL
~~~

## 10. Blocker R3-F8 — mutation matrix still contains false/no-op proofs

Current matrix contains:

~~~text
timezone: UTC -> UTC, expected_code=None
~~~

This is not an invalid mutation and must not be counted.

Other deficits:

- no independent timing state mutation;
- no non-noop valid timezone mutation;
- no strength/risk public ID mutation;
- no lower-ranked valid fact mutation;
- no fact activation/sphere/natal provenance mutations as separate cases;
- no manifestation natal/sphere provenance cases;
- no action heading/subset/reorder/natal provenance cases;
- no action tone/verdict/intent cases;
- no complete nested technique state/peak/timing cases;
- forbidden/unsupported action cases are caught by action_not_authorized, not
  intended policy code;
- action helpers often replace full do list with [changed], so count/list
  change can mask the named field mutation;
- some helpers return unchanged baseline when preconditions fail;
- exact fact ID leak uses fake fact_id_12345, not actual fact ID;
- privacy sentinel matrix is absent;
- deprecated instance model_fields access emits 19 warnings.

### Required mutation test rules

- every registered case must actually differ from baseline;
- every case must expect rejection; no expected_code=None;
- if precondition is absent, fail setup, never return baseline;
- preserve all unrelated siblings/count/order for single-field cases;
- use exact actual activation/fact IDs for leakage cases;
- assert exact intended code;
- no broad exception class;
- total invalid mutation cases >=70 after all mandatory additions;
- callback reports equal rejected/total numbers;
- zero new Pydantic deprecation warnings from B2B2 tests.

Use type(instance).model_fields or class metadata, not deprecated instance
access.

## 11. Mandatory gates

### 11.1 Focused

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q
~~~

Focused output must have no B2B2 Pydantic deprecation warning.

### 11.2 Evidence outputs

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_coverage.py -q -s

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q -s
~~~

### 11.3 Upstream

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py \
  apps/api/tests/test_horizon_selection_benchmark.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py -q
~~~

### 11.4 GRACE exact 12 files

Run exact full command from document 70. Required:

~~~text
grace_lint: PASS — 12 file(s) clean
~~~

### 11.5 Contracts/full API

~~~bash
pnpm contracts:check
apps/api/.venv/bin/python -m pytest apps/api/tests -q
~~~

Full API may show only the exact six baseline IDs from documents 69/70.

### 11.6 Final static

~~~bash
git diff --check
git diff --cached --quiet
~~~

Also scan untracked allowlist for trailing whitespace and production lines
over 140. Re-run line counts. Exact allowlist only. No commit/push.

## 12. Callback

Return exactly:

~~~text
READY_STAGE_B2B2_R3_REVIEW
changed_paths: <exact code/test/fixture paths>
accepted_head_unchanged: c47863a0c4b2be2242c276bb610a262b4b91a737
production_split: PASS <all production line counts>
test_sizes: PASS <all test line counts <=700>
grace: PASS 12/12 ZERO_VIOLATIONS
focused_tests: <result, zero B2B2 deprecation warnings>
strict_yaml_mutations: <rejected>/<total> REJECT
shifted_story_regressions: 4/4 PASS <NY leap/Berlin DST/Moscow/UTC>
coverage: <valid>/60 <percent>
coverage_selected: <selected>/60
coverage_contract_ready: <ready>/<selected>
coverage_dates_timezones: 12 DATES / 5 TIMEZONES
coverage_roundtrip_byte_identity: 60/60 PASS
coverage_failure_breakdown: <exact>
residual_fail_open_probes: 18/18 REJECT
additional_r3_fail_open_probes: 10/10 REJECT
claim_mutations: <rejected>/<total>=70 REJECT_BY_INTENDED_CODE
policy_code_matrix: PASS <exact codes>
sanitized_errors: PASS <sentinel cases, zero raw values>
pipeline_benchmark: p95=<ms> runs=20 combinations=1728 all_runs=23/23
upstream_regression: <result>
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact six baseline IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
~~~

Do not return READY until every line is backed by an executed gate. After the
callback, stop.
