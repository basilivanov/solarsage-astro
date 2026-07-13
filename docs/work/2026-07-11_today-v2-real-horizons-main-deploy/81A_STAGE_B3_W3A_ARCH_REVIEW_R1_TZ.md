# Stage B3.W3A — architect review R1 corrections

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `9e1c6c0af9103e73e56d65644642d5c075fba3a3`
Parent implementation document: `81`
Статус: **NARROW CORRECTIONS — NO COMMIT/PUSH**

## 1. Review verdict

The main implementation is directionally accepted:

- full API is green: `1258 passed, 4 skipped, 0 failed`;
- former six failures pass;
- resolver is frozen and correctly maps V1/V2 constants;
- Today, Calendar and expected-cache paths call the resolver;
- generated contracts and fixture remain unchanged.

Before acceptance, correct the following narrow proof/source-of-truth gaps.

## 2. Resolver must drive every field it owns

`TodayRuntimeIdentity` owns `content_version`, but all three cache-key calls
still rely on the default argument of `build_today_cache_key` instead of the
resolved identity.

Pass explicitly:

~~~py
content_version=identity.content_version
~~~

in:

1. `expected_cache_identity`;
2. `TodayService.get_today_payload` write-key construction;
3. `CalendarService._compute_and_cache_day_status` write-key construction.

Update V1/V2 read/write parity tests so their explicit write-key construction
also passes `content_version=identity.content_version`. The tests must fail if
the resolver's content field and cache key diverge.

No hash field or version value changes.

## 3. Do not select the family twice in TodayService

TodayService currently calls the resolver, then separately repeats:

~~~py
str(dual.selected_scoring_version) == str(SCORING_V2_VERSION)
~~~

Derive the branch from the returned canonical identity instead:

~~~py
v2_selected = identity.payload_version == TODAY_V2_PAYLOAD_VERSION
~~~

Remove the now-unused `SCORING_V2_VERSION` import from TodayService if it has no
other use. The selected scoring version still enters the resolver exactly once;
the resolver remains the only family map.

## 4. Remove the newly exposed unused Calendar selection read

Within `CalendarService._compute_and_cache_day_status`, remove the unused local
`sel_ver` and remove `selected_scoring_version_for_flags` from that method's
local import. The read path in `_get_cached_day_status` still legitimately uses
`selected_scoring_version_for_flags` through current cache identity and must
remain unchanged.

Do not perform broad cleanup outside this exact dead local.

## 5. Make claimed flag tests real

In `TestRuntimeIdentityResolver`:

### 5.1 Frontend flag test

`test_frontend_flag_does_not_alter_v1_identity` must actually set:

~~~py
settings.solarsage_v2_enabled = False
settings.solarsage_v2_frontend_enabled = True
~~~

Then assert the expected read identity and resolver identity are the exact V1
family, including payload-equivalent fields available at each boundary.

### 5.2 Dual-run test

`test_dual_run_does_not_alter_v1_identity` must accept `monkeypatch`, set:

~~~py
settings.solarsage_v2_enabled = False
settings.solarsage_v2_dual_run = True
~~~

Build `expected_cache_identity` and compare it with a V1 resolver-derived
write key, including exact hash equality. A comment that the pure resolver
ignores dual-run is not a substitute for setting and proving the runtime flags.

### 5.3 Runtime identity type

The test imports `TodayRuntimeIdentity`; use it in a real
`isinstance(identity, TodayRuntimeIdentity)` assertion or remove the unused
import. Prefer the assertion in the immutability test.

## 6. Complete Today payload version assertions

In the V2 selected test add:

~~~py
assert payload.meta.scoring_version == SCORING_V2_VERSION
~~~

In the disabled/V1 test add assertions using constants for:

- `payload.meta.scoring_version == LEGACY_SCORING_VERSION`;
- `payload.meta.payload_version == TODAY_V1_PAYLOAD_VERSION`;
- `payload.meta.frontend_payload_version == LEGACY_FRONTEND_PAYLOAD_VERSION`;
- `payload.meta.content_version == TODAY_CONTENT_VERSION`.

Import the two missing V1 identity constants. Remove literal identity assertions
and keep the existing honest null-body assertion.

## 7. GRACE ownership updates

Update the material ownership contracts, not only executable code:

### CalendarService

- add `M-CACHE-KEY-SERVICE` to dependencies;
- add invariant that semantic-cache write identity and pre-read expected
  identity derive from the same selected scoring family resolver.

### TodayService

- add `M-CACHE-KEY-SERVICE` to dependencies;
- add invariant that the same resolved runtime identity drives both cache key
  and public meta version fields.

Do not invent new log events.

## 8. Exact allowed paths

~~~text
apps/api/app/services/cache_key_service.py
apps/api/app/services/calendar_service.py
apps/api/app/services/today_service.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_today_v2_payload.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/81A_STAGE_B3_W3A_ARCH_REVIEW_R1_TZ.md
~~~

`test_semantic_v2_service.py` remains byte-identical in R1. All other current
W3A changes remain byte-identical.

## 9. Gates

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_v2_payload.py \
  apps/api/tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row -q

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_calendar_endpoints.py \
  apps/api/tests/test_semantic_v2_service.py \
  apps/api/tests/test_today_v2_payload.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_today_horizon_integration_service.py \
  apps/api/tests/test_today_horizons_contract.py -q

apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

python3 scripts/grace_lint.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/app/services/calendar_service.py \
  apps/api/app/services/today_service.py

npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
npx tsc --noEmit

git diff --check
git diff --cached --quiet
git status --short
~~~

Required:

~~~text
targeted identity/payload/calendar: PASS
focused backend: PASS
full API: 0 failed
GRACE: 3/3 PASS
contract Vitest: 21 PASS
typecheck: PASS
generated/fixture: unchanged
index: empty
~~~

## 10. Forbidden

- no public schema/generated/fixture/version changes;
- no resolver field removal;
- no feature semantics change;
- no real API/W3B/frontend/deploy;
- no edits outside section 8;
- no commit/push/staging;
- no subagents/delegation.

## 11. Exact callback

~~~text
READY_STAGE_B3_W3A_R1_REVIEW
resolver_owned_fields: PASS content included explicitly in all three cache keys
single_family_selection: PASS Today branches from resolved identity
calendar_dead_local: REMOVED
flag_proofs: PASS frontend=true and dual_run=true exercised under V1 selection
today_meta_family: PASS current V2 and legacy V1 exact constants
grace_ownership: PASS Today/Calendar cache resolver invariants documented
targeted: <count> PASS
focused_backend: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
grace: PASS 3/3
contract_vitest: 21 PASS
typecheck: PASS
generated_fixture: UNCHANGED
git_diff_check: PASS
parent_sha: 9e1c6c0af9103e73e56d65644642d5c075fba3a3 local/origin unchanged
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
