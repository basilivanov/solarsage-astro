# Stage B3.W3B — real dev-auth API and sidecar proof

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Authority: `00`, `50`, `51`, `75`, accepted W1/W2/W3A documents
Статус: **IMPLEMENTATION — NO COMMIT/PUSH**

## 1. Outcome

Create a reproducible one-command proof that the real FastAPI HTTP surface can
produce a backend-owned, validated, three-horizon V2 payload using:

~~~text
POST /api/auth/dev
PUT  /api/profile              dedicated dev user only
GET  /api/day/<accepted-date>
  -> real PostgreSQL 5433
  -> real sidecar 18091
  -> real activation/scoring/interpretation/horizon pipeline
  -> today.v2.1 / frontend 3 / content 10
  -> long, medium, fast
~~~

The proof runs the FastAPI application through ASGI transport in the current
Python process. This is a real route/dependency/DB/sidecar request, not a unit
service call, while respecting the repository prohibition on manual uvicorn.

The canonical systemd API on port 8000 remains running and unchanged in this
wave. A second proof mode must be reusable against `http://127.0.0.1:8000`
during B4/release after the controlled systemd reload.

## 2. New proof command

Add:

~~~text
scripts/prove_today_v2_real_api.py
~~~

and one Make target:

~~~bash
make prove-today-v2-real DATE=2026-07-08 \
  OUT=/tmp/solarsage-v2-real-api-proof.json
~~~

Make defaults:

~~~text
DATE       2026-07-08
OUT        /tmp/solarsage-v2-real-api-proof.json
TRANSPORT  asgi
BASE_URL   http://127.0.0.1:8000
~~~

The target supplies process-local settings only:

~~~text
APP_ENV=development
DEV_MODE=false
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_DUAL_RUN=false
SOLARSAGE_V2_FRONTEND_ENABLED=false
~~~

It must not edit `.env`, `.env.production`, systemd or the shell profile.

Supported script modes:

~~~text
--transport asgi
  import current app after environment is resolved;
  httpx ASGI transport;
  no listener/process/port allocation.

--transport http --base-url http://127.0.0.1:8000
  call the already-running canonical API;
  never start or restart it.
~~~

Both modes execute the same auth/profile/day flow and the same response
validator. No special success path for ASGI.

## 3. Dedicated dev profile through public API only

Use only the fixed `/api/auth/dev` user (`tg_user_id=999999999`, already owned
by the dev-auth endpoint). Never select or modify a real user.

After auth, issue `PUT /api/profile` through the authenticated HTTP client with
the canonical non-personal test profile:

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

This makes the proof reproducible and invalidates only the dedicated dev
user's caches through the normal profile API. Do not access ORM models or write
the DB directly from the proof script.

The script must never print or serialize the profile, auth response, user ID,
cookie or session token.

## 4. HTTP request contract

For ASGI mode:

- base URL and Host are `http://127.0.0.1:8000`;
- client address is loopback;
- no forwarded/proxy headers;
- use an empty cookie jar before `/api/auth/dev`;
- preserve the HttpOnly session cookie only inside the client;
- call `/api/day/<date>` with no query string and especially no `fixture`;
- do not override FastAPI dependencies;
- do not monkeypatch sidecar, DB, LLM, scoring or horizon services;
- do not use test fixtures, `page.route`, mock HTTP transports or canned
  responses.

Before the day call, require:

~~~text
GET http://127.0.0.1:18091/v1/health -> healthy
~~~

The health body is not copied into the proof; record only status/pass.

The normal endpoint may use deterministic LLM fallback if the configured
provider is unavailable. Horizon guidance remains deterministic and must not
depend on LLM output.

## 5. Typed payload validation

Validate the HTTP JSON through `TodayPayload.model_validate` before inspecting
it. Do not validate an ad-hoc subset only.

Require exact current identity:

~~~text
meta.payload_version           today.v2.1
meta.frontend_payload_version  3
meta.content_version           10
meta.calculation_version       ss-calc-1.2.0
meta.activation_layer_version  al-1.1
meta.scoring_version           ss-scoring-2.0
~~~

Require:

- `v2` non-null;
- `v2.audit.horizon_pipeline.status == built`;
- reason `selected`, selected count `3`;
- `v2.horizons.schema_version == today-horizons.v1`;
- `guidance_mode == deterministic`;
- item order exactly `long`, `medium`, `fast`;
- each item has non-empty active-from, active-until, state, range/state label,
  timezone and activation IDs;
- medium/fast have non-null `exact_at` and `peak_label`;
- long follows its contract and may omit exact peak;
- every horizon activation ID exists in `v2.activation_evidence`;
- all nested Pydantic provenance/cross-reference validators pass;
- every horizon has at least one manifestation, one action and one avoid item;
- all likely spheres are members of the closed 12-sphere product enum;
- the exact nine canon-version keys are present;
- no fixture query, fixture response marker, demo source or port 18092 is used.

An unavailable pipeline is an honest product outcome but is not the W3B
acceptance case. The script must exit non-zero with only this sanitized shape:

~~~json
{
  "status": "unavailable",
  "date": "YYYY-MM-DD",
  "reason": "<closed selection reason>"
}
~~~

Never print the full response when validation fails.

## 6. Redacted proof artifact

On success write exactly one JSON object to `OUT` and print the same redacted
summary. Required shape:

~~~json
{
  "schemaVersion": "today-v2-real-api-proof.v1",
  "status": "pass",
  "transport": "asgi",
  "date": "YYYY-MM-DD",
  "authPath": "/api/auth/dev",
  "dayPath": "/api/day/YYYY-MM-DD",
  "sidecarHealth": "pass",
  "versions": {
    "calculation": "ss-calc-1.2.0",
    "activation": "al-1.1",
    "scoring": "ss-scoring-2.0",
    "payload": "today.v2.1",
    "frontend": 3,
    "content": 10
  },
  "pipeline": {
    "status": "built",
    "selectedCount": 3,
    "guidanceMode": "deterministic"
  },
  "horizons": [
    {
      "id": "long",
      "tone": "<enum>",
      "timingState": "<enum>",
      "hasRange": true,
      "hasPeak": false,
      "activationCount": 1,
      "activationIdsSha256": "<sha256>",
      "manifestationCount": 1,
      "doCount": 1,
      "avoidCount": 1,
      "likelySpheres": ["<closed key>"]
    }
  ],
  "activationEvidenceCount": 1,
  "canonKeys": ["<sorted exact nine keys>"],
  "fixtureDependency": false
}
~~~

Counts vary according to the valid payload; the schema above shows field
ownership, not fixed counts except the three horizons.

Forbidden anywhere in the artifact/stdout:

- user/profile/birth/current-location fields;
- UUID, Telegram ID/name/initData;
- cookies/session/auth body;
- raw activation IDs;
- headline, intro, summary, manifestation, strength/risk, action/avoid or
  technical copy;
- exact natal values or coordinates;
- LLM/provider response.

Use SHA-256 over sorted activation IDs and counts instead of raw IDs.

## 7. Acceptance date procedure

First run exact `2026-07-08`.

If it returns an honest unavailable reason:

1. do not change selection thresholds, canons, profile, sidecar or product
   code;
2. probe dates in ascending order from `2026-07-01` through `2026-07-31` using
   the same command and canonical dev profile;
3. stop at the first validated built triple;
4. record that date as `<accepted-date>` for B4;
5. retain only the final successful redacted proof in `/tmp`.

If none of the 31 dates builds, stop with evidence; do not fabricate a triple.

## 8. Script architecture and tests

Keep the script at most 320 lines. Separate pure validation/redaction from I/O:

~~~text
validate_today_v2_payload(payload) -> typed validated result
build_redacted_proof(payload, transport, date) -> JSON-safe allowlist dict
run_asgi_proof(...)
run_http_proof(...)
~~~

Equivalent boundaries are allowed.

Add `apps/api/tests/test_real_today_v2_api_proof.py` with no external I/O. It
may load the canonical committed contract fixture only as test input.

Required unit coverage:

- valid current complete payload produces the exact redacted shape;
- previous/V1 versions rejected;
- null V2 rejected;
- unavailable pipeline returns sanitized unavailable outcome;
- missing/reordered horizon rejected;
- medium/fast missing peak rejected;
- provenance activation outside evidence rejected;
- forbidden output keys/raw activation IDs cannot appear recursively;
- activation hashes deterministic and order-independent;
- CLI transport/date/out validation;
- HTTP and ASGI modes call the same pure validator/redactor boundary by source
  guard or injected-call test.

No production runtime module may import this script.

## 9. Exact allowed paths

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82_STAGE_B3_W3B_REAL_DEV_AUTH_API_PROOF_TZ.md
~~~

No API/sidecar/frontend production code or generated contract change is
expected. If real proof exposes a production defect, stop and report it for a
separate architect correction wave.

## 10. Gates

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_real_today_v2_api_proof.py -q

apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

python3 scripts/grace_lint.py \
  scripts/prove_today_v2_real_api.py \
  apps/api/tests/test_real_today_v2_api_proof.py

make prove-today-v2-real \
  DATE=<accepted-date> \
  OUT=/tmp/solarsage-v2-real-api-proof.json

test -s /tmp/solarsage-v2-real-api-proof.json

pnpm contracts:fixture:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
npx tsc --noEmit

curl -fsS http://127.0.0.1:18091/v1/health >/dev/null
curl -fsS http://127.0.0.1:8000/api/health >/dev/null
systemctl is-active --quiet solarsage-api.service
systemctl is-active --quiet solarsage-sidecar.service

git diff --check
git diff --cached --quiet
git status --short
~~~

Inspect the redacted artifact structurally; do not paste any unredacted HTTP
body into callback or docs.

## 11. Forbidden

- no manual uvicorn or second API listener;
- no systemd restart/change;
- no `.env`/production env change;
- no direct DB write/query from the proof script;
- no user other than fixed dev-auth user;
- no mocks, dependency overrides, fixture query or route interception in the
  real proof;
- no product threshold/canon/version change;
- no frontend/B4 work;
- no stage/commit/push;
- no subagents/delegation;
- never touch frozen unrelated paths.

## 12. Exact callback

~~~text
READY_STAGE_B3_W3B_REVIEW
accepted_date: <YYYY-MM-DD>
proof_transport: ASGI_REAL_ROUTE
auth_dev: PASS loopback public route
profile_seed: PASS dedicated dev user through PUT /api/profile
postgres: PASS canonical 5433
sidecar: PASS canonical 18091 real activation
api_versions: PASS today.v2.1/frontend=3/content=10
horizons: PASS long,medium,fast backend-owned
timing: PASS ranges; medium/fast exact peaks
provenance: PASS all activation references resolved
guidance_mode: deterministic
fixture_dependency: NO
redacted_artifact: /tmp/solarsage-v2-real-api-proof.json
redaction: PASS no profile/auth/copy/raw activation IDs
proof_unit: <count> PASS
api_full: <count> passed, 4 skipped, 0 failed
contract_vitest: 21 PASS
typecheck: PASS
services: api=active unchanged; sidecar=active unchanged
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976 local/origin unchanged
changed_paths: 4 EXACT_ALLOWLIST
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

Stop after callback.
