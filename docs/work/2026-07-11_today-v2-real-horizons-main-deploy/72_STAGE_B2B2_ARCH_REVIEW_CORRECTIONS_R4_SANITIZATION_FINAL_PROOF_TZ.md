# Stage B2B2 — architect review corrections R4: sanitization and final proof

Дата: 2026-07-12  
Ветка: preview/solarsage-v2-human-first-navigator-ux  
Accepted HEAD/origin: c47863a0c4b2be2242c276bb610a262b4b91a737  
Parent documents: 68–71  
Статус: **NOT ACCEPTED — NARROW R4, NO COMMIT/PUSH**

## 0. Scope

R3 functional work is largely correct and must be preserved.

Independently confirmed after R3:

~~~text
GRACE:                   PASS 12/12
focused:                 141 passed, zero B2B2 warnings
upstream:                82 passed
strict YAML mutations:   18/18 rejected
coverage:                60/60, roundtrip/byte identity present
shifted timing:          exact long / medium ±90 local days / fast local day
R2 residual probes:      18/18 rejected
R3 additional probes:    10/10 rejected
actual fact ID in copy:  rejected
benchmark assertions:    real 120, 40/40/40, 12/12/12, 23/23 at 1728
benchmark isolated x5:   p95 21.35–30.48 ms
~~~

Do not redesign or reopen those areas.

This is a narrow final correction for:

1. raw ID/key leakage in exception strings;
2. missing executed proof for action-intent gates;
3. three remaining mutation-completeness gaps.

No subagents. No new files. No commit/push. Exact B2B2 allowlist from R3 only.
After callback, stop.

## 1. Blocker R4-F1 — raw IDs still leak from validator/policy errors

Architect direct probes on current R3:

~~~text
manifestation.id = RAW_DEBUG_SENTINEL
-> manifestation_invalid | mismatch RAW_DEBUG_SENTINEL

action.id = PROFILE_NAME_SENTINEL
-> action_not_authorized | id PROFILE_NAME_SENTINEL not in canon bucket
~~~

Therefore callback:

~~~text
sanitized_errors: PASS ... zero raw values
~~~

is false.

Additional current leakage paths include:

- fact_reused passes raw fact ID to _fail;
- collect_user_visible_strings builds paths from item.id, manifestation.id,
  action.id and technique key;
- action authorization errors interpolate action ID, theme key, safety class
  and intent;
- forbidden-intent-pair error prints both action IDs and both intent names;
- manifestation mismatch prints public manifestation ID;
- unsupported/forbidden policy errors can print a dynamic path containing a
  mutated public ID.

### Required production correction

Error details may contain only:

- closed error code;
- stable structural path using numeric indices;
- closed horizon enum long/medium/fast;
- safe field name.

Never include:

- action/manifestation/fact/activation/public item ID;
- theme/sphere/technique/entity key;
- safety-class or intent name;
- source/user/sentinel value;
- raw body or upstream exception text.

Refactor collect_user_visible_strings to use stable paths:

~~~text
intro.headline
items[0].title
items[0].timing.range_label
items[0].manifestations[0].body
items[0].strength.text
items[0].actions.heading
items[0].actions.do[0].text
items[0].technique_explanations[0].why_it_matters_now
~~~

Do not build structural paths from public IDs.

Refactor check_action_authorization loops with enumerate and pass only safe
index paths to _fail. Logic may use IDs internally for lookup, but exception
text must not.

Refactor validator:

- fact_reused -> safe items[index].strength/risk path, never fid;
- manifestation mismatch -> safe horizon/index path, never m.id;
- all remaining dynamic raw details -> safe structural path.

Audit every HorizonGuidanceError and HorizonClaimValidationError creation in the
13-file B2B2 allowlist again.

## 2. Blocker R4-F2 — action-intent callback has no executed test proof

Current production code contains action_intent_conflict branches, but no test in
the B2B2 test collection references action_intent_conflict or mutates
forbidden_intents / forbidden_intent_pairs.

Architect independently forced both branches by copying the loaded canon:

~~~text
forbidden_intents += reflect
-> action_intent_conflict
-> currently leaks: forbidden intent reflect for structure.long.inventory

forbidden_intent_pairs += (reflect, postpone_major_decision)
-> action_intent_conflict
-> currently leaks both canonical action IDs and intent names
~~~

### Required tests

Add two deterministic tests using a copied canon bundle injected into a local
HorizonClaimValidator instance:

1. selected action intent is added to forbidden_intents;
2. an actually present do/avoid intent pair is added to forbidden_intent_pairs.

For each:

- validator must reject exact action_intent_conflict;
- exception must contain no action ID;
- exception must contain no intent name;
- exception must contain no sentinel/raw canon value;
- original cached canon must not be mutated.

These tests are required evidence for policy_code_matrix.

