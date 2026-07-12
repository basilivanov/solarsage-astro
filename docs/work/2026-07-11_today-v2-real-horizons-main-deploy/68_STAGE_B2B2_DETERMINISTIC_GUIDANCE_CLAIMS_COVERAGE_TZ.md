# Stage B2B2 — deterministic guidance, claim validation and coverage

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Accepted HEAD/origin: `c47863a0c4b2be2242c276bb610a262b4b91a737`  
Parents: `50_...`, `51_...`, `63_...`, accepted B2A/B2B1  
Статус: **IMPLEMENT B2B2 ONLY — NO COMMIT/PUSH**

## 0. Контекст для новой coding-сессии

Ты продолжаешь работу после другой coding-сессии. Не восстанавливай решения по
tmux history и не переделывай принятые волны.

Приняты и уже запушены:

```text
3a58c581bbe010e98e78b2295a135f138d32bd88
feat(today): add grounded three-horizon contract

cd27d1a8056eef92737e992c1b0998423331734b
feat(today): add deterministic horizon selection

c47863a0c4b2be2242c276bb610a262b4b91a737
feat(today): add grounded horizon content pipeline
```

Текущий tracked tree должен быть чистым. Допустимые старые unrelated untracked:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Их не читать без необходимости, не редактировать, не добавлять в index.

Уже существуют и считаются immutable inputs:

- B1 public `TodayV2HorizonsBlock` и validators в
  `apps/api/app/schemas/today_horizons.py`;
- B2A `SelectedHorizonTriple`, raw timing, sphere/theme mapping и bounded
  deterministic selection;
- B2B1 strict language/action/personal-pattern canons;
- B2B1 `PersonalFactPack`;
- B2B1 `HorizonToneResult`.

Эта волна строит из них complete deterministic public block и независимо
валидирует каждое утверждение. Production Today flow пока не подключается.

## 1. Роль и запреты

Ты — coding executor. Архитектор принимает diff после callback.

Обязательно:

- прочитать полностью этот файл до правок;
- прочитать применимые root `AGENTS.md`;
- соблюдать GRACE для каждого нового code/test file;
- реализовать только exact allowlist;
- использовать только deterministic, typed, in-process code;
- вернуть callback и остановиться.

Запрещено:

- субагенты/delegated agents;
- `git add`, commit, push;
- B3/Today/Semantic/Calendar integration;
- изменение public contract или generated contracts;
- изменение B2A selection/canon/thresholds;
- изменение B2B1 canons/schemas/services;
- LLM/provider/prompt work;
- DB/migration/settings/env;
- frontend/fixture runtime/preview;
- sidecar calls, network, filesystem runtime writes;
- server wall clock;
- logging/events/version/cache changes;
- main/systemd/nginx/production ports.

Если exact B1 contract нельзя построить из конкретного selected triple, нельзя
выдумывать данные или менять selection. Нужно fail closed структурным error
code и доказать этот boundary тестом.

## 2. Exact allowlist

