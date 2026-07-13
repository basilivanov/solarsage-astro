# Stage B2B1 — architect review corrections R1

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD/origin: `cd27d1a8056eef92737e992c1b0998423331734b`
Implementation ТЗ: `64_STAGE_B2B1_CONTENT_CANONS_FACT_PACK_TONE_TZ.md`
Статус: **NOT ACCEPTED — CORRECTIONS REQUIRED, NO COMMIT/PUSH**

## 0. Architect verdict

Текущая реализация имеет хороший functional skeleton:

```text
23 focused tests pass
three canons load
three golden fact packs differ
privacy sentinels absent
tone happy paths work
contracts have no public diff
full API preserves the six accepted baseline failures
```

Но strictness и future B2B2 safety пока недостаточны. Запрещены commit/push и
переход в B2B2 до закрытия всех пунктов этого документа.

## 1. Reproduced architect findings

### R1-F1 — invalid canon/model mutations are accepted

Independent in-memory mutation probe produced:

```text
tone_infinite_thresholds       ACCEPT
extra_timing_template          ACCEPT
empty_template_tones           ACCEPT
empty_compatible_verdicts      ACCEPT
action_unknown_placeholder     ACCEPT
avoid_intent_inside_do         ACCEPT
base_confidence_below_min      ACCEPT
empty_pattern_links_bundle     ACCEPT
reordered_pattern_catalog      ACCEPT
blank_selected_activation_ids  ACCEPT
blank_fact_activation_id       ACCEPT
```

Every line above must become `REJECT` with an isolated regression test.

### R1-F2 — verdict compatibility is dead configuration

`SafetyClassRule.compatible_verdicts` is neither structurally validated nor
used to prove action availability. If every likely sphere has verdict `avoid`,
the current canon lacks contract-minimum safe `do` candidates for:

```text
structure_boundaries_control.medium       do=1 need=2
communication_learning_documents.medium  do=1 need=2
relationships_values_closeness.medium     do=1 need=2
resources_security.medium                 do=1 need=2
energy_body_pacing.medium                 do=1 need=2
home_belonging.medium                     do=0 need=2
inner_clarity_recovery.medium             do=1 need=2
direction_growth_meaning.medium           do=1 need=2
creativity_visibility.medium              do=1 need=2
creativity_visibility.fast                do=0 need=1
change_innovation.medium                  do=1 need=2
change_innovation.fast                    do=0 need=1
```

B2B2 would therefore have to violate `ConcreteAdvice` compatibility, violate
B1 action counts, or invent copy. All three are forbidden.

### R1-F3 — policy has two sources of truth

Forbidden copy fragments and conditional prefix are duplicated/hardcoded in
Python (`FORBIDDEN_COPY_FRAGMENTS`, literal `"Если "`) while the same policy is
owned by `horizon_language.ru.v1.yml`.

This violates the canon ownership rule. Runtime validation must consume the
loaded language policy; Python owns only structural mechanics.

### R1-F4 — action YAML inheritance obscures edits

`horizon_actions.ru.v1.yml` contains 73 YAML anchor/merge uses (`&...`, `<<:`).
Changing one anchor silently changes many template fields. For a safety canon,
every template must show its complete metadata explicitly.

### R1-F5 — tests prove happy paths, not the required boundary matrix

Current new tests are only 17 top-level tests (23 focused including existing
canon tests). Missing independent proof includes:

- exact supportive/tense threshold and ±1e-6 boundaries;
- each tone feature independently live, including `impact`;
- missing-verdict denominator;
- safety compatibility and per-tone/per-verdict action coverage;
- language timing key/placeholder closure;
- blank-copy rejection;
- complete pattern predicate/rule boundaries;
- fact order/ID/source/activation alignment;
- missing activation, timing mismatch, contribution kind/identity and
  non-finite scoring paths;
- exception privacy.

## 2. Exact correction allowlist

Allowed existing paths:

