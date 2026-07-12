# Stage B3.W3A — full-green backend and canonical runtime identity

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `9e1c6c0af9103e73e56d65644642d5c075fba3a3`
Authority: `00`, `50`, `51`, `75`, accepted W1/W2 documents through `79C`
Статус: **IMPLEMENTATION — NO COMMIT/PUSH**

## 1. Outcome

Make the complete API suite green with zero frozen failures and remove the
version/cache identity drift that caused the calendar failure.

This wave closes exactly the current authoritative baseline:

~~~text
6 failed, 1243 passed, 4 skipped
~~~

The six failures are:

1. calendar semantic-cache write cannot be reread because its write identity
   is derived differently from the read identity;
2. four stale SemanticV2 unit tests omit the now-required typed
   `ScoringV2Result`;
3. one stale Today V2 payload test selects V1 but expects a V2 response and
   asserts the retired `today.v2` / frontend `2` identity.

Do not weaken any W2 production invariant to make these tests pass.

## 2. Architectural correction — one runtime identity resolver

The underlying calendar defect is duplicated V1/V2 version-family mapping.
`TodayService` already compensates for the fact that a locally built
`ActivationLayer` carries current calculation identity even when V1 scoring is
selected; `CalendarService` does not. The read path uses
`expected_cache_identity`, so calendar writes and reads can disagree.

Create one pure canonical resolver in
`apps/api/app/services/cache_key_service.py`.

Recommended public names:

~~~py
@dataclass(frozen=True)
class TodayRuntimeIdentity:
    calculation_version: str
    activation_layer_version: str
    scoring_version: int | str
    payload_version: str
    frontend_payload_version: int
    content_version: int

def resolve_today_runtime_identity(
    *,
    selected_scoring_version: int | str,
    activation_layer_version: str | None,
) -> TodayRuntimeIdentity:
    ...
~~~

Equivalent naming is allowed only if ownership and semantics remain exact.

Required mapping:

~~~text
selected scoring == SCORING_V2_VERSION
  calculation      CALCULATION_VERSION
  activation       supplied activation version or ACTIVATION_LAYER_VERSION
  scoring          SCORING_V2_VERSION
  payload          TODAY_V2_PAYLOAD_VERSION
  frontend         V2_FRONTEND_PAYLOAD_VERSION
  content          TODAY_CONTENT_VERSION

all other selected scoring values
  calculation      LEGACY_CALCULATION_VERSION
  activation       supplied activation version or ACTIVATION_LAYER_VERSION
  scoring          LEGACY_SCORING_VERSION
  payload          TODAY_V1_PAYLOAD_VERSION
  frontend         LEGACY_FRONTEND_PAYLOAD_VERSION
  content          TODAY_CONTENT_VERSION
~~~

Invariants:

- selected scoring is the only family selector;
- `SOLARSAGE_V2_FRONTEND_ENABLED` never selects payload/cache identity;
- dual-run computation does not imply V2 selection;
- the caller's current activation-layer version is retained when non-null;
- no settings, DB, sidecar or network access occurs in the resolver;
- returned identity is immutable;
- string/int comparison remains tolerant in the same way as current code.

Use this resolver in all three boundaries:

1. `expected_cache_identity` uses it with
   `selected_scoring_version_for_flags()`;
2. `TodayService.get_today_payload` uses it with the exact
   `dual.selected_scoring_version`, then uses the same returned identity for
   cache key fields and public meta payload/frontend/content family;
3. `CalendarService._compute_and_cache_day_status` uses it with the exact
   `dual.selected_scoring_version` before writing semantic cache.

Do not leave a second hand-written V1/V2 identity table in TodayService or
CalendarService. `build_today_cache_key` remains the low-level hash builder;
the resolver owns family selection.

Do not change cache key fields, hash algorithm, canon hashing, version values,
feature-flag semantics or DB schema.

## 3. Calendar failure

Keep and pass:

~~~text
apps/api/tests/test_calendar_endpoints.py::
  test_calendar_status_cache_duplicate_rereads_winning_row
~~~

The production correction must make a V1-selected write use the same canonical
identity as a subsequent read even when the activation object itself carries
the current V2 calculation version.

Add focused resolver/cache proofs in
`apps/api/tests/test_today_cache_v2_key.py`:

- V1 selected + current activation object maps to the exact legacy
  calculation/scoring/frontend/payload family;
- V2 selected maps to the exact current family;
- V1 and V2 `expected_cache_identity` hashes equal write hashes constructed
  from the same resolved family;
- frontend flag true while V1 scoring is selected does not alter identity;
- dual-run true while V1 is selected does not alter identity;
- supplied activation-layer version is preserved; null uses the canonical
  fallback;
- resolver result is frozen/immutable.

Do not relax semantic-cache validation and do not accept incomplete legacy
rows. Do not add a retry loop or broad exception swallowing.

## 4. SemanticV2 stale tests

In `apps/api/tests/test_semantic_v2_service.py`, add one small reusable fixture
or helper that returns a valid typed empty `ScoringV2Result` with:

- current `SCORING_V2_VERSION`;
- valid `day_status`;
- empty score/status/signal/activation collections where the schema permits;
- a typed canon map appropriate for the test.

Pass that exact typed object into these four calls:

