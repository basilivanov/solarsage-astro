# Stage B3.W3B — architect review R2: fail-closed proof and truthful runtime identity

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Parent documents: `82`, `82A`
Статус: **CORRECTIONS — NO COMMIT/PUSH — NO SERVICE RESTART**

## 1. Outcome

Correct only the W3B proof utility so it is privacy-safe, fail-closed and
truthful about the currently loaded runtime.

This R2 does **not** accept the current callback. A successful unit/full-suite
run is not enough while the proof utility can:

- skip the activation-layer identity check;
- call a success artifact valid when sidecar health is false;
- turn any validation/HTTP/runtime error into a fake pipeline `unavailable`;
- leak in-process API logs to proof stdout;
- claim a common request boundary which does not exist;
- report `exact_versions: PASS` while also reporting `al-1.0 vs al-1.1`.

After R2, the official command must have exactly one of two honest outcomes:

1. `pass` with a fully validated built triple and all six exact identities; or
2. non-zero sanitized `error`/`unavailable`, with no raw response or runtime
   exception text.

Do not restart or modify `solarsage-sidecar.service` in this wave. If the
loaded sidecar is stale, stop with the exact blocked callback in section 15.

## 2. Architect findings that must be closed

Current file references are from the 197-line implementation reviewed on
2026-07-12.

### 2.1 Activation identity is not validated

`scripts/prove_today_v2_real_api.py:58-64` validates five identities and then
explicitly exempts `activation_layer_version`.

This violates documents `82` and `82A`. Require exact equality with
`ACTIVATION_LAYER_VERSION`, currently `al-1.1`.

There is no environment exception and no compatibility fallback in this
proof. A different value is `activation_version_mismatch`, never
`unavailable` and never `pass`.

### 2.2 Sidecar health is checked after the day response and is not enforced

Current `_validate_and_redact` calls `check_sidecar_health()` only after the
payload has already been requested and validated. `build_redacted_proof` can
then emit `status=pass` with `sidecarHealth=fail`.

Required order:

~~~text
parse/validate CLI
-> real sidecar 18091 health preflight
-> auth
-> assert cookie presence without reading value
-> profile PUT
-> day GET
-> typed payload validation
-> redaction
-> one sanitized output
~~~

An unhealthy/unreachable/malformed health response must stop before auth and
emit only `sidecar_unhealthy`.

A success artifact can only contain `sidecarHealth: "pass"`. Remove the
accepted code path and test that produce a successful artifact with `fail`.

### 2.3 Every exception is incorrectly classified as unavailable

Current `main` catches `Exception`, parses `str(exc)` and emits
`status=unavailable`. This already hid a calculation-version mismatch as an
unavailable result.

Delete all exception-string parsing. In particular, the accepted source must
not contain logic equivalent to:

~~~text
str(exc)
repr(exc)
"pipeline status" in error_text
searching missing_long/missing_medium/... inside exception text
printing exception type or message
~~~

Use two compact typed outcomes/exceptions:

~~~text
PipelineUnavailable(reason: TodayV2UnavailableHorizonSelectionReason)
ProofFailure(code: ProofErrorCode)
~~~

`PipelineUnavailable` may be created only after `TodayPayload.model_validate`
returns a typed payload whose audit contains
`TodayV2HorizonPipelineAuditUnavailable`. Copy the already-validated typed
`reason` field directly. Do not rediscover it from text.

All other failures are `status=error`, never `unavailable`.

### 2.4 The common request boundary is missing

The module map advertises `request_proof`, but no such function exists.
`run_asgi_proof` and `run_http_proof` duplicate auth/profile/day logic.

Provide one actual shared boundary, preferably async:

~~~text
request_proof(client, transport, date)
  -> POST /api/auth/dev
  -> assert named cookie exists, value never read
  -> PUT /api/profile
  -> GET /api/day/<date>
  -> validate_today_v2_payload
  -> build_redacted_proof
~~~

Both transport wrappers must create their client and call this boundary
exactly once. No separate success logic by transport.

### 2.5 ASGI proof stdout is not privacy-clean

The current in-process request lets API structured logs and legacy auth debug
prints reach proof stdout. During review it emitted request logs containing a
dev user UUID. Even though that is the dedicated dev identity, document `82`
forbids UUID/user/session material anywhere in proof stdout.

For ASGI mode, silence in-process application stdout and stderr at the OS file
descriptor level only while importing/executing the app request path. A plain
`contextlib.redirect_stdout` is insufficient because
`app.core.logging._stdout` owns file descriptor 1 directly.

Accepted pattern:

- save descriptors with `os.dup`;
- point descriptors 1 and 2 to `/dev/null` with `os.dup2` for app import and
  request execution;
- always restore them in `finally`;
- never save suppressed output to a file, pipe, string or artifact;
- print the final sanitized outcome only after restoration.