Разрешено создать только:

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

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md
```

Нельзя менять существующий accepted file. Если обнаружена объективная
необходимость изменить существующий file, остановиться и вернуть
`BLOCKED_STAGE_B2B2_ALLOWLIST` с точным path/reason. Не расширять scope самому.

## 3. Public и product invariants

Результат для contract-ready input:

```py
TodayV2HorizonsBlock(
    schema_version="today-horizons.v1",
    guidance_mode="deterministic",
    intro=...,
    items=[long, medium, fast],
    warnings=[],
)
```

Обязательно:

- ровно long, medium, fast;
- один selected anchor на один public horizon;
- raw timing copied exactly from accepted anchor;
- human labels formatted in anchor target timezone;
- medium и fast имеют real `exact_at` и `peak_label`;
- ни один пик/дата/technique/fact не синтезируется;
- dynamic intro зависит от selected story;
- main text human-first;
- astrology terms находятся в technical disclosure;
- likely spheres — exact selected product spheres, 1..3;
- manifestations conditional and sphere-linked;
- actions exact from accepted action canon;
- strength/risk only from accepted fact pack;
- every public claim has typed provenance;
- output byte-identical for identical typed inputs;
- no raw evidence/debug/PII/previous LLM text.

### 3.1 Важный B1/B2A peak boundary

B1 public `TodayV2Horizon` требует:

```text
medium -> exact_at non-null + peak_label non-null
fast   -> exact_at non-null + peak_label non-null
```

B2A может технически выбрать period candidate без exact peak. B2B2 не меняет
B2A и не подставляет midpoint/start/end как “peak”.

`HorizonGuidanceService` обязан reject до public model construction:

```text
medium exact_at is null -> code=medium_peak_missing
fast exact_at is null   -> code=fast_peak_missing
```

Long exact may be null and это нормальный background period.

Coverage должен считать отдельно:

```text
selected
contract_ready
guidance_valid
```

Если contract-ready coverage ниже 95%, не менять B2A. Вернуть breakdown.

## 4. Internal schema

Создать `apps/api/app/schemas/horizon_guidance.py`.

Все модели:

```py
ConfigDict(
    extra="forbid",
    frozen=True,
    hide_input_in_errors=True,
)
```

### 4.1 HorizonGuidanceContext

Exact shape:

```py
class HorizonGuidanceContext(BaseModel):
    schema_version: Literal["horizon-guidance-context.v1"]
    selection: SelectedHorizonTriple
    fact_pack: PersonalFactPack
    tone_result: HorizonToneResult
    sphere_verdicts: dict[
        TodayV2ProductSphereKey,
        HorizonSphereVerdict,
    ]
```

After-validation:

1. `selection.items` exact long/medium/fast уже typed, но проверить снова через
   ordered IDs.
2. `fact_pack.selected_activation_ids` equals exact ordered selected IDs.
3. `tone_result.items` exact long/medium/fast.
4. Каждый tone item имеет ровно один activation ID.
5. Tone activation ID for each horizon equals selected anchor ID.
6. Все three anchor timing timezones equal.
7. Все three `target_local` and `target_utc` represent the same request clock
   already carried by B2A; mismatch rejects.
8. `sphere_verdicts` may be partial or all 12. Missing verdict is not invented.
9. No mutation/coercion of selection/facts/tone.

### 4.2 Typed errors

Создать compact exceptions:

```py
class HorizonGuidanceError(ValueError):
    code: str
    path: str
    item_id: str | None

class HorizonClaimValidationError(ValueError):
    code: str
    path: str
    item_id: str | None
