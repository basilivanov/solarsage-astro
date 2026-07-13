# Stage B3 master ТЗ — real API population, identity and backend proof

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Prerequisite: accepted and pushed Stage B2B2 commit from document `74`
Authority: `00`, `50`, `51`, `63`, accepted B1/B2A/B2B1/B2B2 documents
Статус: **BACKEND EXECUTION PLAN — RUN ONLY ONE AUTHORIZED WAVE AT A TIME**

## 1. Outcome of Stage B3

Stage B3 is complete only when a normal authenticated request to the real
FastAPI `/api/day/<date>` can return a `TodayV2Block` containing a validated
backend-owned `horizons` block built from the already available calculation
objects:

~~~text
existing ActivationLayer
existing selected ScoringV2Result
existing NatalContextData
existing ConcreteAdvice verdict rows
  -> coherent selection
  -> personal fact pack
  -> per-horizon tone
  -> deterministic guidance
  -> strict claim validation
  -> TodayV2Block.horizons
~~~

No second sidecar, natal, scoring, DB profile, LLM or network call is allowed
for horizons.

Stage B3 does not redesign the frontend. It prepares the real public payload
that B4 renders.

## 2. Product and safety decisions

### 2.1 Deterministic release copy

The first production release ships `guidanceMode=deterministic` only.

An LLM must not rewrite personal claims/actions during this release path. The
current canon-backed copy already contains the accepted human explanations,
manifestations, strength/risk and actions. This maximizes factual precision and
keeps every statement reconstructable by the validator.

LLM refinement may be proposed later only as a separate opt-in wave proving:

- byte-independent semantic equivalence;
- unchanged provenance;
- no new claim/action/number/life assertion;
- atomic validation and deterministic fallback.

### 2.2 Honest no-triple outcome

`HorizonSelectionResult.selection=None` is an ordinary typed outcome. The API
must return `v2.horizons=null` plus a sanitized structured diagnostic; it must
not force weak or incoherent evidence into three cards.

Invalid internal alignment after a triple was selected is not an ordinary
fallback. When V2 is selected it fails loudly through the existing API error
policy and emits no personal/raw data in logs.

### 2.3 Version family

Final backend identity for this release:

~~~text
CALCULATION_VERSION           ss-calc-1.2.0 (already shared)
ACTIVATION_LAYER_VERSION      al-1.1 (already shared)
SCORING_V2_VERSION            ss-scoring-2.0 (unchanged)
TODAY_V2_PAYLOAD_VERSION      today.v2.1
V2_FRONTEND_PAYLOAD_VERSION   3
TODAY_CONTENT_VERSION         10
LLM prompt version            2 (unchanged: no horizon LLM ships)
~~~

The public `payloadVersion` schema must continue accepting old `today.v2` for
cached/migration compatibility while new V2 responses emit `today.v2.1`.

## 3. Wave decomposition

### B3.W1 — pure HorizonPipelineService

Goal: create one internal orchestration boundary that composes accepted B2
services without touching TodayService or the public contract.

Required architecture:

~~~text
HorizonPipelineService.build(...)
  -> HorizonSelectionService.select
  -> if no selection: typed result with horizons=None + reason/diagnostics
  -> PersonalFactPackService.build
  -> HorizonToneService.assess
  -> HorizonGuidanceContext
  -> HorizonGuidanceService.build
  -> HorizonClaimValidator.validate
  -> typed result with validated horizons
~~~

Inputs:

- exact `ActivationLayer`;
- exact `ScoringV2Result`;
- exact cached `NatalContextData`;
- exact product-sphere verdict mapping from caller.

The service is pure/deterministic, performs no I/O and has bounded runtime.
Add a frozen internal result model with only sanitized reason/diagnostics and
the optional public horizons block. Do not expose natal facts or claim bodies in
diagnostics.

Mandatory proof:

- at least three distinct real-shaped stories build distinct complete blocks;
- no-triple returns honest typed null;
- malformed selected pipeline fails, never silently nulls;
- second build is byte-identical;
- inputs are not mutated;
- no duplicate sidecar/natal/scoring/LLM calls are possible by dependency shape;
- p95 remains below 100 ms using the accepted 120/1728 corpus.

