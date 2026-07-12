# Stage B3.W2 — architect review R2: final typed/canonical cleanup

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`
Parent documents: `78`, `79`, `79A`
Статус: **THREE NARROW CORRECTIONS; NO COMMIT/PUSH**

## 1. Review verdict

R1 behavior and test coverage are accepted. Independent architect reruns:

~~~text
focused backend: 167 passed
horizon regression: 242 passed
request reuse: 15 passed
generated/fixture hashes: exact expected values
~~~

Before W2 acceptance, correct exactly three narrow code-quality/canonical-source
issues. Do not change behavior, tests, wire shape, generated contracts, fixture
or version values.

## 2. Correction A — new production line exceeds 140 characters

`apps/api/app/schemas/today.py` contains one newly added 143-character GRACE
contract line in `TodayPayload.validate_v2_identity_requires_body`:

~~~text
# error_behavior: raises ValueError for missing V2 body, contradictory current pair, missing pipeline audit, or audit payload mismatch.
~~~

Split it into two GRACE comment lines, each at most 140 characters. Preserve the
same meaning and paired contract markers.

After correction, this command must print nothing:

~~~bash
git diff -U0 -- apps/api/app scripts | \
  awk '/^\+\+\+/{next} /^\+/{line=substr($0,2); if (length(line)>140) print length(line) ":" line}'
~~~

Do not rewrite pre-existing long lines outside added W2 lines.

## 3. Correction B — preserve the required typed SemanticV2 boundary

`SemanticV2Service.build_v2_block` now requires a typed
`ScoringV2Result`, but the implementation still uses a defensive
`getattr(scoring_result, "canon_versions", {})` and leaves
`SCORING_V2_VERSION` newly unused after the old fallback was removed.

Required cleanup in `apps/api/app/services/semantic_v2_service.py`:

1. Remove only the newly unused `SCORING_V2_VERSION` import. Do not perform a
   broad unrelated unused-import cleanup.
2. Consolidate `CANON_VERSIONS` and `get_canon_versions` into the existing
   top-level import from `app.services.canon_service`; do not import them inside
   `build_v2_block`.
3. Read `scoring_result.canon_versions` directly. The argument and field are
   required typed contracts; no `getattr`, dict duck typing or null fallback.
4. Overlay only keys present in canonical `CANON_VERSIONS`.
5. Prefer membership against `CANON_VERSIONS` directly; do not allocate a new
   `set(CANON_VERSIONS.keys())` on every request.
6. Preserve exact behavior:
   - base is `get_canon_versions()` exact nine;
   - scoring may override only five core keys;
   - horizon and unknown scoring keys are ignored;
   - input is not mutated.

Acceptable shape:

~~~py
canon_versions = get_canon_versions()
for key, value in scoring_result.canon_versions.items():
    if key in CANON_VERSIONS:
        canon_versions[key] = str(value)
~~~

Equivalent code is allowed only if it keeps the same typed and canonical
boundary.

## 4. Correction C — use shared compatibility sets in cache guards

W2 introduced canonical compatibility constants, but
`TodayService._get_cached_payload` still duplicates them:

~~~py
{"today.v2", TODAY_V2_PAYLOAD_VERSION}
{2, V2_FRONTEND_PAYLOAD_VERSION}
~~~

Required correction in `apps/api/app/services/today_service.py`:

1. Import and use:
   - `TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS`;
   - `V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS`.
2. Replace both duplicated literal guards with membership in those shared
   canonical sets.
3. Preserve the exact cache-miss behavior and all existing tests.

Optional within the same narrow correction in `apps/api/app/schemas/today.py`:
import `TODAY_V2_PREVIOUS_PAYLOAD_VERSION` and use it instead of the two
behavioral `"today.v2"` comparisons. Do not alter the explicit `Literal[...]`
wire enum.

## 5. Exact allowed changed paths for R2

~~~text
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
~~~

No test edit is expected. No generated/fixture edit is allowed. The architect
document `79B` is read-only for the coder.

All other current W2/R1 changes remain byte-identical.

## 6. Mandatory gates

Run:

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

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_wave3_day_pipeline_reuse.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_concrete_advice.py -q

python3 scripts/grace_lint.py \
  apps/api/app/services/today_horizon_integration_service.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/app/services/today_service.py

pnpm contracts:sync
pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
npx tsc --noEmit
~~~

Expected:

~~~text
focused backend: 167 PASS
horizon regression: 242 PASS
request reuse: 15 PASS
GRACE: 3/3 PASS
focused contract Vitest: 21 PASS
compat: breakingChanges=0 overrideUsed=false
~~~

Prove generated/fixture hashes remain exact:

~~~text
openapi.json       917a04222aeeb793bd9ce6831d2ecfdcde8666663b6542ed6d1693028daba3dd
_generated.ts      e081d9dcf1ba19290c6489b52e6b01815d5e915474aab1d28569475304608a30
_generated.zod.ts  6fc7665fe0058803eef838fb9f3b84119b97695c857153d5984966666f4be78e
fixture             6100ddc601ae06a903ca038f975818b2f0ccec12e228ab2c86993f218e2bfa4c
~~~

Run root full API suite only if any behavioral test above changes unexpectedly;
otherwise the already completed root evidence remains valid:

~~~text
1243 passed, 4 skipped, exact 6 frozen failures
~~~

Static final:

~~~bash
git diff --check
git diff --cached --quiet
git status --short
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
~~~

Prove no new unused `SCORING_V2_VERSION` reference remains in
`semantic_v2_service.py`, shared compatibility sets are used by cache guards,
all new lines are <=140, exact hashes unchanged, index empty, no commit/push.

## 7. Forbidden

- no test rewrites;
- no generated/fixture changes;
- no version changes;
- no behavior changes;
- no broad import cleanup;
- no full baseline failure fixes;
- no commit/push/staging;
- no W3/B4/deploy;
- no subagents/delegation.

## 8. Exact callback

~~~text
READY_STAGE_B3_W2_R2_REVIEW
typed_semantic_boundary: PASS direct scoring_result.canon_versions; no unused scoring fallback import
compatibility_sources: PASS shared payload/frontend sets used by cache guards
new_line_lengths: PASS all added production lines <=140
focused_backend: 167 PASS
horizon_regression: 242 PASS
request_reuse: 15 PASS
grace_owned: PASS 3/3
contract_vitest: 21 PASS
contract_compat: breakingChanges=0 overrideUsed=false
generated_contract_hashes: UNCHANGED exact
fixture_hash: UNCHANGED normalized
git_diff_check: PASS
accepted_w1_sha: ecae4d0ff95bf29953fbb6957e48c38a7d22e198 local/origin unchanged
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
