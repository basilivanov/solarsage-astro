# Stage B3.W2 — real Today population, public identity and cache contract

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`
Parent documents: `75`, `76`, `77`
Статус: **IMPLEMENT WITHOUT COMMIT/PUSH**

## 1. Goal

Populate `TodayPayload.v2.horizons` in the real authenticated Today request
using the already computed request-local objects, then atomically advance the
public/cache version family:

~~~text
CALCULATION_VERSION          ss-calc-1.2.0 (unchanged)
ACTIVATION_LAYER_VERSION     al-1.1 (unchanged)
SCORING_V2_VERSION           ss-scoring-2.0 (unchanged)
TODAY_V2_PAYLOAD_VERSION     today.v2.1
V2_FRONTEND_PAYLOAD_VERSION  3
TODAY_CONTENT_VERSION        10
prompt version               2 (unchanged)
~~~

Fresh V2 responses must emit this exact family. The previous wire identity
`today.v2` plus frontend version `2` remains schema-compatible for cached,
fixture and migration inputs, but no fresh V2 request may emit it.

This wave ends at a reviewed, uncommitted backend/contract diff. Do not start
B3.W3, frontend B4, preview port 3003, main, deployment or services.

## 2. Architectural boundary

Add one thin integration service:

~~~text
TodayHorizonIntegrationService.build(...)
  receives existing ActivationLayer
  receives existing selected ScoringV2Result
  receives existing NatalContextData
  receives existing ConcreteAdviceBlock
  derives exact 12-key verdict mapping from row.key + row.verdict only
  calls HorizonPipelineService exactly once
  emits one sanitized day.payload_built event
  returns HorizonPipelineResult unchanged
~~~

`TodayService` remains the request orchestrator. It calls this integration
service only after `TodayInterpretationService.build` has returned the final
`ConcreteAdviceBlock` and before `SemanticV2Service.build_v2_block`.

`SemanticV2Service` receives the already built optional horizons block and a
small typed public pipeline audit. It must not select, rebuild, rewrite or
validate claims independently.

No new sidecar, natal, scoring, profile, DB, LLM, network or clock dependency
may enter `HorizonPipelineService` itself.

## 3. Exact allowed paths

Production/backend:

~~~text
apps/api/app/core/versions.py
apps/api/app/schemas/today.py
apps/api/app/services/cache_key_service.py
apps/api/app/services/canon_service.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_horizon_integration_service.py       # new
apps/api/app/services/today_service.py
scripts/audit_downstream_v2.py
scripts/audit_today.py
~~~

Backend tests:

~~~text
apps/api/tests/test_today_horizon_integration_service.py         # new
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_today_meta_versions.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_content_canon_service.py
apps/api/tests/test_payload_v2_downstream_mapping.py
apps/api/tests/test_downstream_v2_audit.py
apps/api/tests/test_audit_today_modes.py
apps/api/tests/test_day_endpoints.py
~~~

Generated contract artifacts and their owned fixture/tests:

~~~text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-fixture-roundtrip.test.ts
~~~

Owning architecture document may remain untracked and must not be edited by
the coder:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/78_STAGE_B3_W2_REAL_TODAY_POPULATION_CONTRACT_CACHE_TZ.md
~~~

No other path may change. In particular do not update the four stale
`test_semantic_v2_service.py` calls or the final real-horizon expectation in
`test_today_v2_payload.py`; those exact frozen failures belong to B3.W3.

Always preserve and never stage:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 4. Version constants and compatibility

Move the content version source of truth into `app/core/versions.py` while
keeping `from app.services.today_service import TODAY_CONTENT_VERSION`
backward-compatible through an imported module-level name.

Required constants and semantics:

~~~py
TODAY_V2_PREVIOUS_PAYLOAD_VERSION = "today.v2"
TODAY_V2_PAYLOAD_VERSION = "today.v2.1"
TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS = frozenset({
    TODAY_V2_PREVIOUS_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
})

PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION = 2
V2_FRONTEND_PAYLOAD_VERSION = 3
V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS = frozenset({2, 3})

TODAY_CONTENT_VERSION = 10
~~~

Equivalent explicit names are acceptable only if all call sites use one
canonical source and the old/current distinction remains unambiguous.

Do not change calculation, activation-layer, scoring or prompt versions.

`TodayMeta.payload_version` must accept exactly:

~~~text
today.v1
today.v2
today.v2.1
~~~

The field remains defaulted to `today.v1`. Do not narrow the existing integer
type of `frontend_payload_version`; runtime validators enforce the known V2
identity pairs without turning this additive contract change into a breaking
OpenAPI narrowing.

## 5. Public sanitized pipeline audit

In `app/schemas/today.py`, add a public CamelModel:

~~~text
TodayV2HorizonPipelineAudit
  schemaVersion = today-horizon-pipeline-audit.v1
  status = built | unavailable
  reason = existing closed HorizonSelectionReason
  selectedCount = 0 | 3
~~~

Invariants:

- `built` requires `reason=selected` and `selectedCount=3`;
- `unavailable` requires a non-selected reason and `selectedCount=0`;
- no activation IDs, natal facts, themes, spheres, actions, copy, profile data
  or raw debug values are exposed;
- use `extra=forbid`, hidden inputs in errors and structural error messages.

Add the optional field to `TodayV2Audit`:

~~~text
horizonPipeline: TodayV2HorizonPipelineAudit | null
~~~

Legacy/direct `TodayV2Block` construction may omit this field. A complete
`TodayPayload` with the current identity (`today.v2.1` or frontend version `3`)
must require it.

Extend model validation so that:

- any `today.v2` or `today.v2.1` meta identity requires non-null `v2`;
- frontend version `2` or `3` requires non-null `v2`;
- current `today.v2.1` and frontend `3` must occur as one exact pair;
- current identity requires non-null `v2.audit.horizonPipeline`;
- `v2.audit.payloadVersion` equals current meta payload version for current
  responses;
- pipeline audit `built` requires non-null `v2.horizons`;
- pipeline audit `unavailable` requires null `v2.horizons`;
- any non-null horizons block still passes the existing activation evidence
  and aggregate timing cross-reference validator.

Previous `today.v2`/frontend `2` payloads with a V2 body remain accepted and
may omit `horizonPipeline`. V1 with `v2=null` remains accepted.

## 6. Verdict mapping contract

`TodayHorizonIntegrationService` derives verdicts from
`ConcreteAdviceBlock.rows` with these exact rules:

1. Read only `row.key` and `row.verdict`.
2. Never inspect `text`, `label`, icon/color, rank, confidence or evidence.
3. Require exactly one row for every key in accepted `PRODUCT_SPHERE_ORDER`.
4. Reject missing, duplicate or unknown keys; do not silently insert neutral.
5. Return the mapping in canonical `PRODUCT_SPHERE_ORDER`, independent of row
   insertion order.
6. Do not mutate the advice block or any row.

Define a small typed `HorizonVerdictMappingError(ValueError)` with a closed
machine code such as:

~~~text
missing_spheres
duplicate_sphere
unknown_sphere
~~~

Its string representation may contain only a fixed structural prefix and the
closed code. Never include row text or user content.

The new integration module must not import SQLAlchemy, FastAPI, settings,
sidecar/client, NatalContextService, DayScoringRuntimeService, LLMService,
TodayInterpretationService or ORM models.

## 7. Integration service behavior and safe logs

Constructor injection of `HorizonPipelineService` is required for exact call
tests. Production default instantiates the accepted W1 service. Use explicit
`is not None`, not truthiness, when choosing an injected dependency.

Public entrypoint:

~~~py
TodayHorizonIntegrationService.build(
    *,
    activation_layer: ActivationLayer,
    scoring_result: ScoringV2Result,
    natal_context: NatalContextData,
    concrete_advice: ConcreteAdviceBlock,
) -> HorizonPipelineResult
~~~

Exact order:

1. derive and validate the 12 verdicts;
2. start a monotonic duration measurement;
3. call `HorizonPipelineService.build` exactly once with the exact first three
   object identities plus the derived mapping;
4. emit exactly one `day.payload_built` log for success/unavailable;
5. return the exact pipeline result object.

If verdict mapping or pipeline execution raises:

- emit exactly one failed log;
- do not include the exception body or input values;
- re-raise the exact exception;
- do not fabricate an unavailable result.

Log envelope:

~~~text
event:  day.payload_built
slice:  W-DAY
module: M-TODAY-SERVICE
block:  HORIZON_PIPELINE
duration_ms: round(monotonic elapsed milliseconds, 3)
~~~

Exact payload keys only:

~~~text
status: built | unavailable | failed
reason:
  selected | invalid_target_clock | missing_long | missing_medium |
  missing_fast | no_coherent_triple | verdict_mapping_invalid |
  pipeline_error
selected_count: 0 | 3
horizon_ids: [long, medium, fast] | []
guidance_mode: deterministic | null
~~~

Do not log activation/fact/action IDs, technique families, themes, sphere keys,
profile/user/date/birth values, row values, copy or exception text. Use a fixed
message. Logging failure must not affect the user flow through the existing
logging failure policy.

## 8. TodayService wiring

Extend `TodayService.__init__` with one optional injected
`TodayHorizonIntegrationService`. Existing `TodayService(db)` calls remain
valid.

Inside `get_today_payload`, preserve this exact order:

1. existing profile/cache/natal/transits/activation/scoring pipeline;
2. existing semantic/LLM/important/day-chart preparation;
3. `TodayInterpretationService.build` returns final `concrete_advice`;
4. only when `v2_selected`, require `dual.v2_result` as today;
5. call the injected integration service once with exact existing objects;
6. create `TodayV2HorizonPipelineAudit` from result status/reason and count;
7. call `SemanticV2Service.build_v2_block` once with:
   - exact activation layer;
   - exact `dual.v2_result`;
   - existing diff/trace;
   - exact `result.horizons`;
   - the typed public audit;
8. construct `TodayPayload` normally and let Pydantic perform final validation;
9. cache only the final public payload.

For an honest unavailable selection, return current V2 identity with:

~~~text
v2.horizons = null
v2.audit.horizonPipeline.status = unavailable
v2.audit.horizonPipeline.reason = exact selector reason
v2.audit.horizonPipeline.selectedCount = 0
~~~

Do not turn unavailable into a request error. Any error after a selected triple
or any mapping inconsistency propagates through the existing API error policy.

Forbidden in TodayService:

- second activation-layer, natal-context or scoring computation;
- deriving verdict from advice text/color/evidence;
- fixture/demo imports;
- dict injection into `v2` after validation;
- `model_construct`;
- catch-and-null around selected pipeline failures;
- horizon LLM call or rewrite.

## 9. SemanticV2Service contract

Change `build_v2_block` so `scoring_result: ScoringV2Result` is a required typed
argument rather than optional-with-runtime-null-check.

Add optional typed parameters:

~~~py
horizons: TodayV2HorizonsBlock | None = None
horizon_pipeline_audit: TodayV2HorizonPipelineAudit | None = None
~~~

The service passes both directly into the `TodayV2Block`/`TodayV2Audit`
constructors. It does not invoke any horizon service or alter the objects.

Audit canon versions must be the exact merged current map plus any exact core
scoring canon values carried by `ScoringV2Result`. The four horizon keys must
never disappear merely because scoring_result already has a canon map.

Do not update the four stale direct tests in `test_semantic_v2_service.py` in
this wave. Their missing required scoring argument is an accepted frozen
baseline to be closed in B3.W3.

## 10. Canon identity

`get_canon_versions()` becomes the single public Today/cache/audit map and must
return exactly these nine keys with string values:

~~~text
spheres
dignities
aspect_rules
activation_rules
scoring_v2
horizon_selection
horizon_language_ru
horizon_actions_ru
personal_patterns_ru
~~~

Merge the accepted outputs of `get_horizon_canon_versions()` and
`get_horizon_content_canon_versions()` through local imports that do not create
an import cycle. Do not duplicate literal horizon versions in
`canon_service.py`.

The existing dedicated horizon version functions remain valid and unchanged in
meaning.

## 11. Cache identity

Add `content_version` to `TodayCacheKey`, its serialized hash material and
`build_today_cache_key`. Default it from the canonical core version constant.

The cache hash for fresh requests must therefore include:

~~~text
user/date/profile hash
calculation version
activation layer version
scoring version
all nine canon versions through canon_versions_hash
prompt version 2
content version 10
frontend payload version 3
~~~

No database migration is allowed. Existing cache columns remain; content
version is represented in the deterministic hash and public JSON. Existing
read-time JSON content-version validation also remains.

Update cache read guards so both known V2 payload versions and both known V2
frontend versions require a non-null V2 body. Current identity without the
pipeline audit must miss through normal Pydantic validation.

Tests must prove:

- expected read key equals actual write key;
- changing content 9 -> 10 changes hash;
- changing frontend 2 -> 3 changes hash;
- changing any horizon canon version changes hash;
- previous valid V2 schema input remains parseable;
- stale or contradictory current cache rows are misses, never request errors.

## 12. Audit tools

Update only V2 identity recognition in the two allowed audit scripts:

- use the shared compatible payload-version set;
- use `V2_FRONTEND_PAYLOAD_VERSION` instead of hard-coded `2` for fresh
  synthetic output;
- recognize previous frontend `2` and current `3` as V2;
- fresh audit wording expects `today.v2.1` while compatibility inputs may still
  be `today.v2`;
- do not otherwise refactor, split or reformat these legacy scripts.

Their existing baseline GRACE debt is out of scope. Add no new GRACE violation
in changed functions.

## 13. Generated contracts and canonical fixture

Regenerate OpenAPI, TypeScript and Zod only from Pydantic source. Never hand
edit generated files.

The canonical JSON fixture must be normalized and updated to the exact fresh
version family:

~~~text
meta.calculationVersion = ss-calc-1.2.0
meta.activationLayerVersion = al-1.1
meta.scoringVersion = ss-scoring-2.0
meta.payloadVersion = today.v2.1
meta.frontendPayloadVersion = 3
meta.contentVersion = 10
meta.promptVersion = 2
meta.canonVersions = exact nine-key map

v2.audit.calculationVersion = ss-calc-1.2.0
v2.audit.activationLayerVersion = al-1.1
v2.audit.scoringVersion = ss-scoring-2.0
v2.audit.payloadVersion = today.v2.1
v2.audit.canonVersions = exact nine-key map
v2.audit.horizonPipeline = built / selected / 3
~~~

Do not change the accepted human copy, timing, actions, activation IDs or
visual content of the fixture. Run the repository normalizer; do not format it
manually.

Contract tests must explicitly prove:

- current fixture parses through generated `TodayPayloadWireSchema`;
- current version/audit/canon family is exact;
- previous `today.v2` plus frontend `2` with V2 body remains accepted;
- current identity with missing pipeline audit is rejected by Pydantic;
- built/unavailable audit-to-horizons contradictions are rejected by Pydantic;
- no handwritten V2 wire schema appears in frontend code.

### 13.1 Generated-Zod boundary

Do not add a handwritten refinement to `packages/contracts/runtime.ts`,
`lib/contracts/today.ts` or any other frontend runtime file. Those paths are
outside the allowlist and would create a second wire-contract authority.

The local three-field `TodayV2HorizonPipelineAudit` invariant must be visible
to OpenAPI/Zod by expressing it in Pydantic as a discriminated union of strict
built and unavailable variants (or an equivalent Pydantic-native union that
generates `oneOf`/discriminator). Generated Zod must therefore reject an audit
object such as `status=built, reason=missing_fast, selectedCount=0`.

Use two named strict CamelModel variants, for example
`TodayV2HorizonPipelineBuiltAudit` and
`TodayV2HorizonPipelineUnavailableAudit`, plus an `Annotated[Built |
Unavailable, Field(discriminator="status")]` alias for the public field.
`TodayService` constructs the concrete variant class; it must not try to call a
`TypeAliasType` alias as though it were a Pydantic model.

The cross-object relationship between `TodayV2Audit.horizonPipeline` and the
sibling `TodayV2Block.horizons` is enforced by the existing Pydantic
`TodayV2Block`/`TodayPayload` validators. OpenAPI 3.1 generation in this
repository does not preserve arbitrary cross-object `model_validator` logic;
do not fake that guarantee in generated-Zod tests. TypeScript tests should
prove the generated audit union plus valid current/previous fixture parsing,
while Python contract tests prove missing-audit and audit-to-horizons
contradictions.

Compatibility report requirements:

~~~text
breakingChanges = 0
overrideUsed = false
~~~

The enum expansion and optional audit schema are additive. Do not use a
compatibility override.

## 14. Tests for the new integration service

The new test file requires full GRACE structure and must cover:

1. Three accepted real B2 stories produce built results through the real W1
   pipeline using 12 typed advice rows.
2. Advice row order permutations yield byte-identical verdict mapping/result.
3. Text, labels, confidence and evidence sentinel changes cannot affect the
   mapping or result.
4. Missing/duplicate rows fail with the exact sanitized typed mapping code.
5. Honest unavailable preserves exact reason and logs unavailable once.
6. Built logs exactly one safe built event with long/medium/fast only.
7. Injected pipeline exception is re-raised by identity and logs failed once.
8. Pipeline receives exact activation/scoring/natal object identities and is
   called exactly once.
9. Advice, activation, scoring and natal inputs are byte-identical before and
   after.
10. Source AST/import guard proves no forbidden runtime dependency and proves
    mapping code does not access advice text/evidence/label/color fields.
11. Captured log envelope/payload contains none of several raw sentinel IDs,
    profile strings or human copy fragments.

Modify the existing V2-selected Today meta test to inject/spy the integration
service and prove `TodayService` passes exact already-computed objects once,
then emits current identity and a consistent unavailable audit for its
single-activation fixture. Do not force that fixture into a fake triple.

## 15. Baseline failure policy

Before this wave the full API suite has exactly six accepted failures:

1. calendar duplicate-cache winning-row reread;
2. four stale `test_semantic_v2_service.py` calls missing scoring_result;
3. one stale `test_today_v2_payload.py` selected-path expectation.

W2 must introduce zero additional failures. Updating the explicit
`TODAY_CONTENT_VERSION == 9` assertion in `test_day_endpoints.py` to `10` is
part of this atomic version wave; preserve and strengthen its stale-cache
invalidation proof.

Do not fix the six accepted failures here. B3.W3 owns them.

## 16. GRACE and change-size rules

Full GRACE is mandatory for:

~~~text
apps/api/app/services/today_horizon_integration_service.py
apps/api/tests/test_today_horizon_integration_service.py
~~~

`today_service.py` must remain GRACE-clean. Add paired function contracts for
new/changed public validators or functions in touched legacy files, but do not
rewrite unrelated legacy files solely to erase pre-existing lint debt.

Limits:

~~~text
new integration service <= 320 lines
new integration test <= 750 lines
new production lines <= 140 characters
no changed production function > 140 lines
today_service.py net growth <= 70 lines
semantic_v2_service.py net growth <= 90 lines
today.py net growth <= 130 lines
~~~

No broad formatting or import sorting outside touched blocks.

## 17. Mandatory gates

Focused backend:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_today_horizons_contract.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_content_canon_service.py \
  apps/api/tests/test_payload_v2_downstream_mapping.py \
  apps/api/tests/test_downstream_v2_audit.py \
  apps/api/tests/test_audit_today_modes.py \
  apps/api/tests/test_day_endpoints.py -q
~~~

Horizon regression:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_service.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q
~~~

Request reuse regression:

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_wave3_day_pipeline_reuse.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_concrete_advice.py -q
~~~

GRACE for new/clean owned files:

~~~bash
python3 scripts/grace_lint.py \
  apps/api/app/services/today_horizon_integration_service.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/app/services/today_service.py
~~~

Contracts:

~~~bash
pnpm contracts:sync
pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
~~~

Run the real compatibility checker with JSON output and prove exact zero
breaking changes and no override. Run generation and fixture check a second
time and prove byte-identical hashes for all three generated files and the JSON
fixture.

Full backend evidence:

~~~bash
cd apps/api
source .venv/bin/activate
python -m pytest tests/ -q
~~~

The only failures may be the exact six in section 15. Any other failure is a
W2 blocker.

Static/git gates:

~~~bash
git diff --check
git diff --cached --quiet
git status --short
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
~~~

Also prove:

- exact allowed changed-path set;
- untracked-file whitespace clean;
- new/changed production line lengths and change-size budgets;
- no forbidden imports;
- generated files were not hand edited;
- frozen unrelated paths untouched;
- accepted W1 local/origin SHA unchanged;
- index empty;
- no commit/push.

## 18. Exact callback

~~~text
READY_STAGE_B3_W2_REVIEW
changed_paths: <exact allowlisted paths>
accepted_w1_sha: ecae4d0ff95bf29953fbb6957e48c38a7d22e198 local/origin unchanged
runtime_wiring_exact_reuse: PASS activation/scoring/natal/advice once
verdict_mapping: 12/12 EXACT key+verdict only
pipeline_built: <passed>/<total> PASS
pipeline_unavailable: PASS <reason>
pipeline_fail_closed: PASS exact exception identity
public_audit_alignment: PASS built/non-null unavailable/null
fresh_versions: ss-calc-1.2.0 al-1.1 ss-scoring-2.0 today.v2.1 frontend=3 content=10 prompt=2
previous_v2_compatibility: PASS today.v2/frontend=2
canon_versions: 9/9 EXACT
cache_identity: PASS content+frontend+horizon_canons included
safe_logs: PASS exact payload allowlist no PII/copy/IDs
contract_compat: breakingChanges=0 overrideUsed=false
generated_idempotence: PASS
fixture_current_wire: PASS normalized
focused_backend: <count> PASS
horizon_regression: <count> PASS
request_reuse: <count> PASS
contract_vitest: <count> PASS
full_api: <passed> passed, <skipped> skipped, exact 6 frozen failures only
grace_owned: PASS 3/3
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