Do not silence the proof's own final output. Do not create a raw log artifact.

Make must not echo the command before the proof JSON. Prefix the recipe command
with `@` so a successful or failed target emits only the script's compact
sanitized JSON on stdout and nothing sensitive on stderr.

### 2.6 Cookie contract is incomplete

ASGI transport must continue using:

~~~text
ASGITransport(app=app, client=("127.0.0.1", ephemeral_port))
base_url="https://127.0.0.1:8000"
~~~

After auth, import the configured `settings.session_cookie_name` and assert
only:

~~~text
settings.session_cookie_name in client.cookies
~~~

Never call `.get`, index the jar, iterate values, print length/value or build a
raw `Cookie` header.

For `--transport http`, reject an `http://` base URL under the current secure
cookie policy with sanitized code `secure_cookie_requires_https`. Do not copy
the Secure cookie manually. An `https://` HTTP-mode URL may proceed normally.

### 2.7 CLI validation is incomplete

Keep date canonicalization through `date.fromisoformat`, and additionally:

- canonical output date is `parsed_date.isoformat()`;
- reject `OUT` when it is an existing directory;
- reject an empty filename or a parent that is not an existing directory;
- do not create directories from the proof script;
- parse `BASE_URL` structurally with `urllib.parse.urlsplit`;
- allow only `http` or `https` schemes, a non-empty host, no credentials, no
  query and no fragment;
- never echo a rejected URL because it could contain credentials;
- ASGI still uses its fixed in-process HTTPS base and does not allocate a
  listener.

CLI/config failures must be sanitized and occur before network or profile I/O.

### 2.8 Current tests assert several wrong behaviors

Replace these false-positive tests/guards:

- `test_sidecar_health_passthrough` currently accepts success + health `fail`;
- `test_all_six_versions` checks a valid fixture but never mutates activation;
- `test_no_raw_activation_ids` repeatedly checks only the first long ID;
- `test_forbidden_values` checks only four strings and is not recursive;
- `test_transport_share_boundary` only searches for a helper name and does
  not prove both transports use the same request function;
- no test distinguishes typed pipeline unavailable from version/HTTP/Pydantic
  failures;
- no test proves stdout is one sanitized JSON object with in-process API noise
  suppressed;
- no test proves cookie presence without value extraction.

## 3. Closed outcome schema

Success remains exactly the redacted schema from document `82`.

Honest selection unavailability remains:

~~~json
{
  "schemaVersion": "today-v2-real-api-proof.v1",
  "status": "unavailable",
  "date": "YYYY-MM-DD",
  "reason": "missing_long"
}
~~~

The reason must be one of the typed closed reasons already owned by
`TodayV2UnavailableHorizonSelectionReason`:

~~~text
invalid_target_clock
missing_long
missing_medium
missing_fast
no_coherent_triple
~~~

All other failures use exactly:

~~~json
{
  "schemaVersion": "today-v2-real-api-proof.v1",
  "status": "error",
  "date": "YYYY-MM-DD",
  "code": "activation_version_mismatch"
}
~~~

Use a closed `ProofErrorCode` literal/enum. It must cover at least:

~~~text
invalid_date
invalid_out_path
invalid_base_url
sidecar_unhealthy
auth_failed
secure_cookie_missing
secure_cookie_requires_https
profile_failed
day_failed
payload_validation_failed
calculation_version_mismatch
activation_version_mismatch
scoring_version_mismatch
payload_version_mismatch
frontend_version_mismatch
content_version_mismatch
audit_alignment_failed
canon_keys_mismatch
horizon_validation_failed
internal_error
~~~

No error object contains `detail`, exception class, exception message, HTTP
body, validation body, URL, profile, cookie, IDs or copy.

`main` may catch the two owned outcome types explicitly. A final generic catch
may emit only `internal_error`; it must not inspect or print the exception.

## 4. Exact typed validation

`validate_today_v2_payload(raw) -> TodayPayload` must:

1. call `TodayPayload.model_validate(raw)` first;
2. convert Pydantic failure to `payload_validation_failed` without retaining or
   emitting the validation text;
3. require all six exact identities:

~~~text
meta.calculation_version          == CALCULATION_VERSION
meta.activation_layer_version     == ACTIVATION_LAYER_VERSION
meta.scoring_version              == SCORING_V2_VERSION
meta.payload_version              == TODAY_V2_PAYLOAD_VERSION
meta.frontend_payload_version     == V2_FRONTEND_PAYLOAD_VERSION
meta.content_version              == TODAY_CONTENT_VERSION
~~~

4. inspect the typed horizon audit:
   - unavailable union member -> `PipelineUnavailable(typed reason)`;
   - built union member -> exact `built / selected / 3`;
