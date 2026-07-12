# Stage B3.W3B — architect review R3: final proof hardening

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Parent documents: `82`, `82A`, `82B`
Статус: **FINAL CORRECTIONS — NO COMMIT/PUSH — NO SERVICE RESTART**

## 1. Outcome

Keep the honest R2 runtime result (`activation_version_mismatch`) and perform
one final narrow hardening pass on the proof utility and its tests.

R2 correctly established that the loaded sidecar is stale and did not weaken
the version gate. That architectural result is accepted.

The R2 implementation itself is not yet accepted because independent review
found concrete contract/test defects:

1. canonical profile text was changed from `Moscow, Russia` to `Moscow`;
2. payload/frontend version mismatches are hidden as
   `payload_validation_failed`;
3. `auth_failed`, `profile_failed`, and `day_failed` exist but are never used;
4. output-file write failures can still escape with a traceback;
5. several tests only search for source substrings and can pass without the
   required behavior;
6. the declared GRACE gate actually fails with 44 violations;
7. Make double-quoting does not safely preserve arbitrary command-line values
   containing shell syntax.

Close exactly these issues. Do not restart the sidecar, change product code,
scan additional dates, commit or push.

## 2. Preserve accepted R2 behavior

Do not regress any of the following:

- exact activation identity is enforced;
- sidecar health runs before auth/profile/day;
- honest typed pipeline unavailable is distinct from `error`;
- ASGI app stdout/stderr is suppressed at OS descriptor level and restored;
- cookie value is never read or copied;
- both transports share `request_proof`;
- artifact contains only allowlisted pass/unavailable/error shapes;
- official `2026-07-08` result is a sanitized
  `activation_version_mismatch` error;
- no additional date scan after an identity error;
- script and test stay at most 320 physical lines each.

## 3. Restore the exact canonical dev profile

The profile must be byte-for-field equivalent to document `82`:

~~~json
{
  "firstName": "Dev",
  "gender": "female",
  "birth": {
    "birthday": "1990-01-01",
    "birthTime": "12:00:00",
    "birthCity": "Moscow, Russia",
    "birthLat": 55.7558,
    "birthLon": 37.6173,
    "birthTz": "Europe/Moscow"
  },
  "currentLocation": {
    "city": "Moscow, Russia",
    "lat": 55.7558,
    "lon": 37.6173,
    "tz": "Europe/Moscow"
  }
}
~~~

Do not alter profile content to make a redaction test easier. Redaction tests
inspect the produced outcome, not the source constant.

Add an exact unit assertion for this profile shape without printing it on
failure/callback.

## 4. Preserve exact version error codes across Pydantic rejection

The required six-way version classification is:

~~~text
calculationVersion       -> calculation_version_mismatch
activationLayerVersion   -> activation_version_mismatch
scoringVersion           -> scoring_version_mismatch
payloadVersion           -> payload_version_mismatch
frontendPayloadVersion   -> frontend_version_mismatch
contentVersion           -> content_version_mismatch
~~~

`TodayPayload.model_validate` must remain the first typed validation attempt.
However, Pydantic may reject an incompatible payload/frontend pair before the
post-validation exact checks run.

Accepted fail-closed pattern:

1. call `TodayPayload.model_validate(raw)`;
2. catch only Pydantic `ValidationError` for this boundary;
3. inspect only the six known `raw["meta"]` identity fields through a small
   private helper;
4. if one differs from the exact current constant, raise its closed
   `ProofErrorCode` without including observed/expected values;
5. otherwise raise `payload_validation_failed`;
6. non-Pydantic unexpected exceptions are not silently relabeled as a payload
   validation failure; they reach the owned `internal_error` boundary.

The helper must tolerate non-dict/missing raw data and never stringify or
serialize the raw payload.

Update the parameterized test so all six fields expect their exact code.

## 5. Map each HTTP phase to its owned closed error

Current `request_proof` calls `raise_for_status()` directly. An auth/profile/day
failure therefore falls into generic `internal_error`, leaving three declared
codes dead.

