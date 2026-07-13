# Stage B3.W3B — architect review R4: proven edge fixes

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Parent documents: `82`, `82A`, `82B`, `82C`
Статус: **NARROW FINAL CORRECTION — NO COMMIT/PUSH — NO RESTART**

## 1. Outcome

Fix only four independently proven R3 gaps:

1. Make command-line data can execute as a Make function;
2. malformed base URLs are not fail-closed;
3. payload validation still inspects raw versions before the typed boundary and
   catches every exception as a payload error;
4. request/main/security tests are still source-string assertions rather than
   behavior tests.

Preserve all accepted R3 behavior, the exact canonical profile, `320`-line
maximum, GRACE zero violations, and the honest official
`activation_version_mismatch` result.

Do not touch sidecar/API runtime, product code, generated contracts, fixtures,
env, systemd, dates beyond `2026-07-08`, git index, commit or push.

## 2. Proven defect A — Make expands command-line data

Independent architect check used a disposable `/tmp` sentinel and established
that the current pattern:

~~~make
PROOF_RUN_DATE := $(or $(DATE),$(PROOF_DATE))
~~~

executes a value shaped like a Make function. The sentinel was removed
immediately.

The reason is twofold:

- command-line Make variables are automatically exported unless explicitly
  unexported;
- `$(DATE)` recursively expands Make syntax before the value reaches Python.

Double shell quotes around `$${PROOF_RUN_DATE}` do not protect against the
earlier Make expansion.

### 2.1 Required safe Make pattern

Before deriving effective values, explicitly prevent automatic export:

~~~make
unexport DATE OUT TRANSPORT BASE_URL
unexport PROOF_DATE PROOF_OUT PROOF_TRANSPORT PROOF_BASE_URL
~~~

Select each alias/default using raw `$(value ...)`, never `$(DATE)` or
`$(PROOF_DATE)`:

~~~make
ifneq ($(strip $(value DATE)),)
PROOF_RUN_DATE := $(value DATE)
else
PROOF_RUN_DATE := $(value PROOF_DATE)
endif
~~~

Repeat the same exact pattern for `OUT`, `TRANSPORT`, and `BASE_URL`.

Then export only the four simple effective variables:

~~~make
export PROOF_RUN_DATE PROOF_RUN_OUT PROOF_RUN_TRANSPORT PROOF_RUN_BASE_URL
~~~

The recipe continues to use only quoted shell environment expansion:

~~~make
--date "$${PROOF_RUN_DATE}"
~~~

Required invariants:

- `DATE=2026-07-08` still overrides the default;
- an empty alias falls back to its `PROOF_*` default;
- spaces remain one argument;
- literal Make/shell syntax remains data and is not executed;
- no raw `$(DATE)`, `$(OUT)`, `$(TRANSPORT)`, or `$(BASE_URL)` appears in the
  recipe or effective-value assignment;
- exact app env flags remain unchanged.

Do not execute a destructive payload in coder tests. Use structural assertions
for `unexport`, `$(value ...)`, simple `PROOF_RUN_*` assignments, and
`$${PROOF_RUN_*}` recipe usage. The architect will perform the disposable
sentinel acceptance check.

## 3. Proven defect B — malformed URL escapes or passes

Independent calls established:

~~~text
http://[::1          -> unowned ValueError
http://localhost:bad -> accepted
~~~

Wrap URL parsing and property access:

~~~text
try:
  parsed = urlsplit(base_url)
  parsed.hostname
  parsed.port
except ValueError:
  raise ProofFailure(invalid_base_url) from None
~~~

Then apply the existing closed checks for scheme, host, credentials, query and
fragment.

Add behavior tests for at least:

- unmatched IPv6 bracket;
- non-numeric port;
- credentials;
- query;
- fragment;
- unsupported scheme;
- valid default loopback URL.

Every invalid case must produce only `invalid_base_url`, never an unowned
exception or accepted Namespace.

## 4. Typed boundary must genuinely run first

Current R3 calls raw payload/frontend checks before
`TodayPayload.model_validate` and catches every exception from Pydantic as
`payload_validation_failed`.

Required exact flow:

~~~text
try:
  payload = TodayPayload.model_validate(raw)
except pydantic.ValidationError:
  inspect only the six known raw meta identity fields
  -> exact version code if mismatched
  -> otherwise payload_validation_failed
~~~

Rules:

- import and catch `pydantic.ValidationError`, not broad `Exception`;
- an unexpected exception from `model_validate` must reach `internal_error`;
- raw inspection is allowed only inside the ValidationError branch;
- inspect all six identity fields with deterministic priority;
- never stringify raw input, exception or observed values;
- successful typed validation still performs all six exact post-checks;
- the real stale activation payload remains
  `activation_version_mismatch`.

The helper may raise the exact code or return `ProofErrorCode | None`.

Keep `validate_today_v2_payload` under its complete GRACE contract and keep the
entire script at most 320 lines. Remove the unnecessary class comment blocks or
compress private helpers if line budget is needed; do not remove validation.