5. require audit payload identity equal to meta payload identity;
6. require actual audit canon key set equal to the exact nine current keys;
7. require non-null horizons, schema `today-horizons.v1`, deterministic mode,
   exact `long,medium,fast` order;
8. preserve all timing/content/provenance checks required by `82`; typed model
   validators may own checks already guaranteed by the Pydantic contract;
9. require every top-level horizon activation ID to resolve in
   `activation_evidence`, and never include orphan values in errors.

Version error codes must identify only the field, never include observed or
expected values in output.

## 5. Sidecar preflight boundary

Split the real request and pure parser:

~~~text
parse_sidecar_health(status_code, parsed_json) -> bool
check_sidecar_health() -> Literal["pass"] or ProofFailure("sidecar_unhealthy")
~~~

The real check calls only `http://127.0.0.1:18091/v1/health`, requires HTTP 200
and `ok is true`, and never returns/copies the body.

Run it before auth/profile/day. `build_redacted_proof` should receive only the
closed success value or omit the parameter and always emit `pass`; it must not
be able to manufacture `status=pass` with failed health.

## 6. Output and artifact discipline

- Write only the final allowlist outcome to `OUT`.
- Print the same object as one compact JSON line to stdout.
- Keep stderr empty for expected pass/unavailable/error outcomes.
- Exit `0` only for `status=pass`.
- Exit non-zero for `unavailable` and `error`.
- Use atomic replacement if practical, but no intermediate file may contain a
  raw response.
- Remove stale `OUT` before every official run.
- Never print or persist the auth response, profile response, day response,
  sidecar body or suppressed ASGI logs.

## 7. Required unit coverage

Keep the test file at most 320 physical lines and the script at most 320.
Use the committed canonical fixture as typed input; do not reintroduce a large
synthetic payload builder.

Required tests:

1. valid fixture -> exact pass allowlist;
2. parameterized mutation for each of all six version fields, including
   activation, -> its exact closed error code;
3. typed unavailable audit -> exact unavailable reason and four-key shape;
4. a calculation/activation/Pydantic/HTTP/internal failure can never become
   `unavailable`;
5. audit built/reason/count and audit payload identity alignment;
6. exact canon key missing and extra regressions;
7. exact horizon order and medium/fast peak regressions;
8. success cannot be built when sidecar preflight is false;
9. redactor emits structural IDs `long,medium,fast`, never `hz-*`;
10. collect **all** raw activation IDs from fixture horizons/evidence and prove
    none appears anywhere in recursively serialized result/error;
11. recursively walk all keys and scalar strings and reject forbidden
    profile/auth/copy fields, UUID format, Telegram identity and canonical city
    values;
12. activation hash deterministic and order-independent;
13. date/out/base URL validation, including URL credentials/query/fragment and
    HTTP secure-cookie rejection;
14. cookie source guard forbids header construction, cookie value `.get`, jar
    indexing and Set-Cookie parsing;
15. both `run_asgi_proof` and `run_http_proof` call the same real
    `request_proof` boundary; a weak helper-name substring assertion is not
    sufficient;
16. source guard forbids `DBG`, `DEBUG_ERROR`, `str(exc)`, `repr(exc)`,
    traceback printing and exception-message keyword parsing;
17. main/output test proves one compact sanitized JSON object and no traceback;
18. Make source guard proves the recipe is quiet (`@`) and keeps exact
    process-local flags.

No unit test performs external network I/O or DB writes.

## 8. Make target

Retain the documented defaults and aliases. Correct only these points:

- prefix the executable recipe with `@`;
- quote all four user-controlled arguments safely;
- never pass empty values;
- retain exact process-local environment:

~~~text
APP_ENV=development
DEV_MODE=false
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_DUAL_RUN=false
SOLARSAGE_V2_FRONTEND_ENABLED=false
PYTHONPATH=apps/api
~~~

No shell command may print profile/auth/day content.

## 9. Known runtime evidence — diagnose, do not fix in R2

Architect read-only checks established:

~~~text
loaded sidecar process start: 2026-07-10 11:02:50 MSK
current shared contract file mtime: 2026-07-12
sidecar venv imported constants: al-1.1 / ss-calc-1.2.0
current health calculation_version: ss-1.0.0
service state: active
~~~

This strongly indicates the currently loaded sidecar process predates the
accepted contract/runtime changes. R2 must not restart it, modify systemd or
weaken validation.

The corrected proof should expose the stale runtime as a closed identity error.
That error is the handoff evidence for a separate architect-authored controlled
runtime convergence wave.

Do not scan 31 dates after any version/health/runtime error: a date cannot fix
process identity.

If, unexpectedly, all identities are current on the first official date and
the pipeline is honestly unavailable, then follow document `82` and probe
ascending July dates using the official command only.