Use one small private request helper or explicit phase wrappers. Required
mapping:

~~~text
POST /api/auth/dev       network/status failure -> auth_failed
missing named cookie                           -> secure_cookie_missing
PUT /api/profile         network/status failure -> profile_failed
GET /api/day/<date>      network/status failure -> day_failed
invalid/non-JSON day body                      -> day_failed
typed JSON contract failure                    -> version/payload/audit/... code
~~~

Never inspect, print or retain response bodies in error objects.

Catch the relevant `httpx` transport/status/JSON exceptions, then raise the
closed phase code `from None` so no chained traceback/body appears.

Unit-test all three HTTP phases with an in-memory fake or `httpx.MockTransport`.
No external network or DB I/O in unit tests.

## 6. Make CLI parsing fully fail-closed

Keep existing date/out/base URL validation and close these edges:

- `out.parent` must both exist and be a directory;
- malformed IPv6/port/URL parser exceptions become `invalid_base_url`;
- invalid transport/unknown/missing CLI arguments do not let argparse print a
  usage dump or user-supplied URL;
- add closed `invalid_cli` and/or `invalid_transport` codes as needed;
- `--help` may retain normal successful help behavior;
- never echo an invalid URL, OUT value or exception message.

A custom `ArgumentParser.error()` that raises a closed `ProofFailure`, or an
equivalent `exit_on_error=False` design, is acceptable.

## 7. Output writing must never create a second traceback

Current success writes inside `try`, but the error path writes again outside
the guarded block. If `OUT` is unwritable, the second write can escape and
print a traceback.

Create one private final emitter/writer boundary:

~~~text
emit_outcome(out_path, outcome, desired_exit_code) -> actual_exit_code
~~~

Required behavior:

- serialize only the already-redacted outcome;
- attempt the file write once;
- on `OSError`, replace the printed outcome with sanitized
  `status=error/code=invalid_out_path`;
- do not retry the same failed path;
- still print exactly one compact JSON object to stdout;
- emit no traceback and return non-zero;
- no raw/intermediate file is created.

Unit-test the write-failure path by monkeypatching `Path.write_text` or using a
safe temporary unwritable target. Do not touch repository files.

## 8. Strengthen behavior tests; remove source-substring false positives

The following R2 tests are insufficient and must be replaced:

### 8.1 Common request boundary

`src.count("request_proof(") >= 2` counts the function definition and would
still pass if one transport stopped using the boundary.

Use AST inspection scoped separately to `run_asgi_proof` and
`run_http_proof`, or injected-call tests, and prove each contains exactly one
call to `request_proof`.

### 8.2 Main compact JSON output

Searching for `print(json.dumps(out` does not execute behavior.

Monkeypatch real I/O boundaries, call `main`, and capture stdout/stderr. Prove:

- exactly one non-empty stdout line;
- it parses as JSON;
- exact closed keys for the selected outcome;
- stderr is empty;
- no traceback, UUID, profile/cookie/copy/raw activation material.

Cover at least pass, unavailable, owned error and unexpected internal error.

### 8.3 Sidecar fail-closed

`_outcome("pass")` not containing `sidecarHealth` does not prove the real flow
stops when health fails.

Monkeypatch `check_sidecar_health` to fail and prove neither transport/auth nor
profile/day boundary is called, result is non-zero closed
`sidecar_unhealthy`, and no pass artifact is emitted.

### 8.4 Make recipe guard

Inspect the actual `prove-today-v2-real` recipe block. Do not fall back to
accepting any unrelated `\t@` recipe elsewhere in the Makefile.

### 8.5 Recursive redaction

Keep the complete all-activation-ID check. Replace the nominal recursive test
with an actual recursive walk over dict keys/list values/scalar strings, or an
equivalent exact allowlist assertion plus recursive scalar scan.

## 9. Safely transport Make command-line values

Current recipe uses Make interpolation inside shell double quotes:

~~~text
--out "$(OUT)"
~~~

That preserves spaces but can still allow Make/shell metacharacter evaluation.

Pass effective values through exported environment variables whose contents
are expanded by the shell only as quoted variable values, not inserted into
the shell program text. One acceptable design:

~~~make
PROOF_RUN_DATE := ... value/default selection using $(value ...)
PROOF_RUN_OUT := ...
PROOF_RUN_TRANSPORT := ...
PROOF_RUN_BASE_URL := ...

export PROOF_RUN_DATE PROOF_RUN_OUT PROOF_RUN_TRANSPORT PROOF_RUN_BASE_URL

prove-today-v2-real:
	@APP_ENV=development ... \
	python ... \
		--transport "$${PROOF_RUN_TRANSPORT}" \
		--base-url "$${PROOF_RUN_BASE_URL}" \
		--date "$${PROOF_RUN_DATE}" \
		--out "$${PROOF_RUN_OUT}"
~~~

Equivalent safe transport is allowed. Requirements:

- user overrides `DATE/OUT/TRANSPORT/BASE_URL` still work;
- documented defaults still work;
- empty aliases fall back to defaults;
- no raw Make value is interpolated into shell command syntax;
- values containing spaces or literal `$()` reach the Python parser as data
  and are never executed;
- exact process-local app flags remain unchanged.

Add a non-executing Make/source test for this boundary. Do not run a malicious
command as a test; assert the recipe structure instead.

## 10. GRACE must actually pass

Independent command result on R2:

~~~text
python3 scripts/grace_lint.py \
  scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

FAIL — 44 violations
~~~

The callback claim `3/3 PASS (production files)` is not accepted because the
specified command was run against the two new files and returned non-zero.

Required final result:

~~~text
grace_lint: PASS — 2 file(s), 0 violation(s)
~~~

### 10.1 Script strategy

Add complete six-field function contracts to every non-private public
function, or rename genuinely internal helpers with `_` so the public surface
matches the module map.

Every function contract contains exactly the required fields:

~~~text
purpose
inputs
returns
side_effects
emitted_logs
error_behavior
~~~

Keep the script at most 320 lines by tightening formatting, not removing
behavior.

### 10.2 Test strategy

Do not add a seven-line contract to each of 38 separate test methods and exceed
the line limit.

Consolidate cases into at most six public parameterized pytest functions, for
example:

~~~text
test_validation_cases
test_request_phase_cases
test_redaction_cases
test_cli_and_output_cases
test_source_contract_cases
test_health_and_main_cases
~~~

Private helpers may prepare mutations/assertions. Each public test function
gets one complete function contract. Pytest may still collect 30+ parameter
cases; callback reports the actual collected count.

The test file must remain at most 320 physical lines and preserve all required
coverage from `82A`, `82B`, and this document.

## 11. Canonical stdout/stderr interpretation

The Python proof process itself must emit:

~~~text
stdout: exactly one compact sanitized JSON line
stderr: empty
~~~

For a non-zero recipe, GNU Make may append its own generic non-sensitive
`make: *** ... Error 1` line to Make's stderr. This Make-owned line is not an
application/privacy leak and does not need an unsafe workaround.

Acceptance still requires:

- no ASGI/API log line;
- no UUID/user/profile/cookie/token/copy/raw activation ID;
- no Python traceback or exception text;
- Make stdout itself contains exactly the one sanitized JSON line.

Do not weaken the script exit code merely to suppress GNU Make's own status
line.

## 12. Exact allowed paths

R3 may edit only:

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82C_STAGE_B3_W3B_ARCH_REVIEW_R3_FINAL_PROOF_HARDENING_TZ.md
~~~

Documents `82`, `82A`, and `82B` remain byte-identical. Architect SHA-256
baselines:

~~~text
82   fb638c42c096338191bb3a734f688c3b52e4e9d80ab33a9ebdd46033767aab91
82A  e0c25f38472385668898d0a5d474437f6b17cb0640ce224cc2bb880d92ba93f0
82B  ba0d355215d01ab7512c09a5ca54f56d34f7370f02340734f88c10bf0ce87ee5
~~~

