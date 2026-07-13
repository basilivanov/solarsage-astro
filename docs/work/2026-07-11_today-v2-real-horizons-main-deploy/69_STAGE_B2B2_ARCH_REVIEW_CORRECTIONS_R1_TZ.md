# Stage B2B2 — architect review corrections R1

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted HEAD/origin: `c47863a0c4b2be2242c276bb610a262b4b91a737`
Parent: `68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md`
Статус: **NOT ACCEPTED — CORRECT R1, NO COMMIT/PUSH**

## 0. Режим

Исправить B2B2 по этому документу. Не начинать B3.

Запрещено:

- субагенты;
- `git add`/commit/push;
- изменение accepted B1/B2A/B2B1 files;
- public contract/generated contract changes;
- Today/Semantic/Calendar/frontend/sidecar integration;
- threshold/selection/canon changes;
- LLM/log/cache/version/settings work.

После исправлений выполнить все gates и вернуть callback section 12.

## 1. Независимо воспроизведённые blockers

### R1-F1 — callback falsely reports GRACE SKIP

Скрипт существует:

```text
/opt/solarsage-astro/scripts/grace_lint.py
```

Architect run:

```text
grace_lint: FAIL — 70 violations across 10 files
```

В том числе:

- `horizon_guidance_service.py` has
  `START_MODULE_MAP` + wrong `END_MODULE_MODULE`;
- production properties/helpers lack function contracts;
- nearly every public test function lacks function contract.

`grace: SKIP` недопустим. Required result is real `PASS`.

### R1-F2 — timing formatter emits raw machine copy and accepts invalid timezone

Architect output:

```text
long   Ориентир до 2026-12-31
medium Актуально до 2026-09-30T00:00:00Z
fast   Короткий пик ослабеет к 2026-07-12T23:00:00Z
```

These are raw machine values, not human Russian labels.

Also accepted:

```text
timezone=Not/A_Zone
precision=date
-> ACCEPT_INVALID
```

Other formatter defects:

- date regex does not validate a real calendar date;
- invalid timezone is not wrapped into `invalid_timezone`;
- long instant range omits timezone suffix;
- house target is not restricted to 1..12;
- missing transit source becomes generic `планета` instead of fail closed;
- `entity_display` may return a raw unknown machine key;
- technique active/exact placeholders use raw strings;
- unresolved template placeholders are not rejected;
- error paths sometimes contain raw input instead of structural path.

### R1-F3 — claim validator is fail-open

Architect probes returned:

```text
ACCEPT_INVALID changed_state_and_labels
ACCEPT_INVALID unsupported_strength_text
ACCEPT_INVALID invented_manifestation_body
ACCEPT_INVALID embedded_snake_case
```

Exact examples accepted:

```text
timing.state=active with arbitrary range/state labels
strength.text="У вас диагноз и это уже факт."
manifestation.body="Ваш работодатель уже решил вас уволить."
title contains structure_boundaries_control
```

Root causes:

- formatted timing/state/valid-until labels are not recomputed;
- timing state itself is not aligned;
- strength/risk exact fact kind/text/provenance is not validated;
- manifestation exact condition/body/title/order/provenance is not validated;
- unsupported-life scan excludes strength/risk/actions/manifestations;
- forbidden scan skips conditional actions;
- snake_case regex only works when the whole string is snake_case;
- exact activation/fact IDs and sentinels are not scanned in human copy;
- technique label/definition/why copy is not validated exactly;
- action intent conflict and forbidden intent pairs are not implemented;
- numeric validation excludes plain explanation and technical copy;
- test mutations are often rejected by unrelated action text mismatch or public
  validation and therefore do not prove the named claim check.

### R1-F4 — 60-case coverage is not real

`test_horizon_coverage.py` ignores:

- YAML file;
- case target date;
- case timezone;
- `shifted_story_for`.

It calls the same fixed:

```text
build_selected_story(...)
target_date=2026-07-12
target_tz=UTC
```

sixty times.

The YAML is dead duplicated metadata.

`shifted_story_for("2028-02-29", "America/New_York", ...)` independently
fails with `AssertionError` because it still constructs a hardcoded
2026-07-12/UTC ActivationLayer.

Coverage therefore proves neither dates, timezones, DST nor leap day.