```text
grace/canon/horizon_language.ru.v1.yml
grace/canon/horizon_actions.ru.v1.yml
grace/canon/personal_patterns.ru.v1.yml

apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/personal_fact_pack.py
apps/api/app/schemas/horizon_tone.py

apps/api/app/services/canon_service.py
apps/api/app/services/horizon_content_canon_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/app/services/horizon_tone_service.py

apps/api/tests/_horizon_content_testkit.py
apps/api/tests/test_canon_service.py
apps/api/tests/test_horizon_content_canon_service.py
apps/api/tests/test_personal_fact_pack_service.py
apps/api/tests/test_horizon_tone_service.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/63_STAGE_B2B_DECOMPOSITION_AND_INVARIANTS.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/64_STAGE_B2B1_CONTENT_CANONS_FACT_PACK_TONE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/65_STAGE_B2B1_ARCH_REVIEW_CORRECTIONS_R1_TZ.md
```

Architect-approved new paths for this correction:

```text
apps/api/app/schemas/horizon_content_canon_types.py
apps/api/tests/test_horizon_language_canon.py
apps/api/tests/test_horizon_actions_canon.py
apps/api/tests/test_personal_patterns_canon.py
```

No other path. No public schema/barrel/contract/frontend/Today/Semantic/cache/
version/log/sidecar changes. No commit/push.

## 3. Split the content schema before adding validation

`horizon_content_canon.py` is already 646 lines. Do not compress new validation
into it.

Create `apps/api/app/schemas/horizon_content_canon_types.py` and move only
shared internal material there:

```text
closed Literal aliases/constants
HorizonContentCanonModel
regex/constants that are structural, not copy policy
_ensure_exact_keys
_ensure_unique_non_blank
_ensure_finite
_normalize_copy
_canonical_pair
```

`horizon_content_canon.py` imports and re-exports aliases currently consumed by
`personal_fact_pack.py`/services/tests, so callers do not need broad import
rewrites. Update GRACE contracts/maps accurately.

Limits after correction:

```text
every production Python module <=650 lines
every test module <=700 lines
no whitespace compression
```

## 4. Language canon strict closure

### 4.1 Non-blank reviewed copy

Reject strings that become blank after `.strip()` for all user-facing fields:

```text
horizon labels/headings
tone labels
timing state labels/templates
technique label/definition/template
theme label/headline/intro/title/plain explanation
sphere label/title/body
sphere-fact labels
personal statement text
conditional policy prefixes/fragments
```

Do not mutate preserved wire/canon copy while validating.

### 4.2 Exact timing template keys and placeholders

`timing_templates` keys must equal exactly:

```text
range peak valid_until long_valid_until fast_eases
```

Required placeholder sets are exact:

```text
range            -> active_from, active_until
peak             -> exact_at
valid_until      -> active_until
long_valid_until -> active_until
fast_eases       -> active_until
```

No extra/missing placeholder. Reject unbalanced/unknown braces in every
language template and every action body.

Technique templates may use only the existing allowed vocabulary, and all
literal braces must be valid placeholders.

### 4.3 Finite tone thresholds

Validate:

```text
supportive_min finite in (0, 1]
tense_max finite in [-1, 0)
mixed_opposing_min finite in [0, 1]
```

`inf`, `-inf`, `NaN`, out-of-range and sign inversion must fail.

### 4.4 Canon-owned copy policy

Remove the Python duplicate `FORBIDDEN_COPY_FRAGMENTS` and all hardcoded
conditional-prefix decisions from template-local validation.

At `HorizonContentCanonBundle` cross-validation:

1. build forbidden fragments from
   `language.conditional_policy.forbidden_certainty_fragments +
   forbidden_high_stakes_fragments`;
2. scan all user-facing language/action copy case-insensitively after whitespace
   normalization;
3. exclude only the policy lists themselves from this scan;
4. conditional action/sphere copy must begin with one of the loaded
   `required_prefixes`;