## 3. Blocker R4-F3 — final mutation-completeness gaps

### 3.1 Actual fact ID leakage test

Current embedded_fact_id mutation uses literal fake text:

~~~text
fact_id_12345
~~~

Replace it with an actual fact ID from baseline context.fact_pack.facts.
Assert exact internal_copy_leak.

### 3.2 Horizon timing state

Current matrix tests state_label and nested technique timing state, but not the
public horizon timing state field itself.

Add a non-noop mutation of item.timing.state and require exact
timing_alignment_invalid.

### 3.3 Lower-ranked otherwise-valid fact

R1 explicitly requires proof that validator rejects an otherwise-valid
lower-ranked fact.

Build a copied context fact pack containing:

- original top-ranked strength fact;
- one additional eligible strength fact with same horizon/theme/activation/
  sphere compatibility and valid canonical statement;
- lower confidence and a distinct synthetic ID.

Build the valid block from that copied context; top-ranked fact must be selected.
Then mutate the public strength to a fully well-formed item derived from the
lower-ranked fact:

- valid canonical text;
- valid kind;
- valid activation/sphere provenance;
- its own valid natal fact ID;
- correct public ID shape for that lower fact.

Validator must reject exact fact_provenance_invalid because deterministic
ranking expects the original top fact, not because text/provenance is malformed.

## 4. Required sanitization matrix

Add explicit rejection/no-leak tests for at least:

~~~text
manifestation ID sentinel
action ID sentinel
public horizon item ID sentinel plus unsupported body
actual reused fact ID
forbidden selected intent
forbidden do/avoid intent pair
formatter unknown entity/source/target sentinels
service unknown theme/sphere/activation sentinels
builder unknown statement/theme/technique sentinels
public cross-reference mismatch with raw ID
~~~

For every case:

~~~text
exception is mandatory
exact code is asserted
sentinel/raw ID absent from str(exc)
raw intent/safety/theme/action values absent from str(exc)
~~~

No try/except test without an else-fail branch. Prefer pytest.raises and inspect
exc_info.value.

## 5. Test count and limits

Current mutation matrix has 87 invalid cases.

After adding:

- horizon timing state;
- lower-ranked fact;
- forbidden selected intent;
- forbidden intent pair;

required claim/policy mutation count is at least 91, all rejected by intended
code.

The actual-fact-ID case replaces the fake one and does not need to increase
count.

Keep limits:

~~~text
validator <=400
guidance service <=350
production file <=650
test file <=700
production line <=140
GRACE PASS 12/12
zero B2B2 deprecation warnings
~~~

test_horizon_guidance_service.py is currently 691 lines. Do not exceed 700.
Prefer placing compact validator/policy tests in test_horizon_claim_validator.py
(currently 327 lines), or refactor without creating a new file.

## 6. Mandatory gates

Focused:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q
~~~

Evidence:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_claim_validator.py -q -s

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_coverage.py -q -s

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q -s
~~~

Then:

~~~bash
python3 scripts/grace_lint.py <exact 12 Python files from R3>
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py \
  apps/api/tests/test_horizon_selection_benchmark.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py -q
pnpm contracts:check
apps/api/.venv/bin/python -m pytest apps/api/tests -q
git diff --check
git diff --cached --quiet
~~~

Full API may contain only the exact six known baseline failures.

Also run explicit untracked whitespace, line-length, line-count and exact
allowlist scans.

## 7. Callback

Return exactly:

~~~text
READY_STAGE_B2B2_R4_REVIEW
changed_paths: <exact code/test/fixture paths>
accepted_head_unchanged: c47863a0c4b2be2242c276bb610a262b4b91a737
production_split: PASS <counts>
test_sizes: PASS <counts>
grace: PASS 12/12 ZERO_VIOLATIONS
focused_tests: <result, zero B2B2 warnings>
claim_mutations: <rejected>/<total>=91 REJECT_BY_INTENDED_CODE
actual_fact_id_leakage: REJECT internal_copy_leak
horizon_timing_state: REJECT timing_alignment_invalid
lower_ranked_fact: REJECT fact_provenance_invalid
action_forbidden_intent: REJECT action_intent_conflict
action_forbidden_pair: REJECT action_intent_conflict
sanitized_errors: PASS <case count> ZERO_RAW_IDS_ZERO_SENTINELS
residual_fail_open_probes: 18/18 REJECT
additional_r3_fail_open_probes: 10/10 REJECT
strict_yaml_mutations: 18/18 REJECT
shifted_story_regressions: 4/4 PASS
coverage: 60/60 100.0%
coverage_roundtrip_byte_identity: 60/60 PASS
pipeline_benchmark: p95=<ms> runs=20 combinations=1728 all_runs=23/23
upstream_regression: 82 PASS
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact six baseline IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
~~~

Do not return READY until every line is backed by an executed gate. Stop after
callback.
