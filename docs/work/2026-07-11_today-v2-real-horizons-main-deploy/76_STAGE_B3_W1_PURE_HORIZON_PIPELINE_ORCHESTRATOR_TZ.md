# Stage B3.W1 — pure HorizonPipelineService orchestration boundary

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `75_STAGE_B3_BACKEND_REAL_API_INTEGRATION_MASTER_TZ.md`
Prerequisite: `PUSHED_STAGE_B2B2` from document `74`, local/origin feature SHA equal
Статус: **IMPLEMENT WITHOUT COMMIT/PUSH**

## 1. Goal

Create the single pure internal service that composes the already accepted
B2A/B2B services into an atomically validated optional public horizons block.

This wave must not touch TodayService, SemanticV2Service, public Pydantic
barrels, generated contracts, cache/version constants, frontend or runtime.

## 2. Exact allowed paths

New production files:

~~~text
apps/api/app/schemas/horizon_pipeline.py
apps/api/app/services/horizon_pipeline_service.py
~~~

New/owned test file:

~~~text
apps/api/tests/test_horizon_pipeline_service.py
~~~

Existing B2B2 evidence tests that may be changed to exercise the real
orchestrator instead of manually composing services:

~~~text
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_pipeline_benchmark.py
~~~

Architecture docs owned by this upcoming backend stage may remain untracked;
do not edit them:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/75_STAGE_B3_BACKEND_REAL_API_INTEGRATION_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/76_STAGE_B3_W1_PURE_HORIZON_PIPELINE_ORCHESTRATOR_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/80_STAGE_B4_FRONTEND_REAL_DATA_PREVIEW_MASTER_TZ.md
~~~

No other path may change. Never touch the frozen unrelated paths listed in
parent `75`.

## 3. Internal result contract

In `horizon_pipeline.py`, define strict frozen internal models/types with
`extra=forbid` and `hide_input_in_errors=True`.

Required result shape (field names may follow repository Python naming, but
semantics are fixed):

~~~text
schema_version = horizon-pipeline-result.v1
status = built | unavailable
horizons = TodayV2HorizonsBlock | None
selection_reason = existing HorizonSelectionReason
selection_diagnostics = existing HorizonSelectionDiagnostics
~~~

Invariants:

- `built` requires `selection_reason=selected` and non-null horizons;
- `unavailable` requires non-selected reason and null horizons;
- diagnostics contain only bounded machine counts/reasons;
- result contains no selected natal facts, raw copy, profile data, IDs outside
  the already public horizons block or debug payload.

Do not re-declare existing selection diagnostics/reason types.

## 4. Service contract

Public entrypoint:

~~~py
HorizonPipelineService.build(
    *,
    activation_layer: ActivationLayer,
    scoring_result: ScoringV2Result,
    natal_context: NatalContextData,
    sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
) -> HorizonPipelineResult
~~~

Exact call order:

1. `HorizonSelectionService.select` with the exact layer/scoring objects.
2. If `selection is None`, return `unavailable` with the exact closed reason and
   diagnostics. Call no later service.
3. `PersonalFactPackService.build` with accepted selection and exact inputs.
4. `HorizonToneService.assess` with the exact selection/verdict mapping.
5. Construct `HorizonGuidanceContext`.
6. `HorizonGuidanceService.build`.
7. `HorizonClaimValidator.validate` against
   `activation_layer.activations`.
8. Return `built` only with the validated block returned by the validator.

No try/except may convert steps 3–7 into `unavailable`. Those errors represent
internal inconsistency and must propagate as sanitized typed errors.

## 5. Dependency and mutation rules

The service module must not import:

~~~text
DB/SQLAlchemy
settings/env
FastAPI/HTTPException
solarsage client
NatalContextService
DayScoringRuntimeService
LLMService
TodayService/SemanticV2Service
datetime.now/time/random/network
~~~

Constructor dependency injection is allowed and recommended for exact call-count
tests, but production defaults must instantiate the accepted deterministic
services.

Do not mutate any input. Capture `model_dump(mode="json")` before/after in
tests for layer, scoring and natal data. The verdict mapping also remains byte
equivalent.

## 6. Required tests

### 6.1 Real composition

Using existing B2A/B2B testkits, run at least three substantially different
accepted stories through `HorizonPipelineService`:

- result status is `built`;
- horizons are exactly long/medium/fast;
- intro/content differs materially between stories;
- result validates against real source activation evidence;
- guidance mode remains deterministic;
- a second build serializes byte-identically.

Do not use a prebuilt horizons block as input.

### 6.2 Honest unavailable

Use real-shaped inputs lacking at least one eligible horizon:

- exact selection reason is preserved;
- horizons is null;
- fact/tone/guidance/validator spies have zero calls;
- no exception and no fabricated fallback triple.

### 6.3 Fail-closed after selection

Force each downstream boundary to fail separately:

~~~text
fact pack
tone
guidance
claim validator
~~~

The exact exception propagates and no `unavailable` result is returned. Raw
sentinels/claim bodies must not appear in `str(exc)`.

### 6.4 Call count and order

With injected spies/fakes, assert each successful dependency is called exactly
once and in the exact order from section 4. Assert the validator receives the
same activation objects/order from the input layer.

### 6.5 Coverage and benchmark migration

Update the existing 60-case YAML coverage test to execute the orchestrator as
the product composition boundary. Preserve all existing assertions:

~~~text
60/60 selected
60/60 contract ready
12 dates / 5 timezones
roundtrip + second-build byte identity
18/18 strict YAML mutations rejected
~~~

Update the existing benchmark so its measured pipeline is:

~~~text
selection -> facts -> tone -> guidance -> validator via HorizonPipelineService
~~~

Preserve real 120 story combinations, 40/40/40 distribution, 1728 bounded
configurations and 23/23 runs. Isolated p95 must remain `<100 ms`.

## 7. GRACE and size constraints

Both new production files and the new test file require full repository GRACE
headers/module contracts/maps and function contracts.

Limits:

~~~text
schema file <= 220 lines
service file <= 300 lines
new test file <= 650 lines
existing test files remain <= 700 lines
production lines <= 140 characters
~~~

No public schema re-export and no generated contract diff.

## 8. Mandatory gates

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q

python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_pipeline.py \
  apps/api/app/services/horizon_pipeline_service.py \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py -q

pnpm contracts:check
git diff --check
git diff --cached --quiet
~~~

Run benchmark three times sequentially and isolated. Do not run it concurrently
with another test process.

Also prove:

- exact allowlist;
- untracked whitespace clean;
- line counts/line lengths;
- no forbidden imports;
- accepted HEAD/origin unchanged;
- index empty;
- no commit/push.

## 9. Callback

~~~text
READY_STAGE_B3_W1_REVIEW
changed_paths: <exact allowed implementation/test paths>
accepted_b2b2_sha: <local/origin SHA>
pipeline_success_stories: <passed>/<total>
pipeline_unavailable: PASS <exact reason cases>
downstream_fail_closed: 4/4 PASS
call_order_once: PASS
input_immutability: PASS
coverage: 60/60 100.0%
strict_yaml_mutations: 18/18 REJECT
roundtrip_byte_identity: 60/60 PASS
benchmark_run_1: p95=<ms> 1728 23/23 PASS
benchmark_run_2: p95=<ms> 1728 23/23 PASS
benchmark_run_3: p95=<ms> 1728 23/23 PASS
focused_tests: <count> PASS
upstream_tests: <count> PASS
grace: PASS 5/5
contracts: PASS_NO_PUBLIC_DIFF
forbidden_imports: ZERO
size_limits: PASS <counts>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