5. action bodies may contain no placeholders/braces.

Python may validate policy lists are non-empty, unique and non-blank; it may not
repeat their Russian contents.

## 5. Action canon structural and safety validation

### 5.1 Expand every template explicitly

Remove all YAML anchors and merge keys from
`grace/canon/horizon_actions.ru.v1.yml`.

Every template block explicitly contains exactly:

```text
id
text
intent
safety_class
conditional
tones
sphere_keys
```

Add a raw-file style test proving no YAML anchor/alias/merge token remains.

### 5.2 Validate safety classes

For every safety class:

- `allowed_intents` non-empty, unique;
- `compatible_verdicts` non-empty, unique, canonical order
  `good, neutral, caution, avoid` subsequence;
- every template intent belongs to its safety class;
- every template has non-empty unique canonical tones;
- every template has non-empty sphere keys preserving owning theme order.

Do not hardcode the exact Russian policy or verdict lists in services. The
validated canon remains source of truth.

### 5.3 Enforce list semantics

Inside each horizon:

```text
do templates may use only PositiveActionIntent
avoid templates may use only AvoidActionIntent
```

A guardrail intent inside `do`, or a positive intent inside `avoid`, must fail
even if the safety class accepts it.

### 5.4 Coverage across tone and verdict

At canon load, for every:

```text
theme x horizon x tone x verdict
```

filter templates by:

```text
tone in template.tones
verdict in safety_class.compatible_verdicts
```

Then require:

```text
long:   do >=1, avoid >=1
medium: do >=2, avoid >=1
fast:   do >=1, avoid >=1
```

This is a bounded matrix: `10 * 3 * 4 * 4 = 480` combinations. Validate at
startup; no runtime fallback may invent copy.

### 5.5 Add exact safe fallback candidates

Keep all existing 73 templates unchanged. Add the following 13 templates
exactly. All have:

```text
safety_class: reflection
conditional: false
tones: [supportive, neutral, tense, mixed]
sphere_keys: exact owning theme_spheres list
```

#### Medium fallbacks

| theme | id | intent | exact text |
|---|---|---|---|
| `structure_boundaries_control` | `structure.medium.fallback_working_signs` | reflect | Составьте короткий список признаков, по которым поймёте, что правило или граница действительно работает. |
| `communication_learning_documents` | `communication.medium.fallback_fact_question_draft` | reflect | Запишите отдельно факт, вопрос и формулировку, которую пока не стоит отправлять. |
| `relationships_values_closeness` | `relationships.medium.fallback_known_unknown_boundary` | reflect | Запишите, какой факт вы знаете, чего пока не знаете и какую границу хотите прояснить. |
| `resources_security` | `resources.medium.fallback_constraint_check` | clarify | Сверьте решение с одним заранее выбранным ограничением: сроком, суммой или запасом. |
| `energy_body_pacing` | `energy.medium.fallback_load_marker` | record_observation | Зафиксируйте текущий объём нагрузки и один признак, по которому заметите лишнюю интенсивность. |
| `home_belonging` | `home.medium.fallback_rule_cost` | record_observation | Запишите одно бытовое правило, которое сейчас создаёт больше напряжения, чем пользы. |
| `home_belonging` | `home.medium.fallback_fact_not_generalization` | clarify | Отделите конкретное неудобство от общего вывода о доме или близких. |
| `inner_clarity_recovery` | `clarity.medium.fallback_open_question` | reflect | Назовите один вопрос, который можно оставить открытым до появления новых фактов. |
| `direction_growth_meaning` | `direction.medium.fallback_pro_con_unknown` | clarify | Запишите один аргумент за, один против и один факт, которого пока не хватает. |
| `creativity_visibility` | `creativity.medium.fallback_one_element` | record_observation | Запишите один элемент результата, который уже можно оценить отдельно от общего впечатления. |
| `change_innovation` | `change.medium.fallback_problem_first` | clarify | Сформулируйте, какую проблему должно решить изменение, прежде чем выбирать новый способ. |