```

Exceptions may live in schema or owning service, но должны:

- have stable machine `code`;
- stringify only code/path/opaque ID;
- never include human claim body, raw evidence, debug, natal values or profile.

Minimum guidance codes:

```text
context_alignment_invalid
medium_peak_missing
fast_peak_missing
invalid_timezone
invalid_timing_value
unknown_theme
unsupported_entity_label
invalid_manifestation_copy
insufficient_safe_actions
```

Minimum claim codes are listed in section 8.

## 5. Formatting and copy composition

Создать `horizon_guidance_formatter.py`. Он pure/stateless except cached strict
canon loader. No settings, locale process mutation or wall clock.

### 5.1 Exact public timing construction

Public raw fields copied exactly:

```text
active_from <- anchor.timing.active_from
exact_at <- anchor.timing.exact_at
active_until <- anchor.timing.active_until
precision <- anchor.timing.precision
state <- anchor.timing.timing_state
timezone <- anchor.timing.timezone
```

Reject if any required raw field is null.

For date precision:

- parse exact YYYY-MM-DD;
- do not timezone-shift date;
- Russian display: `D <genitive month> YYYY`;
- example: `8 июля 2026`.

For instant precision:

- parse explicit-offset RFC3339;
- convert with `zoneinfo.ZoneInfo(anchor.timing.timezone)`;
- display local date + HH:MM;
- never use server local timezone.

Exact timezone suffix policy:

```text
Europe/Moscow -> по Москве
UTC           -> UTC
other IANA    -> (<exact IANA timezone>)
```

Examples:

```text
12 июля 2026, 15:00 по Москве
8 ноября 2026, 07:30 (America/New_York)
```

Russian month map exact:

```text
1 января
2 февраля
3 марта
4 апреля
5 мая
6 июня
7 июля
8 августа
9 сентября
10 октября
11 ноября
12 декабря
```

The numbers above are month indexes, not output prefixes.

Use loaded language templates:

```text
range
peak
valid_until
long_valid_until
fast_eases
```

Range policy:

- template receives full formatted local boundaries;
- instant range gets one timezone suffix after active-until;
- date range has no timezone suffix in copy;
- precision/raw timezone still remain machine fields.

State label is exact
`language.timing_state_labels[anchor.timing.timing_state]`.

Peak label:

- null iff exact_at null;
- otherwise exact `timing_templates.peak` with local exact display.

Valid-until label:

```text
long   -> timing_templates.long_valid_until
medium -> timing_templates.valid_until
fast   -> timing_templates.fast_eases
```

`actions.valid_until` remains raw `timing.active_until`.

### 5.2 Entity labels for technical explanations

Do not import `SemanticV2Service`: B3 will import guidance, so that creates a
cycle.

The formatter owns only a closed machine-to-Russian display map, not
astrological interpretation.

Exact planet labels:

```text
SUN Солнце
MOON Луна
MERCURY Меркурий
VENUS Венера
MARS Марс
JUPITER Юпитер
SATURN Сатурн
URANUS Уран
NEPTUNE Нептун
PLUTO Плутон
CHIRON Хирон
NORTH_NODE Северный узел
SOUTH_NODE Южный узел
```

Exact angle labels:

```text
ASC Асцендент
DSC Десцендент
MC Меридиан MC
IC Надир IC
```

Known lot labels:

```text
FORTUNE Жребий Фортуны
SPIRIT Жребий Духа
EROS Жребий Эроса
MARRIAGE Жребий Брака
NECESSITY Жребий Необходимости
VICTORY Жребий Победы
NEMESIS Жребий Немезиды
```

Safe target label:

```text
planet -> ваш натальный <planet label>
angle  -> опорную точку <angle label>
lot    -> <known lot label>, unknown lot -> расчётную точку карты
house  -> область карты №<1..12>
sphere -> сферу «<product sphere language label>»
```

Transit source planet must be a known B2A speed-group planet. Missing/unknown
source on a selected transit rejects; do not output raw machine key.

Strip/never surface repeated `Transit_` / `Natal_` prefixes.

### 5.3 Manifestation split

B2B1 sphere `manifestation_body` is a full conditional sentence:

```text
Если <condition>, <body>.
```

Build public manifestation as:

```text
condition = text before first comma, trimmed
body = text after first comma, trimmed, first letter uppercased
```

Requirements:

- source `conditional=True`;
- condition starts one loaded `required_prefixes`;
- exactly one first split is enough; later commas stay in body;
- both parts non-blank;
- missing comma/parts -> `invalid_manifestation_copy`;
- do not duplicate full conditional sentence in both fields.

## 6. Deterministic guidance service

Создать `horizon_guidance_service.py`.

Public entrypoint:

```py
class HorizonGuidanceService:
    def build(
        self,
        *,
        context: HorizonGuidanceContext,
    ) -> TodayV2HorizonsBlock:
        ...
```

No optional untyped dict inputs.

### 6.1 Input preflight

Before output:

1. validate `HorizonGuidanceContext`;
2. exact selected IDs long/medium/fast;
3. medium/fast exact peak boundary section 3.1;
4. each anchor:
   - timing precision/state/bounds present;
   - product spheres 1..3;
   - theme keys non-empty;
   - activation ID non-blank <= public 160 max;
5. all referenced theme/sphere/technique keys exist in loaded canons;
6. do not catch schema/programming errors and return partial block.

### 6.2 Theme resolution

Primary story theme:

```py
primary_theme = context.selection.shared_theme_keys[0]
```

B2A already frequency-orders fallback union. Do not re-score/re-rank it.

Per-horizon theme:

```text
if primary_theme in anchor.theme_keys:
    use primary_theme
else:
    use anchor.theme_keys[0]
