# Stage B2B1 — architect review corrections R2

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD/origin: `cd27d1a8056eef92737e992c1b0998423331734b`
Parents: `64_...`, `65_...`
Статус: **NOT ACCEPTED — SMALL ARCHITECTURE R2, NO COMMIT/PUSH**

## 0. Accepted from R1

Не ломать уже закрытое:

```text
11/11 original architect invalid mutations reject
86 unique explicit templates
YAML anchors/merge keys zero
480/480 action tone/verdict combinations covered
loaded language policy owns conditional/forbidden copy rules
94 focused tests green
GRACE green
contracts no public diff
full API exact same six baseline failure IDs
```

## 1. Remaining reproduced blockers

### R2-F1 — production code duplicates canon content

`horizon_content_canon_types.py` contains:

```text
PATTERN_CATALOG_IDS
PATTERN_REQUIREMENT_SIGNATURES
```

The second constant duplicates every exact natal predicate from
`personal_patterns.ru.v1.yml`. Adding or changing an allowlisted rule therefore
requires a production Python edit, defeating the versioned-canon architecture.

Production schemas validate structure and self-consistency. Exact reviewed v1
content belongs to YAML plus golden tests.

### R2-F2 — incomplete fact packs are accepted

Independent probes currently return `ACCEPT` for:

```text
PersonalFactPack(selected ids, facts=())
pack with every medium sphere fact removed
pack with every fast sphere fact removed
```

A selected B2A triple always has at least one product sphere per horizon. B2B1
must reject a pack that loses one horizon's sphere provenance.

### R2-F3 — impossible tone provenance is accepted

Current schema accepts:

```text
sphere_component = 1.0
sphere_keys = ()
```

It also does not bind activation component magnitude to activation confidence
or an `opposing_material_evidence=True` flag to actually opposing components.

## 2. Exact allowlist

Only:

```text
grace/canon/personal_patterns.ru.v1.yml

apps/api/app/schemas/horizon_content_canon_types.py
apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/personal_fact_pack.py
apps/api/app/schemas/horizon_tone.py

apps/api/tests/test_personal_patterns_canon.py
apps/api/tests/test_personal_fact_pack_service.py
apps/api/tests/test_horizon_tone_service.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/66_STAGE_B2B1_ARCH_REVIEW_CORRECTIONS_R2_TZ.md
```

No other file. No commit/push. Do not enter B2B2.

## 3. Make pattern order self-describing

### 3.1 Remove production content duplication

Delete from production Python:

```text
PATTERN_CATALOG_IDS
PATTERN_REQUIREMENT_SIGNATURES
all validators that compare current YAML values to those Python constants
```

`horizon_content_canon_types.py` returns to structural types/helpers only.

### 3.2 Add `order` to the canon rule

Add required field:

```py
class PersonalPatternRule(...):
    order: int
    id: str
    ...
```

In YAML add exact orders `1..12` in the existing rule order:

```text
1  saturn_angular_dignified_structure
2  mercury_saturn_soft_structured_thinking
3  mars_saturn_soft_measured_effort
4  mercury_venus_soft_tactful_clarity
5  sun_jupiter_soft_broad_view
6  moon_mercury_soft_name_reaction
7  saturn_pluto_hard_control_under_pressure
8  mercury_saturn_hard_overchecking
9  mars_saturn_hard_increase_pressure
10 venus_saturn_hard_defensive_strictness
11 moon_pluto_hard_intensity_before_clarity
12 sun_uranus_hard_all_at_once
```

Schema validation:

- every `order >= 1`;
- orders unique;
- tuple order values exactly `1..len(patterns)`;
- reordering list without corresponding valid contiguous order fails;
- adding rule 13 later requires YAML/language/test change, not production code.

### 3.3 Golden content remains test-owned

In `test_personal_patterns_canon.py`, add one default-canon golden assertion over
the exact current reviewed catalog. It must compare, for every rule:

```text
order
id
kind
statement_key
theme_keys
sphere_keys
base_confidence
min_confidence
normalized predicate signature
```

The expected tuple/dict lives only in the test. This catches accidental content
drift while allowing an intentional reviewed canon update without changing
runtime schema code.

Update mutation tests:

- `reordered_pattern_catalog` remains rejected through `order`;
- duplicate/missing/non-contiguous/zero/negative order each rejected;
- a structurally valid known sign subset is no longer classified as schema-
  invalid solely because Python duplicated old content; exact default drift is
  caught by the golden test.

## 4. Require a complete selected sphere fact pack

Strengthen `PersonalFactPack.validate_pack`:

1. `facts` non-empty;
2. sphere facts exist for each of `long`, `medium`, `fast`;
3. at least one sphere fact per horizon;
4. sphere facts still precede personal facts and keep non-decreasing horizon
   order;
5. selected activation alignment remains exact;
6. removing all sphere facts for any one horizon rejects;
7. a pack containing only personal facts rejects.

Do not require a fixed sphere count because anchors legitimately expose 1–3
product spheres.

Add an activation ID scalar alias or equivalent validator with:

```text
strip-non-empty
max length 160
```

Apply it to selected and fact activation IDs. Do not restrict character set.

Tests:

```text
empty pack rejects
only-personal pack rejects
missing long sphere group rejects
missing medium sphere group rejects
missing fast sphere group rejects
161-char activation ID rejects
160-char activation ID remains valid when consistently aligned
```

## 5. Strengthen tone provenance invariants

In `HorizonToneAssessment.validate_assessment` require:

```text
abs(activation_component) <= activation_confidence
sphere_keys empty -> sphere_component == 0
sphere_component != 0 -> sphere_keys non-empty
opposing_material_evidence -> activation_component * sphere_component < 0
opposing_material_evidence -> tone == mixed
```

Do not require non-empty sphere keys when component is zero: explicit neutral
verdict rows legitimately produce `sphere_component=0` with provenance keys.

Activation ID also uses non-blank max-160 semantics.

Tests independently reject:

```text
component magnitude above confidence
nonzero sphere component without sphere keys
opposing flag with same-sign components
opposing flag with non-mixed tone
161-char activation ID
```

Existing service outputs must remain unchanged and green.

## 6. Maintainability cleanup

After deleting pattern duplication, format the affected files normally.

Required:

```text
no production line >140 chars in affected schema files
all production modules <=650 lines
all test files <=700 lines
GRACE contracts/maps accurate
```

Do not compress comprehensions to hit line limits; deletion should create ample
space.

## 7. Gates

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest \
  tests/test_personal_patterns_canon.py \
  tests/test_personal_fact_pack_service.py \
  tests/test_horizon_tone_service.py -q

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
all focused green
original 11/11 mutation probe still rejects
empty/missing-horizon fact packs reject
impossible tone provenance rejects
86 templates and 480/480 action coverage unchanged
contracts no public diff
full API exact same six baseline failure IDs only
index empty
no commit/push
```

## 8. Callback

```text
READY_STAGE_B2B1_R2_REVIEW
pattern_runtime_duplication: ZERO
pattern_order: SELF_DESCRIBING_1_TO_12
pattern_golden: PASS
fact_pack_completeness: PASS
tone_provenance: PASS
focused_tests: <result>
full_b2b1_focused: <result>
grace: PASS
size_limits: PASS <line counts>
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact failure IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
```

Stop and wait for architect review.
