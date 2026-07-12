# Stage B3.W3B — architect review R5: behavior-test completion

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Parent documents: `82`–`82D`
Статус: **TEST-FOCUSED FINAL CLEANUP — NO COMMIT/PUSH/RESTART**

## 1. Accepted implementation facts

Architect independently confirmed:

~~~text
Make disposable sentinel: SAFE, command-line Make syntax not executed
malformed IPv6: invalid_base_url
non-numeric port: invalid_base_url
auth failure: auth_failed
missing cookie: secure_cookie_missing
profile failure: profile_failed
day status failure: day_failed
day invalid JSON: day_failed
~~~

The proof implementation behavior is accepted except for one narrow fallback
completion in section 2.

The R4 callback is not yet accepted because
`test_request_phase_cases` still only searches source strings. Imported
`MockTransport`, `AsyncClient`, `asyncio`, and related test tools are unused.

Close test coverage truthfully. Do not redesign the proof, Make target or
runtime.

## 2. Complete six-field ValidationError fallback

`_raw_version_code` currently checks only payload/frontend. Document `82D`
requires deterministic fallback over all six identity fields when Pydantic
rejects the payload for any reason.

Inside the existing `ValidationError` branch, the private helper must inspect:

~~~text
calculationVersion       -> calculation_version_mismatch
activationLayerVersion   -> activation_version_mismatch
scoringVersion           -> scoring_version_mismatch
payloadVersion           -> payload_version_mismatch
frontendPayloadVersion   -> frontend_version_mismatch
contentVersion           -> content_version_mismatch
~~~

Use exact constants from `app.core.versions`; never emit observed values.
Keep `TodayPayload.model_validate(raw)` as the first validation attempt and
catch only `pydantic.ValidationError`.

Add a regression where another Pydantic-invalid field and one of the four
non-payload identity fields are both wrong; the exact version code must win.

The script remains `<=320` and GRACE-clean. Remove non-required class comment
lines or compress private code if necessary; do not remove behavior.

## 3. Real request-phase unit behavior

Replace the body of `test_request_phase_cases` completely. It must no longer
read/search the source file for enum names.

Use `httpx.MockTransport` with `AsyncClient(base_url="https://127.0.0.1")`, or
an equivalent in-memory async fake, and call:

~~~python
asyncio.run(request_proof(client, "asgi", "2026-07-08"))
~~~

Parameterize and assert exact `ProofFailure.code` for:

~~~text
auth HTTP failure       -> auth_failed
auth success/no cookie  -> secure_cookie_missing
profile HTTP failure    -> profile_failed
day HTTP failure        -> day_failed
day invalid JSON        -> day_failed
~~~

For auth-success cases, return a normal Secure cookie named from the current
contract (`grace_session_v2`) without inspecting its value in product code.

No external network, DB or real route is used by this unit test.

## 4. Main/output behavior matrix completion

Keep the existing capsys test and add the missing cases:

- unexpected exception from the transport -> exact `internal_error` object;
- output write `OSError` -> exactly one stdout JSON line with
  `invalid_out_path`, stderr empty, no traceback;
- sidecar health failure assertion also checks exact one stdout line and empty
  stderr.

Do not patch `builtins.print`. It is acceptable to patch `Path.write_text` only
to raise `OSError` for the write-failure case.

For pass/unavailable/owned-error/internal-error assert exact top-level key
sets, not only `status`.

## 5. Exact profile and recursive scan

Replace the three partial profile assertions with one exact dictionary equality
against the complete document `82` canonical profile.

Keep recursive scanning of both dictionary keys and scalar values. Fix key
normalization so comparisons are case-insensitive on both sides (for example,
compare `pattern.casefold()` to `key.casefold()`).

Keep the all-activation-ID absence check.

## 6. Make test

Keep source assertions, but scope them to the real proof block and require all
of:

~~~text
unexport DATE OUT TRANSPORT BASE_URL
unexport PROOF_DATE PROOF_OUT PROOF_TRANSPORT PROOF_BASE_URL
$(value DATE), $(value OUT), $(value TRANSPORT), $(value BASE_URL)
$${PROOF_RUN_DATE}, $${PROOF_RUN_OUT},
$${PROOF_RUN_TRANSPORT}, $${PROOF_RUN_BASE_URL}
~~~

Do not execute the disposable sentinel; architect already accepted it.

## 7. Exact allowed paths

Edit only:

~~~text
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82E_STAGE_B3_W3B_ARCH_REVIEW_R5_BEHAVIOR_TEST_COMPLETION_TZ.md
~~~

`Makefile` and documents `82`–`82D` remain byte-identical.

No product/generated/fixture/env/systemd/service/date/git changes. No
subagents/delegation.

## 8. Gates

~~~bash
wc -l scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_real_today_v2_api_proof.py -q

apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

python3 scripts/grace_lint.py \
  scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
npx tsc --noEmit

git diff --check
git diff --cached --quiet
~~~

Then run the official `2026-07-08` proof exactly once. Expected closed result
remains `activation_version_mismatch`; do not scan another date.

## 9. Exact callback

~~~text
BLOCKED_STAGE_B3_W3B_RUNTIME_IDENTITY_R5_ACCEPTANCE
accepted_date: NONE
official_code: activation_version_mismatch
date_scan_after_identity_error: NOT_RUN
six_field_fallback: PASS all six identities under ValidationError
request_phase_behavior: PASS 5 real in-memory async cases
main_output_matrix: PASS pass/unavailable/owned/internal/write/health
canonical_profile: PASS exact full dict
recursive_redaction: PASS normalized keys/values and all raw IDs
make_boundary: UNCHANGED architect sentinel SAFE
script_size: <n>/320 PASS
test_size: <n>/320 PASS
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
grace_lint: 2 files, 0 violations PASS
contract_vitest: 21 PASS
typecheck: PASS
real_artifact: /tmp/solarsage-v2-real-api-proof.json REDACTED ERROR ONLY
services: api=active unchanged; sidecar=active unchanged
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
r5_touched_paths: 3 EXACT_ALLOWLIST
w3b_relevant_paths: 9 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.

## 10. Acceptance addendum — physical line limit

The first R5 callback reported:

~~~text
script_size: 321/320 PASS
~~~

This is a failed gate, not a pass.

Perform one mechanical no-behavior-change cleanup so the script is at most 320
physical lines. Prefer removing a blank line or joining an already compact
private statement. Do not change logic, tests, Makefile, runtime or artifact.

After that run only:

~~~bash
wc -l scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_real_today_v2_api_proof.py -q
python3 scripts/grace_lint.py \
  scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py
git diff --check
git diff --cached --quiet
~~~

Return the same section 9 callback with the truthful corrected line count and
stop. Do not rerun the full API suite or official proof for a physical-line-only
cleanup; retain their already accepted R5 results.