```

Unknown/empty -> fail. Do not substitute structure/control.

### 6.3 Intro

Exact composition:

```text
eyebrow       = "Личная логика периода"
headline      = language.themes[primary_theme].headline
body          = language.themes[primary_theme].intro_body
theme_key     = primary_theme
activation_ids = exact ordered selected IDs
```

Only eyebrow is stable section chrome. Headline/body must differ by theme.

Tests for structure, communication and relationships must assert three distinct
headline/body pairs.

### 6.4 Horizon identity and human copy

For each anchor:

```text
id                   = horizon.<long|medium|fast>
horizon              = anchor.horizon
tone                 = aligned tone assessment.tone
eyebrow              = language.horizons[horizon].eyebrow
title                = language.themes[horizon_theme][horizon].title
summary              = language.themes[horizon_theme][horizon].plain_explanation
plain_explanation    = "<tone label>. <state label>. <range label>."
timing               = formatter result
likely_spheres       = exact anchor.product_spheres
activation_ids       = [anchor.activation_id]
```

Do not include technique names in `summary` or `plain_explanation`.

### 6.5 Manifestations

Generate exactly one manifestation per `likely_spheres` item, preserving anchor
order. Therefore count is 1..3.

For each sphere:

```text
id = manifestation.<horizon>.<sphere>
title = language.product_spheres[sphere].manifestation_title
condition/body = split from section 5.3
sphere_keys = [sphere]
provenance.activation_ids = [anchor.activation_id]
provenance.natal_fact_ids = []
provenance.profile_fact_ids = []
provenance.sphere_keys = [sphere]
```

No profile context in B2B2.

### 6.6 Strength/risk selection

Eligible fact:

- kind exact strength or risk;
- current horizon in `fact.horizon_ids`;
- current anchor ID in `fact.activation_ids`;
- fact theme intersects anchor theme keys;
- fact sphere intersects anchor product spheres;
- statement exists and kind matches in language canon.

Stable rank:

```text
confidence desc
personal-pattern canon order asc
fact id lexicographic
```

At most one strength and one risk per horizon.

Avoid repeating the same fact across cards:

1. build eligible lists for all horizons;
2. long claims are assigned first, because product requires long strength/risk
   when available;
3. medium receives next unused eligible fact;
4. fast receives next unused eligible fact;
5. if a fact links only medium/fast, it may appear there;
6. no generic replacement when no unused fact exists.

Public grounded claim:

```text
id = claim.<horizon>.<fact.id>
kind = fact.kind
text = language.personal_statements[fact.statement_key].text
conditional = false
provenance.activation_ids = [current anchor id]
provenance.natal_fact_ids = [fact.id]
provenance.profile_fact_ids = []
provenance.sphere_keys =
  ordered intersection(anchor.product_spheres, fact.sphere_keys)