## 5. Replace source-only tests with behavior tests

### 5.1 Request phase mapping

Current `test_request_phase_cases` only searches source text for four enum
names. Replace it with real async unit behavior using an in-memory fake client
or `httpx.MockTransport`:

~~~text
auth network/status failure    -> auth_failed
auth success, cookie absent    -> secure_cookie_missing
profile network/status failure -> profile_failed
day network/status failure     -> day_failed
day invalid JSON               -> day_failed
~~~

Call `request_proof` through `asyncio.run`; no external network/DB.

### 5.2 Main/output outcomes

Current main tests patch `builtins.print`, so they do not prove stdout shape.

Use `capsys` and a safe `tmp_path`, monkeypatch only external boundaries, then
call `main`. Cover:

- pass -> exit 0, exact one compact JSON line, artifact same object;
- `PipelineUnavailable` -> exit 1, exact four-key unavailable object;
- owned `ProofFailure` -> exit 1, exact four-key error object;
- unexpected exception -> exit 1, `internal_error`;
- sidecar health failure -> transport function is not called;
- output write failure -> one `invalid_out_path` JSON, no traceback.

For every case assert stderr empty and stdout contains exactly one non-empty
JSON line.

### 5.3 Recursive redaction and exact profile

The recursive scan must inspect dictionary **keys** as well as scalar values.
Assert the complete `CANON_PROFILE` dict equals the exact document `82` shape,
not only `birthCity`.

### 5.4 Shared transport boundary

Keep the scoped AST check proving each transport wrapper calls
`request_proof` exactly once.

## 6. GRACE and size

Required after the correction:

~~~text
scripts/prove_today_v2_real_api.py <= 320 lines
apps/api/tests/test_real_today_v2_api_proof.py <= 320 lines
grace_lint: 2 files clean / 0 violations
~~~

The consolidated test structure may gain parameter cases while keeping at
most six public test functions with complete six-field contracts.

## 7. Exact allowed paths

R4 may edit only:

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82D_STAGE_B3_W3B_ARCH_REVIEW_R4_PROVEN_EDGE_FIXES_TZ.md
~~~

Documents `82`, `82A`, `82B`, and `82C` remain byte-identical. SHA-256:

~~~text
82   fb638c42c096338191bb3a734f688c3b52e4e9d80ab33a9ebdd46033767aab91
82A  e0c25f38472385668898d0a5d474437f6b17cb0640ce224cc2bb880d92ba93f0
82B  ba0d355215d01ab7512c09a5ca54f56d34f7370f02340734f88c10bf0ce87ee5
82C  648fff3cbb6735ae0aff0d0ac534526c6b141373146a335ec4f8eb38b8274736
~~~

Complete relevant W3B worktree after R4: eight paths (`Makefile`, script,
test, and documents `82` through `82D`).

## 8. Forbidden

- no service restart/reload or systemd/env change;
- no product/backend/frontend/generated/fixture change;
- no raw response/log capture or inline date loop;
- no additional date after identity error;
- no direct DB/ORM access;
- no git add/commit/push;
- no next wave/B4/deploy;
- no subagents/delegation;
- never touch frozen unrelated paths.

## 9. Gates

Run from repository root after final edits:

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
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82C_STAGE_B3_W3B_ARCH_REVIEW_R3_FINAL_PROOF_HARDENING_TZ.md

git diff --check
git diff --cached --quiet
~~~

## 10. Official proof

After all gates, remove only the old redacted artifact and run exactly once:

~~~bash
rm -f /tmp/solarsage-v2-real-api-proof.json
make prove-today-v2-real \
  DATE=2026-07-08 \
  OUT=/tmp/solarsage-v2-real-api-proof.json
~~~

Expected outcome remains:

~~~json
{"schemaVersion":"today-v2-real-api-proof.v1","status":"error","date":"2026-07-08","code":"activation_version_mismatch"}
~~~

Do not run the disposable Make sentinel yourself. The architect owns that
acceptance check after callback.

## 11. Exact callback

~~~text
BLOCKED_STAGE_B3_W3B_RUNTIME_IDENTITY_R4_ACCEPTANCE
accepted_date: NONE
official_date: 2026-07-08
official_status: error
official_code: activation_version_mismatch
date_scan_after_identity_error: NOT_RUN
make_raw_value_boundary: PASS unexport + value + quoted env transport
url_validation: PASS malformed IPv6/port and closed matrix
typed_validation_order: PASS model_validate first; ValidationError-only mapping
request_phase_behavior: PASS async behavior tests, no source-only substitute
main_output_behavior: PASS capsys one-line matrix; health fail stops transport
canonical_profile: PASS exact document 82 dict
recursive_redaction: PASS keys, values, all raw activation IDs
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
documents_82_82A_82B_82C: HASHES UNCHANGED
services: api=active unchanged; sidecar=active unchanged
runtime_evidence: loaded sidecar predates current shared contract
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
r4_touched_paths: 4 EXACT_ALLOWLIST
w3b_relevant_paths: 8 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback. Do not restart services or begin another wave.