The complete relevant W3B worktree after R3 consists of seven paths:

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82_STAGE_B3_W3B_REAL_DEV_AUTH_API_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82A_STAGE_B3_W3B_ARCH_REVIEW_R1_PRIVACY_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82C_STAGE_B3_W3B_ARCH_REVIEW_R3_FINAL_PROOF_HARDENING_TZ.md
~~~

No product API/sidecar/frontend/generated/fixture/env/systemd file may change.

## 13. Forbidden

- no sidecar/API restart or daemon-reload;
- no product/runtime/canon/threshold change;
- no raw response/log capture or inline date probe;
- no date scan after identity error;
- no direct DB/ORM access from the proof;
- no dependency override/fixture query in real proof;
- no stage, commit or push;
- no B4/frontend/deploy work;
- no subagents/delegation;
- never touch frozen unrelated paths.

## 14. Gates

Run from repository root:

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

sha256sum \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82_STAGE_B3_W3B_REAL_DEV_AUTH_API_PROOF_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82A_STAGE_B3_W3B_ARCH_REVIEW_R1_PRIVACY_PROOF_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md

git diff --check
git diff --cached --quiet
~~~

Required:

~~~text
script <=320
test <=320
proof unit PASS with all required cases
full API 0 failures
GRACE 2 files / 0 violations
contract fixture/check PASS
contract Vitest 21 PASS
typecheck PASS
82/82A/82B hashes exact
index empty
services unchanged
~~~

## 15. Final official proof

Remove only the existing redacted artifact, then run exactly once:

~~~bash
rm -f /tmp/solarsage-v2-real-api-proof.json
make prove-today-v2-real \
  DATE=2026-07-08 \
  OUT=/tmp/solarsage-v2-real-api-proof.json
~~~

Expected current environment result:

~~~json
{"schemaVersion":"today-v2-real-api-proof.v1","status":"error","date":"2026-07-08","code":"activation_version_mismatch"}
~~~

Verify structurally only:

- Make stdout has exactly that one JSON line;
- any Make stderr is only GNU Make's generic non-zero status line;
- artifact has exactly `schemaVersion,status,date,code`;
- no app logs, UUID, profile/cookie/copy/raw IDs or Python traceback;
- exit is non-zero;
- no second date is run.

If the environment unexpectedly converges and result changes, follow the
truthful outcome procedure from `82B`; never weaken validation.

## 16. Exact callback for the expected stale runtime

~~~text
BLOCKED_STAGE_B3_W3B_RUNTIME_IDENTITY_R3_ACCEPTANCE
accepted_date: NONE
official_date: 2026-07-08
official_status: error
official_code: activation_version_mismatch
date_scan_after_identity_error: NOT_RUN
canonical_profile: PASS exact document 82 shape
six_version_codes: PASS exact field-specific mapping
request_phase_codes: PASS auth/profile/day mapped and tested
outcome_writer: PASS single compact output; write failure fail-closed
make_value_transport: PASS values passed as data, not shell syntax
script_size: <n>/320 PASS
test_size: <n>/320 PASS
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
grace_lint: 2 files, 0 violations PASS
contract_vitest: 21 PASS
typecheck: PASS
stdout_redaction: PASS one compact JSON; no ASGI/API logs
stderr_redaction: PASS no Python/app output; GNU Make status only
raw_payload_artifacts: ZERO
raw_activation_ids: ZERO
real_artifact: /tmp/solarsage-v2-real-api-proof.json REDACTED ERROR ONLY
documents_82_82A_82B: HASHES UNCHANGED
services: api=active unchanged; sidecar=active unchanged
runtime_evidence: loaded sidecar predates current shared contract
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
r3_touched_paths: 4 EXACT_ALLOWLIST
w3b_relevant_paths: 7 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback. Do not restart the service or begin the next wave.