```

No raw natal source IDs on public wire. Public natal fact IDs are opaque fact IDs.

### 6.7 Action selection

Use per-horizon resolved theme, aligned tone and explicit sphere verdicts.

Candidate template must satisfy all:

1. is in exact theme/horizon/do-or-avoid canon bucket;
2. aligned tone is in `template.tones`;
3. ordered intersection of template sphere keys and anchor product spheres is
   non-empty;
4. for every supplied verdict on those intersected spheres, verdict is in
   `safety_class.compatible_verdicts`;
5. missing verdict is ignored, not converted to neutral;
6. template text/ID has not been selected elsewhere.

Preserve canon list order. Do not re-rank by Russian text.

Take up to public max:

```text
long:   do <=2, avoid <=2; require >=1 / >=1
medium: do <=3, avoid <=3; require >=2 / >=1
fast:   do exactly 1, avoid <=2; require 1 / >=1
```

If minima cannot be met after compatibility filtering, fail
`insufficient_safe_actions`. Do not emit incompatible advice.

Grounded action:

```text
id = exact canonical template.id
kind = action for do, avoid for avoid
text = exact template.text
conditional = exact template.conditional
provenance.activation_ids = [anchor.activation_id]
provenance.natal_fact_ids = []
provenance.profile_fact_ids = []
provenance.sphere_keys = ordered template/anchor sphere intersection
```

Action block:

```text
heading = language.horizons[horizon].actions_heading
valid_until = timing.active_until raw
valid_until_label = formatter policy section 5.1
```

The existing public contract/UI owns the avoid subsection rendering. Do not
concatenate `avoid_heading` into action body.

### 6.8 Technique explanation

Exactly one explanation per horizon/selected anchor in B2B2.

```text
technique = anchor.technique
label = language.techniques[technique].label
what_it_is = exact canon what_it_is
why_it_matters_now = render exact canon template
timing = exact same TodayV2HorizonTiming object/value as horizon.timing
activation_ids = [anchor.activation_id]
```

Template values:

```text
theme_label = resolved horizon theme label
range_label = timing.range_label
peak_label = timing.peak_label or ""
state_label = timing.state_label
source_label = section 5.2
target_label = section 5.2
sphere_label = first likely sphere label
active_from/active_until/exact_at = formatted display values
```

Only placeholders actually present are substituted. Unknown/unresolved
placeholder fails; no raw fallback.

Annual profection/firdar tests must prove definition + personal theme + real
range. Transit tests prove named source/target + range.

### 6.9 Output construction

Construct typed public models, not raw dict. Let all B1 Pydantic validators run.

Return:

```text
schema_version=today-horizons.v1
guidance_mode=deterministic
warnings=[]
```

No catch-and-partial return.

## 7. Claim validator API

Создать `horizon_claim_validator.py`.

Entrypoint:

```py
class HorizonClaimValidator:
    def validate(
        self,
        *,
        block: TodayV2HorizonsBlock,
        context: HorizonGuidanceContext,
        activation_evidence: Sequence[ActivationEvidence],
    ) -> TodayV2HorizonsBlock:
        ...