#### Fast fallbacks

| theme | id | intent | exact text |
|---|---|---|---|
| `creativity_visibility` | `creativity.fast.fallback_feedback_fact` | record_observation | Запишите одну конкретную деталь обратной связи и отложите общую оценку результата. |
| `change_innovation` | `change.fast.fallback_record_small_change` | record_observation | Запишите самое маленькое изменение, которое можно проверить позже без разрушения текущей системы. |

After additions:

```text
template count: 86
unique IDs: 86
unique normalized texts: 86
coverage deficiencies for all 480 tone/verdict combinations: ZERO
```

Do not alter safety compatibility to make unsafe actions pass; availability is
fixed by these reviewed reflection candidates.

## 6. Personal pattern canon closure

Validate for every rule:

- `theme_keys`, `sphere_keys`, `requirements` non-empty;
- ordered lists unique;
- `base_confidence` and `min_confidence` finite in `0..1`;
- `base_confidence >= min_confidence`;
- predicate value lists non-empty/unique;
- exact known planet/sign/house/aspect/orb rules from 64;
- duplicate normalized predicates rejected;
- pattern catalog ID order exactly equals the 12-rule order in section 8.3 of
  64;
- statement reference/kind remains one-to-one.

Reordering the catalog is a canon change and must fail current v1 tests rather
than silently alter deterministic fact ordering.

## 7. PersonalFact / PersonalFactPack strengthening

### 7.1 Non-blank opaque machine references

Reject blank/whitespace-only values in:

```text
selected_activation_ids
PersonalFact activation_ids
natal_source_ids
profile_source_ids
theme keys/source ids where represented as strings
```

Keep raw activation ID character set open; require only non-blank and bounded
length, because upstream activation IDs are not B2B-owned.

### 7.2 Kind/ID/statement consistency

For sphere fact require exactly:

```text
id == pf:v1:sphere:<horizon>:<sphere>
statement_key == sphere.active.<sphere>
activation ID == selected activation ID for that horizon
theme_keys non-empty
```

For strength/risk require:

```text
id prefix == pf:v1:<kind>:
statement_key prefix == <kind>.
horizon_ids and activation_ids have equal length
activation IDs equal the selected-ID subsequence for horizon_ids
natal source IDs match only generic v1 structural forms
```

### 7.3 Pack order

Validate:

- all sphere facts precede personal facts;
- sphere horizon groups are non-decreasing long -> medium -> fast;
- within one horizon no duplicate sphere fact;
- personal facts keep unique IDs and canonical horizon subsequences;
- any fact referencing a selected activation uses the activation belonging to
  the same declared horizon.

Service still emits sphere facts in accepted anchor product-sphere order and
personal facts in canon rule order. Add deterministic order tests; do not sort
human/semantic priority away.

## 8. PersonalFactPackService integrity

Keep the current allowed data sources. Add/verify:

1. selected evidence timing mismatch test (`active_from`, `exact_at` and
   `active_until` independently);
2. missing selected activation test;
3. selected activation duplicate/inactive/identity mismatch tests;
4. contribution must be:

```text
source == activation
source_id == selected anchor id
contribution.sphere == owning technical sphere
owning SphereScoreV2.key == technical sphere dict key
finite non-zero amount
```

5. base/convergence/unrelated activation contributions alone cannot ground a
   sphere fact;
6. non-finite used contribution fails without leaking evidence/value;
7. negative and NaN natal orb independently fail;
8. irrelevant valid natal aspects remain deterministic;
9. multiple matching aspects choose smallest orb independent of input order;
10. debug/evidence mutations cannot change any fact/source ID;
11. exception text contains no raw evidence/debug/natal sentinels.

Do not start using dominants/top_signals/balances/special points.

## 9. Tone schema/service proof

No algorithm change is required unless tests reveal one. Add independent tests
for:

```text
supportive net == threshold       -> supportive
supportive net threshold - 1e-6  -> neutral
tense net == threshold            -> tense
tense net threshold + 1e-6       -> neutral
explicit mixed precedence
material opposition both directions
opposition below threshold
missing sphere verdict omitted from denominator
only anchor sphere keys used
reversed mapping insertion order byte-identical
unknown sphere and unknown verdict independently rejected
strength feature independently changes confidence by expected amount
contribution feature independently changes confidence by expected amount
convergence feature independently changes confidence by expected amount
impact independently changes confidence by expected amount
Russian label/copy mutation cannot change output
all output schema impossible states rejected
```

Use validated explicit canon copies/monkeypatch, not `model_copy(update=...)`
when the test intends to prove canon validation. `model_copy` bypasses Pydantic
validation.

## 10. Required test decomposition

Keep loader/cache/error tests in:

```text
test_horizon_content_canon_service.py
```

Move/add isolated validation tests to:

```text
test_horizon_language_canon.py
test_horizon_actions_canon.py
test_personal_patterns_canon.py
```

Each invalid mutation gets its own test or one parametrized test with one field
mutation per case and a descriptive case ID. Do not place unrelated mutations
inside a single broad test body.

Minimum required canon cases in addition to sections 4–6:

- wrong schema/version/locale independently;
- extra key at language/action/pattern/template/predicate levels;
- missing/extra technique/theme/sphere/tone/state/horizon key;
- unreadable file via monkeypatched `Path.open`/OSError;
- non-mapping YAML;
- validation error hides raw copy sentinel;
- duplicate ID/text;
- tone and sphere order;
- safety intent mismatch;
- every fallback coverage boundary;
- statement missing/kind mismatch/unreferenced/duplicate referenced;
- all three predicate types valid and invalid boundaries.

## 11. Independent mutation proof helper

Add tests equivalent to the architect probe so these all reject:

```text
infinite tone thresholds
extra timing key
empty template tones
empty compatible verdicts
action placeholder
avoid intent in do
base confidence below min
empty pattern links
reordered pattern catalog
blank selected activation ID
blank fact activation ID
```

No production diagnostic helper is needed; tests are sufficient.

## 12. Gates

Run:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_content_canon_service.py \
  tests/test_horizon_language_canon.py \
  tests/test_horizon_actions_canon.py \
  tests/test_personal_patterns_canon.py \
  tests/test_personal_fact_pack_service.py \
  tests/test_horizon_tone_service.py -q

cd /opt/solarsage-astro
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_content_canon_types.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/personal_fact_pack.py \
  apps/api/app/schemas/horizon_tone.py \
  apps/api/app/services/horizon_content_canon_service.py \
  apps/api/app/services/personal_fact_pack_service.py \
  apps/api/app/services/horizon_tone_service.py \
  apps/api/tests/_horizon_content_testkit.py \
  apps/api/tests/test_horizon_content_canon_service.py \
  apps/api/tests/test_horizon_language_canon.py \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_personal_patterns_canon.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py

pnpm contracts:check
git diff --check

cd apps/api
.venv/bin/python -m pytest tests -q
```

Expected:

```text
all focused correction tests green
all 11 architect invalid mutations reject
action template count 86
480-combination action coverage deficiencies zero
all modules/tests within size limits
contracts PASS with no public/generated diff
full API exact same six baseline failure node IDs only
index empty
commit/push absent
```

## 13. Callback

Return exactly:

```text
READY_STAGE_B2B1_R1_REVIEW
changed_paths: <exact list>
schema_split: PASS <line counts>
architect_mutations: 11/11 REJECT
action_templates: 86 UNIQUE
action_coverage: PASS 480/480
yaml_anchors: ZERO
canon_focused: <count passed>
fact_pack_focused: <count passed>
tone_focused: <count passed>
privacy_errors: PASS
grace: PASS
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact failure IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
```

Stop. Do not proceed to B2B2.
