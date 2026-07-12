# Stage B2B2 — R5 new-coder continuation: close the remaining sanitization boundary

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Accepted HEAD/origin: `c47863a0c4b2be2242c276bb610a262b4b91a737`  
Parent documents: `68`–`72` in this directory  
Статус: **NOT ACCEPTED — CONTINUE CURRENT UNCOMMITTED B2B2 WIP, NO COMMIT/PUSH**

## 0. Исполнитель и режим работы

Это handoff новому кодеру после восстановления OpenCode-сессии.

Ты — единственный coding executor. Всю реализацию и тесты выполняешь сам.

- Не запускай subagents, teams, delegation или параллельных кодеров.
- Не переключай ветку и не создавай новую ветку.
- Не делай `git add`, commit, amend, rebase, merge, push или deploy.
- Не удаляй и не откатывай текущий незакоммиченный B2B2 WIP.
- Не начинай Stage B2B3/B3/frontend wiring/main deploy.
- После exact callback остановись.

Сначала полностью прочитай документы `68`, `69`, `70`, `71`, `72`, затем этот
документ. Текущий код уже содержит большую часть принятой архитектуры; не
переписывай её заново.

## 1. Зафиксированное состояние, которое нужно сохранить

Architect independently confirmed before this R5 pass:

~~~text
branch/head:             preview/... @ c47863a0c4b2be2242c276bb610a262b4b91a737
index:                   empty
focused after R4:        149 passed
GRACE:                   PASS 12/12
upstream regression:     82 passed
coverage:                60/60, 100.0%
strict YAML mutations:   18/18 rejected
R2 residual probes:      18/18 rejected
R3 additional probes:    10/10 rejected
shifted timing:          exact long / medium +/-90 local days / fast local day
benchmark isolated x5:   p95 21.35-30.48 ms
~~~

The one p95 failure around 122 ms was produced only when the benchmark was run
concurrently with other CPU-heavy pytest processes. Benchmark gates in this TZ
must be run isolated/sequentially.

Current B2B2 implementation/test files are intentionally untracked. Preserve
them. Current R4 work includes the lower-ranked fact, action-intent, timing-state,
coverage, strict-YAML and sanitization tests. Extend/fix those tests; do not
replace their accepted behavior.

Known pre-B2B2 full-API baseline failures are exactly:

~~~text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
~~~

No new failure is allowed.

## 2. Exact allowed paths

Production:

~~~text
apps/api/app/schemas/horizon_guidance.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
~~~

Tests/fixtures already belonging to B2B2:

~~~text
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/fixtures/horizon_guidance_coverage.v1.yml
apps/api/tests/test_horizon_guidance_formatter.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_pipeline_benchmark.py
~~~

Do not create another production or test file. Do not touch anything outside
this exact list. In particular, never touch or stage:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

The architect owns this TZ file; do not edit it.

## 3. Why R4 is not accepted yet

R4 fixed the common validator order, so its end-to-end sentinel examples pass.
However, direct public policy/formatter/builder branches can still serialize raw
IDs, keys, or values in an exception. The error boundary must be safe regardless
of which check happens to run first.

Current independently observed unsafe constructions include:

~~~text
horizon_claim_policy.py:
  manifestation {mani.id} missing condition
  manifestation {mani.id} condition prefix
  action {act_item.id} conditional without prefix
  snake_case key '{cleaned}' in {identifier}

check_numeric_integrity():
  identifiers are built from item.id, action.id, grounded.id,
  manifestation.id and technique key and then included in the error

horizon_guidance_formatter.py:
  precision={precision}
  target_type={target_type}

horizon_guidance_builders.py:
  technique remaining: {raw unresolved placeholder names}

horizon_guidance.py error types:
  optional item_id is appended verbatim as id={item_id}
~~~

This violates the already agreed R4 invariant: error output may contain only a
closed code and stable structural path/index. Validator ordering is not a
security/privacy boundary.

## 4. Required production corrections

### 4.1 One non-negotiable exception contract

For every `HorizonGuidanceError` and `HorizonClaimValidationError` raised by the
B2B2 files:

Allowed in `str(exc)`:

- closed error code;
- stable structural path using field names and numeric indices;
- closed horizon enum `long|medium|fast` when genuinely useful.