### R1-F5 — benchmark excludes most of the required pipeline

Current test measures only:

```text
guidance -> validator
```

It excludes:

- HorizonSelectionService;
- PersonalFactPackService;
- HorizonToneService;
- context construction.

It uses a small three-anchor preselected story and never asserts 1728
combinations. The reported `p95=1.2ms` is therefore not the required benchmark.

The unused `build_worst_case_pipeline_input` is broken:

```text
creates 1728 activations instead of a bounded 120-activation population
SphereScoreV2 construction -> ValidationError
```

### R1-F6 — tests contain false proofs

Examples:

- invalid-timezone test mutates the date, not timezone;
- valid-until test only asserts truthiness;
- avoid-verdict test does not pass avoid verdict and only asserts block exists;
- empty-natal test calculates `all_empty` but never asserts it;
- profection/transit tests assert only non-empty strings;
- privacy test does not inject sentinels;
- “reused fact” test duplicates activation evidence instead;
- forbidden/raw/numeric tests are caught first by canonical action text mismatch;
- broad `raises((HorizonClaimValidationError, ValueError))` hides which layer
  rejected the mutation.

## 2. Corrected exact allowlist

May modify the original untracked B2B2 files:

```text
apps/api/app/schemas/horizon_guidance.py

apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_claim_validator.py

apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/test_horizon_guidance_formatter.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_pipeline_benchmark.py
apps/api/tests/fixtures/horizon_guidance_coverage.v1.yml
```

May create exactly two production split modules:

```text
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_claim_policy.py
```

Architect docs already present/created:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/69_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R1_TZ.md
```

Do not edit `68` or `69`.

No other path.

## 3. Required production split

The current service at 644 lines and validator at 650 lines cannot receive the
missing checks and GRACE contracts maintainably.

Required ownership:

### 3.1 horizon_guidance_service.py

Target <=350 lines.

Own only:

- cached dependencies;
- context preflight;
- primary/horizon theme resolution;
- long/medium/fast orchestration;
- typed public block construction.

Do not own large action/fact/manifestation/technique algorithms.

### 3.2 horizon_guidance_builders.py

Target <=650 lines.

Own:

- stable ordered intersection;
- manifestations;
- eligible/ranked/unique strength-risk claims;
- action eligibility/selection/public items;
- technique explanation construction;
- exact deterministic expected-copy helpers shared by validator.

No import from validator or Today/Semantic.

### 3.3 horizon_claim_validator.py

Target <=400 lines.

Own:

- orchestration;
- evidence/fact/tone maps;
- public cross-reference wrapper;
- exact intro/horizon/timing/fact/manifestation/technique alignment;
- delegation to policy module;
- sanitized failure helper.

### 3.4 horizon_claim_policy.py

Target <=650 lines.

Own:

- action authorization/verdict/intent conflicts;
- conditional policy;
- unsupported-life policy;
- forbidden certainty/high-stakes scan;
- internal/raw/sentinel leakage scan;
- numeric/canonical-copy integrity;
- reusable text enumeration/normalization.

No cycle:

```text
formatter -> schemas/canons
builders  -> formatter/schemas/canons
guidance  -> builders/formatter/schemas/canons
policy    -> builders/formatter/schemas/canons
validator -> policy/builders/formatter/schemas/canons/public helper
```

## 4. Typed timing presentation; remove placeholder public model

Extend `horizon_guidance.py` with frozen:

```py
class HorizonTimingPresentation(BaseModel):
    public_timing: TodayV2HorizonTiming
    active_from_label: str
    active_until_label: str
    exact_at_label: str | None
    valid_until_label: str
    timezone_suffix: str
```

Strict/frozen/hide input.

Formatter signature:

```py
def format_timing(
    *,
    horizon: TodayV2HorizonId,
    timing: HorizonTimingAssessment,
) -> HorizonTimingPresentation:
    ...
```

Delete the construction of a public timing model with:

```text
range_label="placeholder"
peak_label="placeholder peak"
state_label="placeholder"
```

No sentinel/fallback `—`. Missing formatted copy is a programming/config error.

## 5. Exact formatter corrections

### 5.1 Validate first

For every precision:

- instantiate `ZoneInfo(timezone)` before formatting;
- unknown -> exact code `invalid_timezone`;
- never expose ZoneInfo exception/body in error;
- date uses `date.fromisoformat`, not regex alone;
- instant uses `datetime.fromisoformat` after `Z -> +00:00`;
- require aware instant;
- wrap as `invalid_timing_value` with structural path only.

### 5.2 Human labels

`active_until_label` is formatted local display, never raw ISO.

Exact valid-until:

```text
long date:
Ориентир до 31 декабря 2026

