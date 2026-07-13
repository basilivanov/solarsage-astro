# Stage B3.W3B — architect review R1: privacy-safe real proof

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Parent implementation document: `82`
Статус: **CORRECTIONS — NO COMMIT/PUSH**

## 1. Immediate privacy correction

The attempted ad-hoc date probe contained a branch that would write the raw
`/api/day` response to `/tmp/solarsage-v2-real-api-proof.json`. The architect
interrupted it before accepted output and deleted the path without reading it.

From now on:

- no inline Python/date probe may write or print a raw response;
- no raw response may be stored under any temporary path;
- date probing must call the committed proof command once per date;
- every success/unavailable/error output passes through the script's explicit
  allowlist redactor first;
- before the final run, remove `OUT` without reading it;
- only the final redacted artifact may exist at `OUT`.

Do not resume the interrupted inline probe.

## 2. Script size and typed boundary

`scripts/prove_today_v2_real_api.py` is currently about 446 lines; the accepted
limit is 320. Reduce it to **<=320 physical lines** without removing checks.

Use the typed model as the shared boundary:

~~~text
validate_today_v2_payload(raw) -> TodayPayload
build_redacted_proof(payload: TodayPayload, transport, date, sidecar_health)
  -> allowlist dict
request_proof(client, transport, date) -> allowlist dict
run_asgi_proof / run_http_proof -> same request_proof boundary
~~~

Do not return the original raw dict from validation and then reparse camel/snake
dict keys in the redactor. Typed field access removes duplicated wire logic and
shrinks the script.

Remove unused imports and verbose duplicate docstrings while retaining required
GRACE contracts.

## 3. Secure cookie behavior

ASGI mode must not manually parse `Set-Cookie` or construct a raw `Cookie`
header.

Use:

~~~text
ASGITransport(app=app, client=("127.0.0.1", <ephemeral port>))
base_url=https://127.0.0.1:8000
~~~

The HTTPS scheme is an in-process URL only; it does not create a TLS listener.
It allows httpx's cookie jar to preserve the production `Secure` session cookie
normally. After `/api/auth/dev`, assert only that the named cookie exists in
the private jar; never read, print or serialize its value. Profile/day requests
use the same client with no cookie header argument.

HTTP mode may be used only with a base URL whose cookie policy works. If an
`http://` URL yields a Secure cookie that the jar will not send, fail with the
sanitized code `secure_cookie_requires_https`; do not downgrade/reissue the
cookie and do not manually copy its value. B4 browser E2E owns actual loopback
browser-cookie behavior.

Tests must prove the source contains no manual `set-cookie` splitting, raw
cookie value extraction or `Cookie` header construction.

## 4. Sidecar health must be measured

The artifact currently hardcodes `sidecarHealth=pass`. Replace this with an
actual preflight request to:

~~~text
http://127.0.0.1:18091/v1/health
~~~

Require HTTP 200 and the expected healthy status field. Pass only a boolean or
closed `pass` value into the redactor. Never copy the sidecar body.

Unit-test the health result boundary without external I/O by testing the pure
status parser/helper. The real gate uses the actual service.

## 5. Complete exact validation

`validate_today_v2_payload` must check all current identities:

~~~text
calculation             CALCULATION_VERSION
activation layer        ACTIVATION_LAYER_VERSION
scoring                 SCORING_V2_VERSION
payload                 TODAY_V2_PAYLOAD_VERSION
frontend                V2_FRONTEND_PAYLOAD_VERSION
content                 TODAY_CONTENT_VERSION
~~~

Also require exact audit alignment:

~~~text
horizon_pipeline.status          built
horizon_pipeline.reason          selected
horizon_pipeline.selected_count  3
audit.payload_version             == meta.payload_version
~~~

The canon-key block is currently indented beneath the `if orphaned` branch and
is therefore unreachable after the raise. Move it to the normal success path.
Require the payload audit's actual canon key set to equal the exact nine keys
from `get_canon_versions()`.

The redactor must report `sorted(payload.v2.audit.canon_versions.keys())`, not
freshly regenerate canon keys independently after validation.

Never include raw orphan activation IDs in an error. Use only a structural
code plus count/hash if needed.

## 6. Structural horizon IDs in redacted output

The redacted artifact currently emits internal item IDs such as `hz-long`.
Emit the closed structural horizon enum instead:

~~~text
id: long | medium | fast
~~~

Do not output the internal public content/entity ID. The final proof must show:

~~~text
[long, medium, fast]
~~~

Derive the closed sphere set from the typed
`TodayV2ProductSphereKey` literal (`typing.get_args`) or validate through the
typed model and reuse those typed values. Do not maintain a second handwritten
12-sphere enum in the proof script.

## 7. Sanitized unavailable/error outcomes

Introduce one compact exception/outcome for an honest unavailable pipeline.
The only emitted shape is:

~~~json
{
  "schemaVersion": "today-v2-real-api-proof.v1",
  "status": "unavailable",
  "date": "YYYY-MM-DD",
  "reason": "<closed reason>"
}
~~~

For all other failures, CLI stderr/stdout may contain only a closed structural
error code and date. No traceback by default and no Pydantic input body, copy,
profile, cookie or raw IDs.

The CLI exits non-zero for unavailable/error and writes only the sanitized
outcome if it writes `OUT` at all.

## 8. Make target must be truly one-command

Add defaults before the target:

~~~make
PROOF_DATE ?= 2026-07-08
PROOF_OUT ?= /tmp/solarsage-v2-real-api-proof.json
PROOF_TRANSPORT ?= asgi
PROOF_BASE_URL ?= http://127.0.0.1:8000
~~~

Support the documented user overrides `DATE`, `OUT`, `TRANSPORT`, `BASE_URL`
without ever passing empty values. One acceptable approach is normalized Make
variables that prefer command-line aliases and otherwise use the defaults.

The target must set exact process-local env from document `82`:

~~~text
APP_ENV=development
DEV_MODE=false
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_DUAL_RUN=false
SOLARSAGE_V2_FRONTEND_ENABLED=false
~~~

Current `DEV_MODE=true` must change to false so loopback auth policy itself is
proved.

Pass `--transport` and `--base-url` from Make variables; do not hardcode ASGI.

## 9. CLI validation

Validate `--date` with `date.fromisoformat` and return a canonical ISO date.
Reject malformed values before any I/O. Validate `--out` is a file path, and
transport/base URL combinations structurally.

## 10. Unit-test corrections

Keep the test file **<=320 lines**. Remove the large synthetic payload builder
that bypasses `validate_today_v2_payload` and uses non-contract shapes.

Use the canonical committed fixture for pure mutation tests and add/retain:

- all six exact version fields checked;
- audit reason/count alignment checked;
- actual payload audit canon key removal/addition rejected;
- unreachable-canon regression;
- redactor emits `long,medium,fast`, never `hz-*`;
- medium/fast peak rule;
- unavailable returns only the sanitized outcome;
- raw activation IDs absent from result and errors;
- redacted output recursively contains no forbidden keys/values;
- activation hash order-independence tested by reversing one item's IDs;
- date parser rejects invalid dates;
- Make/source guard: both transports use the common request/validator/redactor
  boundary;
- source guard: no manual cookie extraction/header construction;
- sphere enum is not handwritten twice.

Tests must not import `CANON_PROFILE` merely to assert its text is absent.

## 11. Real date procedure

After corrections, remove `OUT` and run the official command for
`2026-07-08`.

If unavailable, invoke the same official command separately for ascending July
dates. Each invocation may emit only its sanitized unavailable object. Do not
use an inline script, do not print payloads, and stop at the first redacted
success.

The successful artifact must be produced by `main -> run_* -> common request ->
validate -> redact -> write`, not by copying intermediate Python objects.

## 12. Exact allowed paths

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82A_STAGE_B3_W3B_ARCH_REVIEW_R1_PRIVACY_PROOF_TZ.md
~~~

Document `82` remains unchanged. No product/backend/frontend/generated file may
change.

## 13. Gates

~~~bash
wc -l scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_real_today_v2_api_proof.py -q

apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

python3 scripts/grace_lint.py \
  scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

rm -f /tmp/solarsage-v2-real-api-proof.json
make prove-today-v2-real \
  DATE=<accepted-date> \
  OUT=/tmp/solarsage-v2-real-api-proof.json

test -s /tmp/solarsage-v2-real-api-proof.json

pnpm contracts:fixture:check
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
script <=320 lines
test <=320 lines
proof unit PASS
full API 0 failures
real artifact redacted PASS
generated/fixture unchanged
index empty
~~~

## 14. Exact callback

~~~text
READY_STAGE_B3_W3B_R1_REVIEW
accepted_date: <YYYY-MM-DD>
script_size: <n>/320 PASS
test_size: <n>/320 PASS
typed_boundary: PASS validator returns TodayPayload; redactor consumes typed model
secure_cookie: PASS ASGI HTTPS jar; no manual cookie value handling
sidecar_health: PASS measured 18091/v1/health
exact_versions: PASS calc/al/scoring/payload/frontend/content
audit_alignment: PASS built/selected/3 and payload identity
canon_keys: PASS actual audit exact nine; regression tested
horizon_ids: PASS long,medium,fast; no hz-* output
unavailable_redaction: PASS closed reason only
raw_payload_artifacts: ZERO
raw_activation_ids: ZERO in artifact/errors
make_one_command: PASS defaults and overrides
proof_transport: ASGI_REAL_ROUTE
auth_dev: PASS DEV_MODE=false loopback policy
real_artifact: /tmp/solarsage-v2-real-api-proof.json REDACTED
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
contract_vitest: 21 PASS
typecheck: PASS
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
changed_paths: 4 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