Forbidden in `str(exc)` and any retained public error detail:

- action, manifestation, fact, activation, horizon-item or evidence ID;
- theme, sphere, technique, entity, target or source key;
- intent or safety-class name;
- raw timing precision/timezone/value;
- unresolved placeholder name;
- text fragment copied from the public body;
- profile/debug/session/sentinel value.

Do not solve this with string replacement against the six known sentinels.
Construct only safe paths at the point the error is created.

### 4.2 Conditional policy: enumerate and use structural paths

In `check_conditional_and_unsupported_policy` enumerate horizons,
manifestations, `actions.do`, and `actions.avoid` separately.

Expected path shapes:

~~~text
items[0].manifestations[0].condition
items[0].actions.do[0].text
items[0].actions.avoid[0].text
~~~

Never interpolate `mani.id` or `act_item.id`.

Add direct policy regression tests that bypass validator ordering:

1. manifestation ID is `RAW_DEBUG_SENTINEL`, condition is missing/invalid;
2. action ID is `PROFILE_NAME_SENTINEL`, action is conditional, text lacks a
   required prefix.

For both, call the policy function directly, assert exact
`conditional_policy_invalid`, and assert the ID and mutated body are absent from
`str(exc)`.

### 4.3 Numeric integrity: no public IDs as diagnostic identifiers

Refactor `check_numeric_integrity` to collect non-timing strings with numeric
index paths, just as `collect_user_visible_strings` now does.

Required path examples:

~~~text
items[0].title
items[0].summary
items[0].actions.do[0].text
items[0].actions.avoid[0].text
items[0].strength.text
items[0].risk.text
items[0].manifestations[0].title
items[0].manifestations[0].body
items[0].manifestations[0].condition
items[0].technique_explanations[0].label
items[0].technique_explanations[0].what_it_is
~~~

Do not use `item.id`, grounded/action/manifestation IDs or `t.technique` in an
error identifier.

Add direct numeric-policy regressions using a unique raw ID/key plus
non-canonical numeric text. Cover at least:

- public horizon item ID;
- action ID;
- manifestation ID;
- technique key.

Each must reject exact `numeric_claim_not_grounded`; the raw ID/key and mutated
copy must be absent from the exception.

### 4.4 Raw-copy scan: do not echo the detected snake_case token

`check_no_raw_leakage` currently includes `cleaned` in the exception detail.
Use only the structural field path, for example
`items[0].summary.snake_case`.

Add a direct regression with a unique snake-case token that is not one of the
hard-coded sentinels. Assert exact `internal_copy_leak` and absence of the raw
token from `str(exc)`.

### 4.5 Formatter errors: raw enum-like input is still raw input

Change unsafe details:

~~~text
precision={precision}       -> timing.precision
target_type={target_type}   -> target_type
~~~

Use `model_copy(update=...)` in the test if Pydantic normally prevents the
invalid precision from being constructed. Test a unique precision sentinel and
a unique target-type sentinel. Assert exact codes and zero sentinel leakage.

Do not weaken valid timing/entity formatting.

### 4.6 Builder unresolved placeholders

`build_technique_explanation` must not list unresolved placeholder names in the
error. Return only a stable safe path such as
`technique.why_it_matters_now`.

Using a deep-copied canon, inject a unique unresolved placeholder into the
selected technique template and execute the real builder path. Assert exact
`unresolved_placeholder` and absence of the placeholder/key in the exception.
The original cached canon must remain unchanged.

### 4.7 Enforce safety in the two typed error classes

`HorizonGuidanceError` and `HorizonClaimValidationError` currently accept and
append arbitrary `item_id` verbatim. That makes every caller one argument away
from violating the privacy invariant.

Keep constructor compatibility if useful, but the error class must neither
stringify nor retain a caller-supplied raw `item_id`. Prefer eliminating the
unsafe field entirely if no B2B2 caller uses it. Add a direct regression for
both classes using `RAW_ITEM_ID_SENTINEL` and assert it is absent from
`str(exc)`, `repr(exc)`, and retained public error fields.

Do not alter the separate established error contract in
`apps/api/app/schemas/today_horizons.py`; that file is outside this R5 scope.

### 4.8 Final manual audit

Audit every error creation in the six production files. The examples above are
known findings, not an exhaustive waiver. If another error detail contains a
runtime ID/key/value, replace it with a stable path and add the smallest direct
regression.