medium instant Moscow:
Актуально до 30 сентября 2026, 03:00 по Москве

fast instant Moscow:
Короткий пик ослабеет к 13 июля 2026, 02:00 по Москве
```

Actual hour depends on exact raw input; tests calculate expected conversion.

All instant range/peak/valid-until labels carry one timezone suffix, including
long instant.

### 5.3 Entities

- strip repeated prefixes for source and target;
- known planet/source exact mapping;
- selected transit with null/unknown source ->
  `unsupported_entity_label`;
- planet/angle unknown -> same code;
- lot unknown -> safe generic allowed;
- house parse exact integer 1..12, otherwise reject;
- sphere uses canon;
- remove raw fallback from `entity_display` or make unknown reject;
- no output machine key fallback.

### 5.4 Technique templates

Render display values, not raw:

```text
active_from -> presentation.active_from_label
active_until -> presentation.active_until_label
exact_at -> presentation.exact_at_label or ""
range_label -> public timing.range_label
peak_label -> public timing.peak_label or ""
state_label -> public timing.state_label
```

After replacement, any brace/placeholder remains -> fail.

For selected techniques whose template requires source:

- missing/unknown source fails;
- never default to `планета`.

## 6. Exact deterministic claim validation

Validator must independently reconstruct expected values from context, canons,
formatter and builders. It must not merely trust generator output.

### 6.1 Intro/horizon exact

Check exact:

- guidance mode;
- intro eyebrow/headline/body/theme/IDs;
- item id `horizon.<horizon>`;
- horizon eyebrow/title/summary/plain explanation;
- activation IDs;
- tone;
- likely spheres.

Any deterministic text mutation rejects with specific structural code.

### 6.2 Timing exact

Recompute `HorizonTimingPresentation` for each anchor.

Require:

```py
item.timing.model_dump() == presentation.public_timing.model_dump()
item.actions.valid_until == presentation.public_timing.active_until
item.actions.valid_until_label == presentation.valid_until_label
```

This must reject independent mutations of:

- state;
- active_from;
- exact_at;
- active_until;
- precision;
- timezone;
- range_label;
- peak_label;
- state_label;
- valid_until;
- valid_until_label.

### 6.3 Strength/risk exact

For every public strength/risk:

- exact kind position;
- exact public item ID;
- exactly one natal fact ID;
- fact exists;
- fact kind matches;
- statement key exists and statement kind matches;
- text exact statement text;
- conditional false;
- current horizon/activation/theme/sphere linkage exact;
- provenance activation exact current anchor;
- provenance natal ID exact fact;
- profile IDs empty;
- provenance spheres exact ordered intersection;
- no fact reused.

Also prove the selected public claim is the same deterministic ranked unused
fact the builder should select. A lower-ranked arbitrary valid fact is not
accepted.

### 6.4 Manifestations exact

Require exact one per likely sphere, exact order:

- ID;
- title;
- split condition;
- split body;
- sphere list;
- activation/sphere provenance;
- empty natal/profile provenance.

No arbitrary body/condition/title.

### 6.5 Technique exact

Exactly one per anchor and all fields exact:

- technique key;
- label;
- what_it_is;
- why_it_matters_now;
- timing full model equality;
- activation IDs.

Arbitrary “safe” new explanation must reject, not only forbidden phrases.

### 6.6 Actions exact and intent conflict

For every action:

- exact resolved theme/horizon/bucket;
- exact canonical text/conditional/provenance;
- exact selected canonical order/count;
- tone compatible;
- every supplied linked verdict compatible;
- safety class exists;
- intent belongs to correct closed positive/avoid type;
- no forbidden intent.

Across all horizons explicitly evaluate loaded `forbidden_intent_pairs`.
Mutation tests must be able to reach `action_intent_conflict`, not be caught by
unrelated public validation.

## 7. Policy and leakage corrections

### 7.1 Scan every user-visible field

Include:

- intro all text;
- horizon eyebrow/title/summary/plain explanation;
- timing range/peak/state;
- manifestation title/condition/body;
- strength/risk text;
- action heading/valid-until label/do/avoid text;
- technique label/definition/why and nested timing labels.

### 7.2 Forbidden applies everywhere

Loaded certainty/high-stakes fragments reject regardless of conditional flag.

Conditional does not make `Если ..., увольняйтесь` safe.

### 7.3 Unsupported life claims

Apply to every field.

Conditional scenario allowance is narrow:

- manifestation condition may contain a scenario because it starts exact
  loaded prefix;
- conditional action may contain scenario only when exact canonical template;
- manifestation body tail cannot introduce a new employer/partner/debt/
  diagnosis/event assertion;
- strength/risk cannot contain such assertion.

### 7.4 Internal leakage

Reject embedded tokens, not just whole-string matches:

- `Transit_`/`Natal_`;
- every exact selected activation ID;
- every exact fact ID;
- privacy sentinels;
- any whole token matching snake_case.

Implement token/finditer logic correctly.

### 7.5 Numeric integrity

Because deterministic copy is exact reconstructed copy:

- canonical intro/theme/action/fact/manifestation fields must equal expected;
- timing/technique values must equal formatter output;
- any extra numeric token therefore rejects;
- do not exclude plain explanation from validation.

## 8. Real coverage corpus

### 8.1 YAML is the sole metadata source

`build_coverage_cases` must strict-load
`tests/fixtures/horizon_guidance_coverage.v1.yml`.

Add test-only strict Pydantic models:

- extra forbid;
- exact schema version;
- exactly 5 profiles;
- exactly 12 dates;
- profile IDs unique;
- exact listed profile set;
- valid IANA timezones;
- known story/natal cases;
- dates valid/unique and exact listed set.

Delete duplicate hardcoded profile/date lists from Python.

### 8.2 shifted_story_for must really shift

Build `ActivationLayer` directly with:

```text
target_date=<case date>
target_time=12:00
target_tz=<case timezone>
```

Use `ZoneInfo` and local aware datetimes.

By expected story IDs:

- long -> local-year date range, exact null;
- medium -> local noon ±90 days, exact local noon;
- fast -> local target-day start/end, exact local noon;
- distractor -> preserve an eligible exact short/medium window around same
  target; never leave fixed 2026 timing.

Convert instant values to explicit UTC `Z`.

Return actual `HorizonSelectionResult` plus layer/scoring/natal, or another
shape that exposes selection reason/diagnostics. Do not assert away null
selection before coverage can count it.

### 8.3 Coverage loop

For each of 60 YAML cases, use its actual:

- date;
- timezone;
- story;
- natal case;
- verdict case.

Run:

```text
selection
contract-ready
fact pack
tone
context
guidance
claim validator
public cross-reference
TodayV2HorizonsBlock JSON roundtrip
second build byte identity
```

Assert:

- YAML cases exact 60;
- coverage >=95%;
- every selected anchor activation exists in that case layer;
- selected timing boundaries complete;
- medium/fast exact;
- product sphere provenance complete;
- every selected anchor impact >= loaded
  `min_candidate_impact[horizon]`;
- no hidden skip/catch-all success.

Print actual failure breakdown.

## 9. Real full-pipeline benchmark

### 9.1 Worst-case input

Build a valid 120-activation layer using the accepted B2A benchmark pattern:

```text
40 long-capable
40 medium-capable
40 fast-capable
```

B2A post-bound must be exactly:

```text
12 long
12 medium
12 fast
```

and `combinations_evaluated == 1728`.

Do not create 1728 activations.

Builder itself must be directly tested/used and produce valid
`ScoringV2Result`.

### 9.2 Timed body

Fixture construction and service construction stay outside.

Every warmup/measured run includes:

```text
HorizonSelectionService.select
PersonalFactPackService.build
HorizonToneService.assess
HorizonGuidanceContext construction
HorizonGuidanceService.build
HorizonClaimValidator.validate
```

Do not reuse precomputed selection/facts/tone/context.

Protocol exact:

- 3 warmups;
- 20 measured;
- p95 index exact;
- p95 <100ms;
- every run valid block;
- every run combinations 1728.

Print exact:

```text
horizon_pipeline_benchmark: p95=<ms> runs=20 combinations=1728
```

## 10. Test adequacy corrections

### 10.1 GRACE

Run real script on all 12 original/new code/test files plus the two split
modules. Every violation fixed.

Public test functions get concise real function contracts. Update module maps.

### 10.2 Formatter

Tests assert exact strings, not truthiness:

- invalid timezone is actually invalid timezone;
- invalid calendar date;
- exact state label;
- exact range/peak/valid-until;
- long instant suffix;
- date/instant local conversion;
- 1 and 12 house valid, 0/13/raw invalid;
- missing transit source;
- unresolved placeholder;
- no raw fallback.

### 10.3 Guidance

Replace false proofs:

- avoid test passes actual all-avoid verdict map and checks incompatible IDs
  absent + compatible fallback IDs present;
- empty natal asserts all strength/risk are null;
- technique tests assert actual expected Russian label/definition/theme/range/
  source/target;
- privacy test injects sentinels into evidence/debug/unconsumed natal fields;
- context mismatch tests assert exact codes;
- test both medium and fast missing peak;
- verdict insertion order byte-identical.

### 10.4 Claim mutations

Minimum independent matrix:

```text
duplicate evidence
intro eyebrow/headline/body/theme/IDs
horizon id/eyebrow/title/summary/plain copy
tone
each raw timing field
each timing label
valid_until raw/label
likely spheres
unknown/reused/lower-ranked/wrong-kind/wrong-text/wrong-provenance fact
profile fact
manifestation id/title/condition/body/sphere/provenance/order
action wrong theme/bucket/text/conditional/provenance/tone/verdict/intent
duplicate action
technique key/label/definition/why/timing/activation
certainty/high-stakes in conditional and nonconditional fields
employer/partner/debt/diagnosis/event in strength/manifestation/technique
embedded snake_case
Transit_/Natal_
activation ID in text
fact ID in text
privacy sentinel in text
invented numeric date outside timing
sanitized exception
```

Use exact expected error code. Do not use broad `ValueError` unless testing
public Pydantic boundary itself.

Architect acceptance target:

```text
claim-specific invalid mutations >= 40
all rejected by intended code
```

## 11. Gates

Focused:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest \
  tests/test_horizon_guidance_formatter.py \
  tests/test_horizon_guidance_service.py \
  tests/test_horizon_claim_validator.py \
  tests/test_horizon_coverage.py \
  tests/test_horizon_pipeline_benchmark.py -q
```