```

Return the same block object/value when valid.

It validates deterministic output now and is designed so B3 can extend it for
LLM candidate-vs-baseline validation. Do not implement LLM in this wave.

### 7.1 Exact source maps

Build:

```text
selected anchor by horizon
selected activation ID set
activation evidence by ID
personal fact by ID
action template by ID + owning theme/horizon/bucket
technique language by key
sphere language by key
tone by horizon
```

Reject duplicate activation evidence IDs before dict construction.

### 7.2 Public cross-reference

Call accepted `validate_horizons_against_evidence` after duplicate-ID check.

Wrap failures in sanitized `HorizonClaimValidationError` without claim body.

### 7.3 Exact immutable alignment

Validate:

- block mode deterministic;
- intro theme exact primary theme;
- intro IDs exact selected ordered IDs;
- horizon order and IDs exact;
- each horizon activation ID exact one anchor ID;
- tone exact aligned B2B1 tone;
- raw timing exact selected timing;
- formatted timing/state/valid-until labels exact formatter recomputation;
- likely spheres exact anchor product spheres;
- technique exact actual anchor technique;
- technique activation IDs exact anchor;
- explanation timing exact horizon timing;
- strength/risk facts exist and are linked;
- no fact ID reused across cards;
- manifestations exact likely sphere set/order;
- no profile fact IDs in B2B2;
- every nested sphere is within likely spheres.

### 7.4 Action authorization

For each action:

- ID exists in exact resolved theme/horizon bucket;
- do/avoid bucket matches kind;
- text equals canonical template text in deterministic mode;
- conditional exact template value;
- provenance activation exact anchor;
- provenance sphere exact ordered intersection;
- tone compatible;
- every supplied verdict compatible with safety class;
- intent belongs to correct positive/avoid closed type;
- no forbidden intent;
- no canonical `forbidden_intent_pairs` conflict across all horizons;
- no normalized duplicate text globally.

### 7.5 Conditional and unsupported-life policy

All loaded forbidden certainty/high-stakes fragments are scanned
case-insensitively with normalized whitespace across every user-visible string.

Also reject direct unsupported assertions containing these normalized patterns
unless the owning item is explicitly conditional and begins with a loaded
required prefix:

```text
у вас есть партнёр
ваш муж
ваша жена
ваша должность
ваш работодатель
у вас есть долг
ваш кредит
ваш доход
у вас болезнь
у вас диагноз
вас уволят
вы увольняетесь
вы переедете
сделка состоится
это уже произошло
```

Deterministic intro/title/summary/plain explanation/technique text are never
treated as conditional item. They therefore cannot contain these assertions.

Manifestation:

- `condition` required;
- condition starts loaded prefix;
- body non-conditional tail contains no new scenario assertion.

Action:

- if template.conditional=true, output text starts loaded prefix;
- if false, output cannot make an unsupported scenario assertion.

Strength/risk:

- must be exact accepted statement text;
- backed by fact;
- may use cautious “можете”, but no certainty fragment.

### 7.6 Raw/internal leakage

Reject if any user-visible string contains:

```text
Transit_
Natal_
activation ID
fact ID
source/debug/evidence sentinel
snake_case theme or sphere key
```

Do not scan machine provenance fields as user copy.

### 7.7 Date/number integrity

Deterministic user-visible copy outside timing/technical labels comes from
canons, whose reviewed text has no digits.

Validator must:

1. recompute every timing/range/peak/valid-until/technique explanation;
2. require exact equality in deterministic mode;
3. reject numeric tokens in intro, horizon title/summary/plain explanation,
   grounded action/strength/risk, manifestation title/body/condition that are
   not part of exact canonical text;
4. allow selected house number only inside recomputed technical target label.

No arbitrary “18 июля” can be inserted into an action.

### 7.8 Minimum stable claim error codes

```text
duplicate_activation_evidence
public_cross_reference_invalid
intro_alignment_invalid
horizon_alignment_invalid
tone_alignment_invalid
timing_alignment_invalid
sphere_alignment_invalid
fact_provenance_invalid
fact_reused
manifestation_invalid
action_not_authorized
action_verdict_conflict
action_intent_conflict
technique_invalid
conditional_policy_invalid
unsupported_life_claim
forbidden_claim
internal_copy_leak
numeric_claim_not_grounded
```

## 8. Deterministic testkit and coverage corpus

### 8.1 Testkit

Создать `_horizon_guidance_testkit.py`.

It may import accepted test builders but must not modify them.

Required helpers:

```text
build_guidance_context(story, natal_case, verdict_case)
build_validated_guidance(...)
shifted_story_for(target_date, timezone, story)
build_coverage_cases()
build_worst_case_pipeline_input()
```

No production fixture/demo import, DB, network, auth, real user or wall clock.

### 8.2 Coverage YAML

Create strict test-only metadata file:

```text
schema_version: horizon-guidance-coverage.v1
profiles: exactly 5
target_dates: exactly 12
```

Profiles are synthetic chart-context descriptors, not raw people.

Exact five profile IDs/timezones/natal cases:

```text
synthetic-structure-moscow
  timezone: Europe/Moscow
  story: structure_boundaries_control
  natal_case: structure

synthetic-communication-utc
  timezone: UTC
  story: communication_learning_documents
  natal_case: communication

synthetic-relationships-berlin
  timezone: Europe/Berlin
  story: relationships_values_closeness
  natal_case: relationships

synthetic-empty-new-york
  timezone: America/New_York
  story: structure_boundaries_control
  natal_case: empty

synthetic-mixed-tbilisi
  timezone: Asia/Tbilisi
  story: communication_learning_documents
  natal_case: mixed
```

Exact 12 dates:

```text
2026-01-01
2026-02-28
2026-03-29
2026-04-15
2026-06-21
2026-07-08
2026-07-12
2026-09-22
2026-10-25
2026-12-31
2028-02-28
2028-02-29
```

No birth date/time/location/user ID/auth field. Natal cases are already
synthetic `NatalContextData` builders.

Total cases: 5 x 12 = 60.

### 8.3 Shifted selection inputs

For each case construct, not mutate after validation:

```text
long:
  annual_profection
  date precision
  Jan 1 .. Dec 31 of target local year
  no exact

medium:
  transit_to_natal
  instant precision
  target local noon - 90 days .. +90 days
  exact at target local noon

fast:
  transit_to_natal
  instant precision
  local target day start .. end
  exact at target local noon