Closed values derived entirely from trusted code, such as the selected
`long|medium|fast` enum, are acceptable. User/context/canon values are not.

Do not change user-visible successful output while fixing error diagnostics.

## 5. Preserve all R4 functional guarantees

The correction must not weaken or remove:

- deterministic three-horizon construction;
- exact timing/date/timezone behavior;
- claim ranking and non-reuse;
- exact manifestation/action/technique reconstruction;
- action verdict and forbidden-intent checks;
- unsupported-life and forbidden-claim scans;
- actual embedded fact-ID rejection;
- public cross-reference validation;
- strict YAML mutation rejection;
- 60/60 coverage and byte-identical second build;
- real 120-combination/1728-configuration benchmark assertions.

Do not turn exact comparisons into subset/contains checks.

## 6. Size, GRACE and code-quality limits

After changes:

~~~text
horizon_claim_validator.py       <= 400 lines
horizon_guidance_service.py      <= 350 lines
each production file             <= 650 lines
each test file                   <= 700 lines
production line length           <= 140 characters
GRACE                             PASS 12/12
B2B2 deprecation warnings        zero
~~~

Keep/update `AI_HEADER`, module contract/map, function contracts and semantic
blocks for every materially changed function. Do not split into new files merely
to satisfy a count.

## 7. Mandatory tests and gates

Run focused tests first:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q
~~~

Run the new sanitization tests directly with `-vv` and report their exact names.
Run coverage evidence and benchmark separately:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_coverage.py -q -s

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q -s
~~~

The benchmark command must be isolated: no other pytest/contracts process in
parallel. Run it three sequential times; every run must pass p95 `<100 ms`.

Then run:

~~~bash
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

Full API may contain only the exact six known baseline failures from section 1.

Also execute and report:

1. exact `git status --short --branch`;
2. exact changed-path allowlist diff;
3. untracked whitespace scan, because ordinary `git diff --check` does not
   inspect untracked files;
4. production/test line counts and production `>140` line scan;
5. grep/manual audit proving no error construction interpolates runtime raw
   IDs/keys/values;
6. index remains empty and accepted HEAD/origin remain unchanged.

## 8. Exact callback

Return exactly this structure, with real executed numbers/results:

~~~text
READY_STAGE_B2B2_R5_REVIEW
changed_paths: <exact code/test/fixture paths>
accepted_head_unchanged: c47863a0c4b2be2242c276bb610a262b4b91a737
production_split: PASS <counts>
test_sizes: PASS <counts>
grace: PASS 12/12 ZERO_VIOLATIONS
focused_tests: <result, zero B2B2 warnings>
r5_direct_sanitization_tests: <passed>/<total> <exact test names>
conditional_policy_direct: PASS ZERO_RAW_IDS_ZERO_COPY
numeric_policy_direct: PASS ZERO_RAW_IDS_ZERO_KEYS_ZERO_COPY
snake_case_direct: PASS ZERO_RAW_TOKEN
formatter_raw_values: PASS ZERO_RAW_VALUES
builder_placeholder: PASS ZERO_RAW_PLACEHOLDER
typed_error_boundary: PASS ZERO_RAW_ITEM_ID
all_error_sites_audited: PASS ZERO_RUNTIME_RAW_VALUES
claim_mutations: <rejected>/<total> REJECT_BY_INTENDED_CODE
residual_fail_open_probes: 18/18 REJECT
additional_r3_fail_open_probes: 10/10 REJECT
strict_yaml_mutations: 18/18 REJECT
shifted_story_regressions: 4/4 PASS
coverage: 60/60 100.0%
coverage_roundtrip_byte_identity: 60/60 PASS
pipeline_benchmark_run_1: p95=<ms> PASS combinations=1728 all_runs=23/23
pipeline_benchmark_run_2: p95=<ms> PASS combinations=1728 all_runs=23/23
pipeline_benchmark_run_3: p95=<ms> PASS combinations=1728 all_runs=23/23
upstream_regression: 82 PASS
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact six baseline IDs>
git_diff_check: PASS
untracked_whitespace: PASS
allowlist: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
~~~

Do not return READY until every line is backed by an executed gate. Stop after
the callback and wait for architect review.