Upstream:

```bash
.venv/bin/python -m pytest \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_ordering.py \
  tests/test_horizon_selection_benchmark.py \
  tests/test_personal_fact_pack_service.py \
  tests/test_horizon_tone_service.py -q
```

GRACE from repo root:

```bash
cd /opt/solarsage-astro
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_guidance.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_builders.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/tests/_horizon_guidance_testkit.py \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py
```

Then:

```bash
pnpm contracts:check
cd apps/api && .venv/bin/python -m pytest tests -q
```

Full API may contain exact same six baseline failure IDs only.

Final:

- all production <=650 lines;
- validator <=400;
- guidance service <=350;
- tests <=700;
- production lines <=140;
- explicit trailing whitespace scan;
- `git diff --check`;
- index empty;
- no commit/push.

## 12. Callback

```text
READY_STAGE_B2B2_R1_REVIEW
changed_paths: <exact paths>
production_split: PASS <line counts>
grace: PASS <file count>
timing_formatter: PASS <exact cases>
valid_until_human_copy: PASS <long/medium/fast samples>
invalid_timezone: REJECT
transit_source_fail_closed: PASS
claim_mutations: <rejected>/<total> REJECT
architect_fail_open_probes: 4/4 REJECT
unsupported_claims: ZERO
privacy_sentinels: PASS
coverage_yaml_source: PASS
coverage: <valid>/60 <percent>
coverage_selected: <n>/60
coverage_contract_ready: <n>/<selected>
coverage_dates_timezones: 12 DATES / 5 TIMEZONES
coverage_failure_breakdown: <exact>
pipeline_benchmark: p95=<ms> runs=20 combinations=1728
focused_tests: <result>
upstream_regression: <result>
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact six IDs>
size_limits: PASS <all counts>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
```

После callback остановиться.