## 10. Exact allowed paths

R2 may edit only:

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md
~~~

Existing W3B documents `82` and `82A` remain byte-identical.

The complete relevant W3B worktree after R2 therefore consists of six paths:

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82_STAGE_B3_W3B_REAL_DEV_AUTH_API_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82A_STAGE_B3_W3B_ARCH_REVIEW_R1_PRIVACY_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md
~~~

No API/sidecar/frontend production code, generated contract, fixture, env,
systemd unit or unrelated path may change.

## 11. Forbidden

- no product/runtime threshold or canon changes;
- no sidecar/API restart, daemon-reload or unit edit;
- no `.env`/`.env.production` edit;
- no raw response/log capture, even temporarily;
- no inline date probe;
- no direct DB/ORM access from the proof;
- no dependency override/mock/fixture query in the real proof;
- no stage, commit or push;
- no B4/frontend/deploy work;
- no subagents or delegation;
- never touch frozen unrelated paths.

## 12. Gates before the official proof

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

git diff --check
git diff --cached --quiet
~~~

Required:

~~~text
script <=320
test <=320
proof unit PASS
full API 0 failures
GRACE 3/3
contract fixture/check PASS
contract Vitest 21 PASS
typecheck PASS
index empty
services unchanged
~~~

## 13. Official proof procedure

First remove the old sanitized artifact without reading it:

~~~bash
rm -f /tmp/solarsage-v2-real-api-proof.json
~~~

Run exactly:

~~~bash
make prove-today-v2-real \
  DATE=2026-07-08 \
  OUT=/tmp/solarsage-v2-real-api-proof.json
~~~

Inspect only the closed top-level shape and allowlist keys. Never print a raw
response.

Outcome handling:

- `pass`: verify exact artifact, then record accepted date;
- `unavailable`: only a typed closed selection reason; if identities were
  exact, continue official ascending-date procedure from `82`;
- `error` with any identity/health/runtime code: stop immediately, do not scan
  more dates and return the blocked callback;
- any extra stdout/stderr, traceback, raw ID/copy/profile/cookie/UUID: fail R2.

## 14. Acceptance callback when a real triple unexpectedly passes

~~~text
READY_STAGE_B3_W3B_R2_REVIEW
accepted_date: <YYYY-MM-DD>
script_size: <n>/320 PASS
test_size: <n>/320 PASS
outcome_taxonomy: PASS typed unavailable vs closed error
typed_boundary: PASS TodayPayload -> exact validator -> allowlist redactor
secure_cookie: PASS named presence only; no value access/header copying
sidecar_health: PASS preflight before auth; success is fail-closed
exact_versions: PASS calc/al/scoring/payload/frontend/content
audit_alignment: PASS built/selected/3 and payload identity
canon_keys: PASS actual audit exact nine
horizon_ids: PASS long,medium,fast
stdout_redaction: PASS exactly one compact allowlist JSON; ASGI logs suppressed
raw_payload_artifacts: ZERO
raw_activation_ids: ZERO
proof_transport: ASGI_REAL_ROUTE
auth_dev: PASS DEV_MODE=false loopback policy
real_artifact: /tmp/solarsage-v2-real-api-proof.json REDACTED PASS
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
grace_lint: 3/3 PASS
contract_vitest: 21 PASS
typecheck: PASS
services: api=active unchanged; sidecar=active unchanged
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
r2_touched_paths: 4 EXACT_ALLOWLIST
w3b_relevant_paths: 6 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.

## 15. Required blocked callback for stale runtime identity

~~~text
BLOCKED_STAGE_B3_W3B_RUNTIME_IDENTITY
accepted_date: NONE
official_date: 2026-07-08
official_status: error
official_code: <closed code>
date_scan_after_identity_error: NOT_RUN
script_size: <n>/320 PASS
test_size: <n>/320 PASS
outcome_taxonomy: PASS typed unavailable vs closed error
typed_boundary: PASS TodayPayload -> exact validator -> allowlist redactor
secure_cookie: PASS named presence only; no value access/header copying
sidecar_health: PASS preflight before auth; success is fail-closed
exact_versions: BLOCKED current loaded runtime rejected without weakening
stdout_redaction: PASS exactly one compact allowlist JSON; ASGI logs suppressed
raw_payload_artifacts: ZERO
raw_activation_ids: ZERO
real_artifact: /tmp/solarsage-v2-real-api-proof.json REDACTED ERROR ONLY
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
grace_lint: 3/3 PASS
contract_vitest: 21 PASS
typecheck: PASS
services: api=active unchanged; sidecar=active unchanged
runtime_evidence: loaded sidecar predates current shared contract
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
r2_touched_paths: 4 EXACT_ALLOWLIST
w3b_relevant_paths: 6 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback. Do not restart the service or begin the next wave.