No public/generated contract diff in W1.

### B3.W2 — Today/Semantic population, cache identity and public contract

Goal: populate real `v2.horizons` in the existing Today request using only
already computed local variables.

Integration order inside `TodayService.get_today_payload`:

1. existing profile/cache/natal/transits/activation/scoring;
2. existing interpretation builds `ConcreteAdviceBlock`;
3. derive `sphere_verdicts` only from `concrete_advice.rows[*].key/verdict`;
4. call `HorizonPipelineService` with existing typed objects;
5. pass the returned block into `SemanticV2Service.build_v2_block`;
6. construct `TodayPayload`; Pydantic performs final public cross-reference;
7. cache exactly the public payload.

Forbidden:

- inferring verdict from row text/color;
- reading ORM profile in horizon pipeline;
- calling sidecar/natal/scoring a second time;
- attaching a fixture block;
- `model_construct`/unchecked dict injection;
- swallowing a selected-pipeline validation error.

`SemanticV2Service.build_v2_block` receives an optional typed horizons argument.
It does not build horizons itself.

Version/cache work is atomic in this wave:

- emit `today.v2.1`, frontend version `3`, content version `10`;
- keep old `today.v2` accepted, not emitted by fresh V2 path;
- include accepted horizon selection/language/actions/pattern canon versions in
  `TodayMeta.canonVersions` and cache identity;
- update cache read/write/version tests together;
- regenerate OpenAPI/TS/Zod from Pydantic source only;
- normalize the canonical JSON fixture from generated wire shape;
- compatibility report must show `breakingChanges=0`, `overrideUsed=false`.

Structured logs use existing registered `day.payload_built` with:

~~~text
slice=W-DAY
module=M-TODAY-SERVICE or M-HORIZON-PIPELINE-SERVICE
block=HORIZON_PIPELINE
payload allowlist only:
  status=built|unavailable|failed
  reason=<closed enum>
  selected_count=0|3
  horizon_ids=[long,medium,fast] or []
  guidance_mode=deterministic|null
  duration_ms rounded
~~~

No activation/fact/action IDs, theme/sphere/profile values or copy in logs.

### B3.W3 — backend stabilization and real API proof

Goal: make the backend release candidate full-green and prove real data.

Close the six frozen baseline failures instead of accepting them:

1. calendar duplicate-cache reread must deterministically return the winning
   row after write;
2. four SemanticV2 tests must use the required real `ScoringV2Result` contract,
   not weaken production validation;
3. V2 Today payload test must follow selected-scoring identity and assert the
   real horizons result/version family.

Also update the explicit `TODAY_CONTENT_VERSION == 9` assertion to `10` with
cache invalidation proof.

Required real API evidence on feature branch:

- canonical API service remains on `8000` (no manual uvicorn);
- dev auth uses `/api/auth/dev` only from localhost development flow;
- a real dev user/date produces `today.v2.1`, frontend `3`, content `10`;
- exactly `long, medium, fast` for the selected acceptance date;
- every horizon activation provenance resolves against
  `v2.activationEvidence`;
- timing ranges/peak/state are non-null according to contract;
- no fixture marker or frontend inference source;
- redacted payload proof contains no auth/profile/birth data.

If the canonical dev user/date honestly has no coherent triple, do not weaken
thresholds. Select a different existing test profile/date or create a dedicated
test-only database profile through normal dev onboarding data, document it, and
keep product selection unchanged.

Stage B3 acceptance requires:

~~~text
API full suite: green, zero baseline failures
sidecar full suite: green
contracts generate/check/compat: green and idempotent
backend guardrails/GRACE/logging guardrails: green
real API proof: pass
feature branch commit/push: accepted separately
~~~

## 4. Per-wave lifecycle

Each wave follows:

~~~text
architect writes exact wave TZ
coder implements without commit/push
architect reviews every changed path and reruns gates
correction wave(s) if needed
architect acceptance + exact commit/push TZ
coder commits/pushes exact allowlist
architect verifies origin SHA
~~~

No wave may borrow future-wave scope to make its focused tests pass.

## 5. Global forbidden paths and operations

Always preserve:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Before final release do not touch `main`, systemd, nginx, production env,
`.next-prod` or canonical service processes.