```

Convert instant bounds to explicit UTC `Z` strings. ActivationLayer carries
exact target date, `12:00` and case timezone.

Keep accepted B2A story/scoring semantics:

- coherent story triple;
- stronger unrelated distractor;
- activation-linked scoring contributions;
- no threshold weakening.

Cycle explicit verdict cases:

```text
good
neutral
caution
avoid
mixed
```

Mixed means deterministic different verdicts across supplied selected spheres,
not an invented enum.

### 8.4 Coverage assertions

For every case:

1. B2A selection;
2. contract-ready peak check;
3. PersonalFactPack;
4. HorizonToneResult;
5. HorizonGuidanceContext;
6. deterministic block;
7. HorizonClaimValidator;
8. public `validate_horizons_against_evidence`;
9. JSON roundtrip through `TodayV2HorizonsBlock`;
10. repeated serialization exact.

Report exact counters:

```text
total=60
selected=<n>
contract_ready=<n>
guidance_valid=<n>
coverage=<percent>
selection_reasons=<counts>
contract_not_ready=<code counts>
guidance_failures=<code counts>
```

Gates:

```text
guidance_valid / total >= 0.95
selected triples with complete timing/provenance = 100%
selected anchor below accepted B2A impact threshold = 0
selected activation outside input layer = 0
unsupported claims = 0
```

Do not hide failed cases with skip/xfail.

## 9. Benchmark

Create `test_horizon_pipeline_benchmark.py`.

Measure:

```text
HorizonSelectionService
-> PersonalFactPackService
-> HorizonToneService
-> HorizonGuidanceService
-> HorizonClaimValidator
```

Excluded:

- fixture construction;
- sidecar;
- DB;
- network;
- LLM;
- stdout/logging;
- cold import.

Use synthetic 120-activation input that reaches exact 12x12x12 =
1728 selection combinations, then the selected triple through all B2B stages.

Protocol:

```text
3 warmups
20 measured runs
sort samples
p95 = ceil(0.95*n)-1
```

Assertions:

```text
every run returns validated block
combinations_evaluated == 1728
p95 < 100 ms
```

Print:

```text
horizon_pipeline_benchmark: p95=<ms> runs=20 combinations=1728
```

Do not weaken the accepted B2A benchmark.

## 10. Focused tests

### 10.1 Formatter tests

`test_horizon_guidance_formatter.py`:

- date precision Jan/May/July/December Russian cases;
- instant UTC;
- Europe/Moscow conversion and suffix;
- America/New_York DST boundary;
- Europe/Berlin DST boundary;
- leap day 2028-02-29;
- invalid timezone rejects;
- malformed/mixed raw timing rejects;
- state label exact;
- long/medium/fast valid-until templates exact;
- peak null only for long;
- medium/fast null peak rejects at service boundary;
- planet/node/angle/lot/house/sphere display;
- unknown transit source rejects;
- no `Transit_`/`Natal_`;
- manifestation split exact/failure cases.

### 10.2 Guidance tests

`test_horizon_guidance_service.py`:

- structure/communication/relationships intro headline/body all differ;
- exact long/medium/fast order and IDs;
- exact timing/raw timezone preservation;
- summary/plain explanation human-first;
- exact likely sphere order;
- one manifestation per sphere;
- conditions split without duplicated full sentence;
- action counts inside exact B1 ranges;
- action IDs/text/conditional/provenance exact canon;
- verdict `avoid` excludes incompatible experiment/communication templates;
- missing verdict does not become guessed neutral;
- strength/risk only exact matched facts;
- empty natal emits no strength/risk;
- fact not repeated across cards;
- profection explanation has definition/theme/range;
- transit explanation has named source/target/range;
- output public model valid;
- output cross-validates against synthetic evidence;
- verdict dict insertion order irrelevant;
- repeated build byte-identical;
- raw evidence/debug/PII sentinel absent;
- medium/fast missing exact rejects exact code;
- mismatched facts/tones/timezones reject exact code.

### 10.3 Claim validator mutation matrix

`test_horizon_claim_validator.py` mutates one independent field at a time:

- duplicate activation evidence ID;
- intro wrong theme/activation;
- horizon wrong anchor;
- changed tone;
- changed raw active_from/active_until/exact;
- changed range/peak/state/valid-until label;
- sphere outside selected anchor;
- unknown/reused fact ID;
- fact moved to unlinked horizon;
- profile fact ID inserted;
- manifestation condition removed;
- manifestation wrong sphere/provenance;
- action ID from wrong theme;
- avoid template placed in do;
- changed conditional flag;
- conditional text without prefix;
- safety class incompatible with supplied verdict;
- duplicate/cross-horizon action;
- invented technique;
- technique activation mismatch;
- forbidden certainty phrase;
- forbidden high-stakes imperative;
- invented employer/partner/debt/diagnosis/event assertion;
- raw `Transit_`/`Natal_`;
- raw activation/fact ID in text;
- snake_case theme key in text;
- invented numeric date in action;
- exception message contains no mutated human body/sentinel.

Use validated baseline + `model_copy(update=...)` where public model validators
would otherwise block construction, so claim-specific checks are actually hit.

### 10.4 Coverage and benchmark tests

No xfail/skip. Print exact evidence.

## 11. Privacy and determinism sentinels

Inject only synthetic sentinels:

```text
RAW_EVIDENCE_SENTINEL
RAW_DEBUG_SENTINEL
PROFILE_NAME_SENTINEL
PROFILE_CITY_SENTINEL
COORDINATE_SENTINEL
SESSION_SENTINEL
```

They must be absent from:

- block JSON;
- exception strings;
- pytest callback output.

Allowed public machine data:

- selected activation IDs;
- opaque fact IDs;
- canonical sphere/theme/technique keys;
- raw selected timing and timezone.

Forbidden public human copy:

- raw evidence/debug;
- natal sign/house/aspect/orb values as personal prose;
- name, gender, city, coordinates, birth date/time;
- unsupported real-life assertions.

## 12. Maintainability

Required:

- every new production file <=650 lines;
- every new test file <=700 lines;
- no production line >140 chars;
- no compressed multi-statement lines to hit limits;
- GRACE header/module contract/module map accurate;
- non-trivial public functions/classes have function contracts;
- no import cycle;
- no service imports from `SemanticV2Service`/`TodayService`;
- no frontend/generated contract import;
- no logger because B2B2 has no runtime integration/log event;
- `git diff --check` plus explicit whitespace scan for untracked new files.

## 13. Gates

Run focused:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest \
  tests/test_horizon_guidance_formatter.py \
  tests/test_horizon_guidance_service.py \
  tests/test_horizon_claim_validator.py \
  tests/test_horizon_coverage.py \
  tests/test_horizon_pipeline_benchmark.py -q
```