~~~text
test_semantic_v2_service_no_convergence
test_semantic_v2_service_with_convergence
test_audit_canon_versions_only_contains_strings
test_techniques_list_is_sorted
~~~

Required:

- keep `SemanticV2Service.build_v2_block(scoring_result: ScoringV2Result)`
  mandatory;
- no default, optional annotation, `getattr`, dict duck typing or production
  fallback;
- retain all existing behavioral assertions;
- add an assertion proving the typed input was not mutated if not already
  covered in the file.

## 5. Today V2 payload stale test

Correct
`test_today_payload_v2_block_included_when_flag_enabled` in
`apps/api/tests/test_today_v2_payload.py` so the setup really selects V2.

Required setup and assertions:

- `settings.solarsage_v2_enabled = True` is the selection authority;
- dual-run may be false; frontend flag must not be required for selection;
- sidecar activation dict uses current `CALCULATION_VERSION` and
  `ACTIVATION_LAYER_VERSION` constants, not stale literals;
- assert selected scoring is `SCORING_V2_VERSION`;
- assert `payload.v2 is not None`;
- assert meta payload/frontend/content are exactly
  `today.v2.1` / `3` / `10` through imported constants;
- assert `payload.v2.audit.payload_version` matches meta;
- assert a typed `audit.horizon_pipeline` exists;
- with the intentionally empty activation setup, accept only the honest
  `unavailable`/`horizons is None` result; do not fabricate a triple in this
  unit test;
- retain the separate disabled-path test and prove V1/null remains unchanged.

Rename the stale docstring and test name only if needed to describe selected
scoring rather than the retired frontend flag behavior. Do not patch the
horizon integration service in this test merely to force output.

## 6. Content-version proof

`TODAY_CONTENT_VERSION` is already canonical `10` and the endpoint assertion
already says `10`. Do not bump it again.

Run and preserve tests proving:

- content version `9` cache rows miss;
- content version `10` rows can hit when all other identity fields match;
- current V2 emits content `10`;
- current cache hash differs from an otherwise identical content `9` key.

## 7. Exact allowed paths

Production:

~~~text
apps/api/app/services/cache_key_service.py
apps/api/app/services/calendar_service.py
apps/api/app/services/today_service.py
~~~

Tests:

~~~text
apps/api/tests/test_calendar_endpoints.py
apps/api/tests/test_semantic_v2_service.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_today_v2_payload.py
~~~

Owning document:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/81_STAGE_B3_W3A_FULL_GREEN_IDENTITY_STABILIZATION_TZ.md
~~~

No other path may change. A test path need not be edited if existing coverage
already proves the requirement.

## 8. GRACE and code quality

- Preserve/update module contracts and maps in the three production files.
- Add function contracts for the new resolver and any non-trivial helper.
- Exact `emitted_logs` remain unchanged; the resolver emits none.
- Added production lines are at most 140 characters.
- No new broad `Any`, `type: ignore`, optional fallback or raw-data log.
- `cache_key_service.py` remains below 300 lines.
- Do not perform unrelated formatting/import cleanup.

## 9. Mandatory gates

Run from repository root.

### 9.1 Exact former failures

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row \
  apps/api/tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence \
  apps/api/tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence \
  apps/api/tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings \
  apps/api/tests/test_semantic_v2_service.py::test_techniques_list_is_sorted \
  apps/api/tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled -q
~~~

If the Today test is renamed, run its exact replacement and report the name.

### 9.2 Focused regression

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_calendar_endpoints.py \
  apps/api/tests/test_semantic_v2_service.py \
  apps/api/tests/test_today_v2_payload.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_today_horizons_contract.py -q
~~~

### 9.3 Full backend

Authoritative invocation is from repository root:

~~~bash
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
~~~

Required: zero failures. Do not accept a frozen baseline any longer.

### 9.4 W2/horizon regression

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

### 9.5 Static/contract no-diff proof

~~~bash
python3 scripts/grace_lint.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/app/services/calendar_service.py \
  apps/api/app/services/today_service.py

pnpm contracts:sync
pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
npx tsc --noEmit

git diff -- packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
git diff --check
git diff --cached --quiet
git status --short
~~~

Generated contracts and fixture must remain byte-identical. If
`pnpm contracts:sync` changes them, stop and report the unexpected public diff.

## 10. Forbidden

- no production signature weakening;
- no public schema/generated/fixture/version change;
- no DB migration;
- no LLM/refinement work;
- no real DB/sidecar/API proof yet (owned by W3B);
- no frontend/B4 work;
- no service/env/port changes;
- no `main` switch;
- no stage/commit/push;
- no subagents/delegation;
- never touch `.grace/`, `artifacts/design/`, the frozen superpowers plan,
  `grace.db` or `skills/`.

## 11. Exact callback

~~~text
READY_STAGE_B3_W3A_REVIEW
runtime_identity_resolver: PASS one immutable canonical family mapping
today_calendar_identity_parity: PASS V1 and V2 read/write hashes
former_failures: 6/6 PASS
focused_backend: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
horizon_regression: 242 PASS
content_version_10: PASS with version-9 invalidation proof
grace: PASS 3/3
contracts: PASS_NO_DIFF
contract_vitest: 21 PASS
typecheck: PASS
git_diff_check: PASS
parent_sha: 9e1c6c0af9103e73e56d65644642d5c075fba3a3 local/origin unchanged
changed_paths: <count> EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
