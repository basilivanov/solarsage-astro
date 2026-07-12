# Stage 1 master — safe request-scoped V2 preview and canonical API convergence

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base SHA: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Parent plan: `101_TWO_STAGE_COMPLETION_MASTER_PLAN.md`
Статус: **STAGE MASTER — EXECUTE ONLY THE CURRENT AUTHORIZED WAVE**

## 1. Stage outcome

Stage 1 creates a real local review path without exposing unapproved V2 to
ordinary users:

~~~text
ordinary production/public request
  -> existing global flag selection (currently V1 before release)

exact local 3003 preview request
  + development app env
  + loopback/proxy-local transport
  + dedicated dev-auth identity
  + exact preview marker
  -> request-scoped V2 selection
  -> today.v2.1 / 3 / 10
  -> long / medium / fast
~~~

No global settings mutation, no second API, no fixture, no manual uvicorn.

## 2. Closed security model

### 2.1 Explicit marker

Proposed closed marker:

~~~text
request header: X-SolarSage-Preview-Mode
value:          today-v2-real
~~~

Header name/value are constants owned by a small pure boundary, not scattered
string literals.

### 2.2 Frontend emission

Frontend sends the marker only when all are true in browser runtime:

~~~text
process.env.NODE_ENV === development
window.location.hostname in {127.0.0.1, localhost, ::1}
window.location.port === 3003
request is fetchDay
~~~

No env override can make production bundle send it. Other API calls do not gain
the marker unless separately justified.

### 2.3 Backend acceptance

Backend accepts marker only when all are true:

~~~text
settings.app_env != production
request client is loopback
effective local host/origin is loopback
effective preview port is exactly 3003
forwarded chain contains no public/non-loopback address
marker value exact
authenticated user is exact dedicated dev-auth identity
~~~

Use a pure guard with explicit inputs and a closed reason enum. Do not infer
from User-Agent, Referer alone, query string or cookie contents.

### 2.4 Dedicated identity

Current `/api/auth/dev` owns fixed `tg_user_id=999999999`, username `dev_user`.
The guard requires both ID and username plus the transport/env/marker checks;
identity alone never activates V2.

Do not add DB columns or alter auth/session schema in Stage 1.

### 2.5 Production fail-closed

`APP_ENV=production` is an absolute first deny even if every request header or
identity is forged. Tests must prove the guard does not inspect/use mutable
global preview flags after this deny.

## 3. Request-scoped selection model

Create an immutable value, recommended shape:

~~~py
@dataclass(frozen=True)
class TodaySelectionContext:
    force_v2: bool = False
    source: Literal['global_flags', 'local_dev_preview'] = 'global_flags'
~~~

Equivalent Pydantic/frozen naming is allowed. It contains no user/profile/header
data and is safe to pass through service boundaries.

Pure resolver:

~~~py
resolve_today_selection_context(
    *,
    global_v2_enabled: bool,
    preview_authorized: bool,
) -> TodaySelectionContext
~~~

Rules:

~~~text
preview_authorized true -> force_v2 true, source local_dev_preview
else global_v2_enabled true -> force_v2 true, source global_flags
else -> force_v2 false, source global_flags
~~~

The context never mutates `settings` and does not outlive the request.

## 4. Scoring/cache integration invariants

Every boundary must use one identical selected family:

~~~text
route selection context
  -> TodayService pre-cache selected version
  -> expected_cache_identity
  -> DayScoringRuntimeService compute selection
  -> resolved public runtime identity
  -> cache write identity
  -> payload meta/audit
~~~

Forbidden split-brain cases:

- V2 cache read + V1 scoring;
- V1 cache read + V2 public meta;
- preview request reading ordinary V1 cache;
- ordinary request reading preview V2 cache;
- global setting changed for one request;
- dual-run computation treated as selected V2.

Existing cache key version fields already segregate V1/V2. No DB migration or
hash algorithm change.

Recommended API extensions with default compatibility:

~~~py
selected_scoring_version_for_flags(*, force_v2: bool = False)
should_compute_v2(*, force_v2: bool = False)
expected_cache_identity(..., selected_scoring_version: int | str | None = None)
DayScoringRuntimeService.compute(..., force_v2: bool = False)
TodayService.get_today_payload(..., selection_context: TodaySelectionContext | None = None)
~~~

Equivalent explicit naming allowed. Defaults must preserve every existing
caller exactly.

## 5. Wave decomposition

### S1.W0 — strict harness checkpoint

ТЗ создаётся отдельно. Scope only current W3 launcher/tests/docs. No backend.

Exit:

~~~text
PUSHED_STAGE_1_W0_STRICT_HARNESS
~~~

### S1.W1 — pure selection/cache foundation

Allowed conceptual ownership:

~~~text
apps/api/app/services/day_scoring_runtime_service.py
apps/api/app/services/cache_key_service.py
new pure preview/selection context module if justified
focused API tests only
~~~

No route, frontend, TodayService or runtime restart.

Required proof:

- pure truth table;
- default behavior unchanged;
- force V2 selects current version family;
- no global mutation;
- independent concurrent calls return independent identities;
- cache read/write hashes align;
- full API green;
- commit/push.

### S1.W2 — transport guard + route/frontend/Today integration

Conceptual ownership:

~~~text
lib/grace/api/client.ts
frontend API client tests
apps/api/app/api/day.py
apps/api/app/services/today_service.py
pure local-preview guard module
focused API route/service/security tests
~~~

Potential additional runtime service files only with architect approval.

Required proof:

- exact security truth table;
- production absolute deny;
- public forwarded host/address deny;
- wrong port/header/identity deny;
- exact local dev combination allow;
- frontend marker only local dev 3003;
- ordinary request remains V1 under current global flags;
- preview request returns V2 in ASGI integration;
- cache rows separate;
- no global settings change under concurrency;
- full frontend/API/contracts gates;
- commit/push.

### S1.W3 — controlled API restart

No file edits except architect evidence docs.

Preflight:

- branch/local/origin accepted S1.W2 SHA;
- tracked clean/index empty;
- full tests already accepted;
- API unit path/ExecStart canonical;
- sidecar/API active;
- record old API PID/start;
- ordinary control request V1;
- preview route ASGI proof V2.

One operation:

~~~bash
sudo systemctl restart solarsage-api.service
~~~

Post-restart:

- new API PID/start;
- sidecar/frontend/nginx PIDs unchanged;
- one listener 8000;
- no 8001/18092;
- health 200;
- no env edit;
- ordinary real HTTP request V1;
- dedicated local preview marker request V2;
- exact cache/provenance/horizon proof;
- logs contain no personal/header/cookie data.

### S1.W4 — strict preview proof

Resume W3 tooling:

- strict V2 identity only;
- 401/V1/unavailable are failures;
- actual desktop/mobile viewports;
- natural dev auth;
- generated schema validation;
- all horizon/technical/sphere interactions;
- screenshots/attachments;
- launcher process/config cleanup;
- accepted commit/push;
- leave review URL running in managed tmux after acceptance.

## 6. Test matrix

### Pure foundation

- resolver truth table;
- frozen context mutation rejection;
- current/legacy identity exact;
- force-v2/default/dual-run matrix;
- cache hash equality read/write;
- parallel tasks do not leak selection.

### Security guard

- production deny;
- non-loopback client deny;
- public forwarded-for deny;
- public forwarded-host deny;
- missing/wrong marker deny;
- local port !=3003 deny;
- wrong dev identity deny;
- exact local marker/dev identity allow;
- query parameter cannot activate;
- ordinary Telegram initData session cannot activate.

### Frontend

- development local 3003 adds exact header;
- local port 3000 does not;
- public host development does not;
- production local-like host does not;
- existing Accept/credentials and schema validation unchanged;
- calendar/other endpoints unchanged.

### Service/cache

- preview cache miss does not hit V1 row;
- later ordinary request still reads/writes V1;
- preview V2 response meta/audit/horizons exact;
- no settings mutation before/after failure;
- selected pipeline error remains fail-loud;
- unavailable remains honest null, never fabricated.

## 7. Logs/privacy

Do not log:

- header values;
- host/forwarded chain raw strings;
- user/Telegram ID or username;
- cookies/session token;
- payload/copy/activation IDs.

If a log is required, use existing registered event with allowlist only:

~~~text
preview_authorized: true|false
selection_source: global_flags|local_dev_preview
selected_family: v1|v2
closed_reason: enum
~~~

No new event without registry update in the same wave.

## 8. Runtime rollback

S1.W3 API restart rollback is code/process only; env unchanged.

If API fails after restart:

1. do not edit env;
2. collect sanitized status + last 80 journal lines;
3. rollback checkout is forbidden in dirty shared tree;
4. use accepted previous commit only through architect-authored rollback plan;
5. do not start manual uvicorn;
6. frontend/sidecar remain untouched.

Because current service already executes the shared checkout, S1.W1/W2 commits
must be accepted/pushed and tree clean before restart.

## 9. Stage acceptance

Stage 1 is accepted only with real HTTP evidence:

~~~text
ordinary control: V1 before global release
local dev preview: V2 today.v2.1 / 3 / 10
three horizons: long, medium, fast
no fixture/mock
no public/global preview leakage
desktop/mobile strict E2E pass
3003 review URL operational
feature branch clean/pushed
~~~

No conditional skip or ASGI-only proof can satisfy final Stage 1 acceptance.