Run accepted upstream regression:

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

GRACE:

```bash
cd /opt/solarsage-astro
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_guidance.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/tests/_horizon_guidance_testkit.py \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py
```

Contracts must have zero public/generated diff:

```bash
pnpm contracts:check
```

Full API:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest tests -q
```

Expected pre-B5 baseline is exact same six IDs only:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

Any seventh failure is B2B2 regression and must be fixed.

Final:

```bash
cd /opt/solarsage-astro
git diff --check
test -z "$(git diff --cached --name-only)"
git status --short
```

Because new files are untracked, additionally scan exact allowlist for trailing
whitespace and line limits; `git diff --check` alone does not inspect them.

## 14. Callback

Return exactly:

```text
READY_STAGE_B2B2_DETERMINISTIC_GUIDANCE
changed_paths: <exact allowlist paths actually created>
context_alignment: PASS
timing_formatter: PASS <focused count>
dynamic_intros: PASS <three story headline/body summary>
actions: PASS <count/verdict matrix summary>
personal_claims: PASS <golden/absence/reuse summary>
technique_explanations: PASS
claim_mutations: <rejected>/<total> REJECT
unsupported_claims: ZERO
privacy_sentinels: PASS
coverage: <guidance_valid>/60 <percent>
coverage_selected: <n>/60
coverage_contract_ready: <n>/<selected>
coverage_failure_breakdown: <exact counts>
pipeline_benchmark: p95=<ms> runs=20 combinations=1728
focused_tests: <result>
upstream_regression: <result>
grace: PASS
size_limits: PASS <per-file lines>
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact failure IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
```

После callback остановиться. Не начинать исправления без architect review.
