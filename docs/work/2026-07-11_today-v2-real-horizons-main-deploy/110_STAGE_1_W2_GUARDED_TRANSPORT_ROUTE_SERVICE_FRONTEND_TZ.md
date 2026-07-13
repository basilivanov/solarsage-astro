# Stage 1.W2 ТЗ — guarded transport, route/service propagation and frontend marker

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base HEAD/origin: `933e749137d00c262c8f2cedec7b945582bf40d1`
Parents: Stage master `102`, accepted W1 `107`–`109`
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Роль и результат

Ты кодер. Реализуй только Stage 1.W2.

После W2 один и тот же canonical API на `127.0.0.1:8000` должен выбирать V2
только для закрытой локальной preview-комбинации:

~~~text
frontend development browser on loopback:3003
  -> fetchDay adds exact marker
  -> Next development rewrite to canonical API 8000
  -> backend pure transport guard
  -> exact dev-auth identity
  -> immutable TodaySelectionContext(force_v2=true, local_dev_preview)
  -> TodayService pre-cache selected V2
  -> V2 cache/read/write/runtime/meta/horizons family
~~~

Любой ordinary/public/production/wrong request продолжает использовать только
global rollout flags. При текущем global V2=false это V1.

W2 не перезапускает сервисы и не поднимает 3003. Controlled API restart —
отдельная W3 после архитектурной приёмки и push.

## 1. Preflight

До правок:

~~~text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = origin = 933e749137d00c262c8f2cedec7b945582bf40d1
index empty
tracked worktree clean
only frozen untracked paths remain
3003 and 18092 absent
8000, 18091, 3002 active
~~~

Frozen/unrelated paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Если base/scope отличается — остановиться.

## 2. Exact implementation allowlist

Ровно шесть путей:

~~~text
apps/api/app/services/today_preview_guard.py          # NEW
apps/api/app/api/day.py                               # MODIFY
apps/api/app/services/today_service.py                # MODIFY
apps/api/tests/test_today_preview_transport.py        # NEW
lib/grace/api/client.ts                               # MODIFY
__tests__/api/grace-client.test.ts                    # MODIFY
~~~

Никакие другие файлы не менять.

Особенно запрещены:

~~~text
apps/api/app/api/auth.py
apps/api/app/core/**
apps/api/app/db/**
apps/api/app/schemas/**
apps/api/app/services/day_scoring_runtime_service.py
apps/api/app/services/cache_key_service.py
apps/api/app/services/today_selection_context.py
apps/api/app/services/calendar_service.py
apps/solarsage/**
packages/contracts/**
scripts/preview-v2-real.mjs
next.config.mjs
app/**
components/**
hooks/**
other frontend API clients
systemd/env/main
generated fixtures
~~~

Не создавать DB migration, второй API, fixture runtime, cookie/query override
или global mutable preview flag.

## 3. Backend pure preview guard

Создать canonical GRACE module:

~~~text
apps/api/app/services/today_preview_guard.py
~~~

Обязательны:

- `AI_HEADER`;
- module contract/map;
- named semantic blocks;
- function contracts;
- standard library only (`dataclasses`, `enum`, `ipaddress`, `urllib.parse`,
  bounded string parsing helpers);
- никаких FastAPI, Request, settings, DB или logger imports.

### 3.1 Closed constants

Ровно:

~~~text
header name:  X-SolarSage-Preview-Mode
header value: today-v2-real
dev tg id:    999999999
dev username: dev_user
preview port: 3003
~~~

Строки marker/identity/port не должны быть разбросаны по backend-файлам.
Route импортирует constants/guard из этого module.

### 3.2 Immutable input and decision

Рекомендуемая форма:

~~~py
@dataclass(frozen=True, slots=True)
class TodayPreviewGuardInput:
    app_env: str
    marker_value: str | None
    client_host: str | None
    host: str | None
    origin: str | None
    forwarded: str | None
    x_forwarded_for: str | None
    x_forwarded_host: str | None
    x_forwarded_port: str | None
    x_real_ip: str | None
    tg_user_id: int | None
    tg_username: str | None

@dataclass(frozen=True, slots=True)
class TodayPreviewGuardDecision:
    authorized: bool
    reason: TodayPreviewGuardReason
~~~

Equivalent safe naming разрешён. Никаких raw request/user объектов в result.

Closed reason enum должен как минимум различать:

~~~text
authorized
production_denied
app_env_denied
marker_denied
client_denied
forwarded_chain_denied
host_denied
origin_denied
port_denied
identity_denied
~~~

Не возвращать raw header/host/user values в reason/result.

### 3.3 Exact evaluation order

Pure guard обязан проверять в таком порядке:

1. `app_env == production` после safe trim/lower → absolute deny immediately;
2. only exact normalized `development` environment may continue;
3. marker exact match;
4. `request.client.host` loopback;
5. every forwarded client address loopback and syntactically valid;
6. every forwarded host local/loopback and syntactically valid;
7. effective host local/loopback;
8. optional Origin, when present, local/loopback;
9. effective external preview port exactly `3003`;
10. exact dev identity: both tg id and username;
11. authorized.

Production deny must occur before touching marker, transport or identity fields.
Test this with exploding/sentinel values.

### 3.4 Loopback and authority rules

Allowed host identities:

~~~text
localhost
127.0.0.0/8 IP literals
::1
[::1]
~~~

Use `ipaddress.ip_address(...).is_loopback`; do not use prefix checks such as
`startswith("127.")` without IP validation.

Support safely:

~~~text
localhost:3003
127.0.0.1:3003
[::1]:3003
~~~

Reject malformed authorities, userinfo, public names/IPs, missing effective
preview port, non-numeric port and port other than 3003.

### 3.5 Direct and Next-rewrite transport

Guard должен разрешать обе безопасные формы:

Direct local proof:

~~~text
client_host=127.0.0.1
host=127.0.0.1:3003
no forwarded headers
optional origin=http://127.0.0.1:3003
~~~

Canonical Next rewrite proof:

~~~text
client_host=127.0.0.1
host may be internal 127.0.0.1:8000
x-forwarded-host=127.0.0.1:3003
x-forwarded-port=3003
x-forwarded-for contains loopback addresses only
optional origin=http://127.0.0.1:3003
~~~

For comma-separated forwarded chains every entry must be valid and loopback.
One public/malformed entry denies the entire request.

If RFC `Forwarded` exists, parse only bounded `for=`/`host=` parameters needed
for this decision; unknown/obfuscated/malformed address tokens deny. Never trust
`Forwarded` merely because another X-Forwarded header looks local.

Host selection precedence:

~~~text
x-forwarded-host when present
else valid Forwarded host when present
else Host
~~~

Port selection precedence:

~~~text
x-forwarded-port when present
else chosen forwarded host explicit port
else Host explicit port
~~~

When Origin is present, it must itself be loopback and explicitly use port
3003. Origin absence is allowed for same-origin GET/proxy behavior.

Do not inspect User-Agent, Referer, cookies or query parameters.

## 4. Day route integration

Modify only `apps/api/app/api/day.py`.

### 4.1 Request extraction

Add FastAPI `Request` parameter to `get_day`. Extract only:

~~~text
request.client.host
Host
Origin
Forwarded
X-Forwarded-For
X-Forwarded-Host
X-Forwarded-Port
X-Real-IP
X-SolarSage-Preview-Mode
authenticated user tg_user_id/tg_username
settings.app_env
~~~

Pass these explicit scalar values into the pure guard.

Do not log raw values. Do not persist them. Do not put them in selection context.

### 4.2 Selection context

Always resolve once per day request:

~~~py
decision = authorize_today_preview(...)
selection_context = resolve_today_selection_context(
    global_v2_enabled=settings.solarsage_v2_enabled,
    preview_authorized=decision.authorized,
)
~~~

Then pass `selection_context` explicitly to `TodayService.get_today_payload`.

Ordinary deny is not an HTTP error: request continues through normal V1/global
selection. Do not expose deny reason in HTTP body/header.

Route must ignore query params such as `preview=`, `fixture=`, `v2=`, `why=` for
selection. Existing `why=1` remains frontend UI state only.

Update route GRACE contract/map inputs/dependencies/invariants.

## 5. TodayService propagation

Modify only the necessary selection boundaries in
`apps/api/app/services/today_service.py`.

### 5.1 Compatible signature

Add explicit optional context without breaking existing callers:

~~~py
async def get_today_payload(
    self,
    user_id,
    target_date: Date,
    access_state: ContentAccessState | None,
    skip_prefetch: bool = False,
    *,
    selection_context: TodaySelectionContext | None = None,
) -> TodayPayload:
~~~

Existing callers without context retain exact behavior.

### 5.2 One request-local selection snapshot

Before cache read:

~~~py
force_v2 = selection_context.force_v2 if selection_context is not None else False
selected_scoring_version = selected_scoring_version_for_flags(force_v2=force_v2)
selected_v2 = str(selected_scoring_version) == str(SCORING_V2_VERSION)
compute_v2 = should_compute_v2(force_v2=force_v2)
~~~

Equivalent local names allowed. Use these locals consistently. Do not reread
`settings.solarsage_v2_enabled` later for selected-vs-shadow policy.

### 5.3 Cache read

Call:

~~~py
expected_cache_identity(
    ...,
    selected_scoring_version=selected_scoring_version,
)
~~~

Preview V2 must never read a V1 row. Ordinary V1 must never read a preview V2
row. Do not change cache fields/hash/schema.

### 5.4 Sidecar activation selection/error policy

Call activation sidecar when `compute_v2` is true.

If sidecar activation call fails:

~~~text
selected_v2 true  -> re-raise, fail loud
selected_v2 false + dual-run compute -> existing shadow fail-open path
~~~

Forced local preview must have the same fail-loud policy as global V2.

Do not add/change event names or add header/identity data to logs.

### 5.5 Runtime propagation and split-brain assertion

Call:

~~~py
dual = runtime.compute(..., force_v2=force_v2)
~~~

Immediately after compute, fail closed if runtime selected family differs from
the pre-cache selected family:

~~~text
str(dual.selected_scoring_version) != str(selected_scoring_version)
  -> RuntimeError with safe fixed message, no personal data
~~~

Then keep existing canonical identity resolver, cache write, public meta, audit
and horizon construction based on `dual.selected_scoring_version`.

Do not fabricate V2/horizons. Existing unavailable/null semantics remain.

### 5.6 Prefetch

Existing background prefetch calls without selection context remain ordinary
global/default requests. Do not propagate local preview context into week
prefetch and do not mutate process globals.

Update TodayService GRACE inputs/invariants/contract.

## 6. Frontend marker emission

Modify only `lib/grace/api/client.ts`.

### 6.1 Closed constants and pure decision

Own/export stable constants in this module:

~~~text
TODAY_PREVIEW_HEADER_NAME = X-SolarSage-Preview-Mode
TODAY_PREVIEW_HEADER_VALUE = today-v2-real
TODAY_PREVIEW_PORT = 3003
~~~

Add a small pure decision helper receiving explicit runtime facts, for example:

~~~ts
type TodayPreviewBrowserRuntime = {
  nodeEnv: string | undefined
  hostname: string
  port: string
}

export function shouldEmitTodayPreviewMarker(
  runtime: TodayPreviewBrowserRuntime,
): boolean
~~~

Exact allow rule:

~~~text
nodeEnv === development
hostname normalized in localhost / loopback IP
port === 3003
~~~

Support browser IPv6 hostname with or without brackets.

No `NEXT_PUBLIC_*`, cookie, query, localStorage or arbitrary env override may
activate marker. Production bundle must fail closed even on localhost:3003.

### 6.2 fetchDay only

`fetchDay` reads browser facts at call time only when `window` exists. It adds
the exact marker only when the pure helper allows it.

Preserve:

~~~text
Accept: application/json
credentials: include
same endpoint
same HTTP/JSON/schema error behavior
TodayPayloadWireSchema validation
~~~

`fetchCalendar` must remain marker-free even on development localhost:3003.
No other client gains the marker.

Update frontend module contract/map/invariants.

## 7. Backend tests

Create one canonical GRACE file under 1000 lines:

~~~text
apps/api/tests/test_today_preview_transport.py
~~~

Every public test/fake method/nested public helper must have paired full function
contracts so exact-file `scripts/grace_lint.py` passes. No suppression.

Minimum 30 collected cases after parametrization.

### 7.1 Pure guard cases

Mandatory:

1. exact constants;
2. exact reason enum closed values;
3. production absolute first deny with exploding other fields;
4. non-development non-production deny;
5. missing marker deny;
6. wrong marker deny;
7. missing client deny;
8. public client deny;
9. direct localhost/127.0.0.1/[::1]:3003 allow;
10. public Host deny;
11. wrong/missing/non-numeric port deny;
12. public Origin deny;
13. wrong Origin port deny;
14. absent Origin allowed;
15. all-loopback X-Forwarded-For allow;
16. one public X-Forwarded-For entry deny;
17. malformed X-Forwarded-For deny;
18. public/malformed X-Real-IP deny;
19. local Next rewrite host/port allow;
20. public X-Forwarded-Host deny;
21. wrong X-Forwarded-Port deny;
22. RFC Forwarded all-local allow;
23. RFC Forwarded public/unknown/malformed deny;
24. wrong tg id deny;
25. wrong/missing username deny;
26. exact identity allow;
27. decision contains no raw transport/identity fields;
28. guard module has no settings/FastAPI/logger/global current context.

### 7.2 Route ASGI integration

Use `ASGITransport` with explicit client address and dependency overrides. No
route interception outside the ASGI app, no live service restart.

Mandatory:

- exact local dev combination reaches route and passes
  `TodaySelectionContext(force_v2=True, source=LOCAL_DEV_PREVIEW)`;
- ASGI response from a schema-valid test stub exposes current V2 identity;
- missing/wrong marker continues ordinary V1/global context, not 403;
- query parameter alone cannot activate;
- exact marker with ordinary Telegram identity cannot activate;
- exact marker with public forwarded address cannot activate;
- exact marker on wrong port cannot activate;
- production absolute deny continues ordinary global context;
- global V2 true without preview resolves source `GLOBAL_FLAGS`, not local preview;
- two overlapping local/ordinary ASGI calls receive independent contexts and
  global settings remain unchanged.

Test stubs may return minimal schema-valid V1/V2 payloads but may not import
frontend/demo/mock runtime modules. V2 stub must respect current payload/frontend
identity and non-null V2 contract; unavailable horizons must remain honest null
with matching pipeline audit.

### 7.3 TodayService boundary tests

Mandatory focused proofs with deterministic mocks:

- forced context passes explicit current V2 version to cache-read identity;
- default/ordinary context passes legacy V1 under current global false;
- forced context makes `should_compute_v2`/activation sidecar path active;
- forced context passes `force_v2=True` to runtime compute;
- forced sidecar activation failure re-raises;
- shadow-only sidecar activation failure remains fail-open;
- runtime/pre-cache family mismatch raises safe split-brain error before public
  payload/cache write;
- global settings unchanged after forced success/failure;
- no preview context is passed into `_prefetch_week`.

Use early deterministic stops/spies where possible; do not duplicate the whole
astrological pipeline merely to prove argument propagation.

## 8. Frontend tests

Modify only:

~~~text
__tests__/api/grace-client.test.ts
~~~

Add at least these cases:

1. pure helper allows development `127.0.0.1:3003`;
2. pure helper allows development `localhost:3003`;
3. pure helper allows development IPv6 loopback:3003;
4. local development port 3000 denies;
5. public hostname development port 3003 denies;
6. production localhost:3003 denies;
7. SSR/no-window fetchDay sends no marker;
8. browser development local 3003 fetchDay sends exact header;
9. marker coexists with exact Accept and credentials include;
10. fetchCalendar remains marker-free in the same local dev runtime;
11. error/schema behavior remains covered by existing tests;
12. no fixture/demo payload becomes product fallback.

Restore env/window/fetch mocks after every case. Do not make tests depend on CSS
or UI copy.

## 9. Static/security guards

Tests or explicit gates must prove:

~~~text
no ContextVar/thread-local/module current selection
no settings mutation or setattr(settings)
no header/host/user/query/cookie logging
no new log event
no auth/dev endpoint change
no calendar service/client marker
no DB/schema/migration change
no package contract/generated change
no launcher/next config change
production deny is first
force/default signatures remain compatible
~~~

## 10. Mandatory gates

Run from repo root.

### 10.1 Backend exact GRACE/lint/type/compile

~~~bash
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/ruff check \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/mypy --follow-imports=skip \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py

apps/api/.venv/bin/python -m py_compile \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py
~~~

Exact four backend paths must be clean. Full-app baseline is not an exemption
for these paths.

### 10.2 Backend focused

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_scoring_v2_runtime_flags.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_day_endpoints.py \
  -q
~~~

All pass.

### 10.3 Full API

~~~bash
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
~~~

Accepted current baseline on W1 commit:

~~~text
1325 passed, 4 skipped, 0 failed
~~~

W2 adds tests; zero failures required.

### 10.4 Frontend focused/full

~~~bash
npx vitest run __tests__/api/grace-client.test.ts
npx vitest run
npx tsc --noEmit
pnpm contracts:check
pnpm guardrails:prod
~~~

All functional gates must pass. Do not regenerate or modify contracts.

Run exact-file frontend lint if available. If repository-wide frontend
guardrail remains on accepted W0 baseline, prove touched frontend paths add zero
new errors and record exact baseline without editing unrelated files.

### 10.5 Diff/scope

~~~bash
git diff --check
git diff --cached --quiet
git diff --name-only
git ls-files --others --exclude-standard apps/api lib __tests__
git diff --exit-code HEAD -- \
  apps/api/app/api/auth.py \
  apps/api/app/core \
  apps/api/app/db \
  apps/api/app/schemas \
  apps/api/app/services/day_scoring_runtime_service.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/app/services/today_selection_context.py \
  apps/api/app/services/calendar_service.py \
  apps/solarsage packages/contracts scripts/preview-v2-real.mjs next.config.mjs \
  app components hooks
~~~

Changed implementation paths = exact 6.

## 11. Runtime safety/final state

До callback:

~~~text
HEAD/origin unchanged at 933e749...
index empty
commit not created
push not created
3003/18092 absent
API/sidecar/frontend start timestamps unchanged
no service restart
no env/main edit
frozen paths untouched
W3 not started
~~~

Do not run manual uvicorn, second API or preview frontend.

## 12. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_1_W2
base_sha: 933e749137d00c262c8f2cedec7b945582bf40d1
changed_paths: EXACT_6
guard_constants: EXACT
guard_reasons: CLOSED
production_absolute_deny: PASS_FIRST
development_only: PASS
direct_loopback_3003: PASS
next_rewrite_loopback_3003: PASS
public_forwarded_chain: DENIED
wrong_marker_port_identity: DENIED
query_cookie_referer: NOT_SELECTORS
route_context_preview: LOCAL_DEV_PREVIEW_V2
route_context_ordinary: GLOBAL_FLAGS
route_concurrent_independence: PASS
service_cache_selected_authority: PASS
service_sidecar_force_policy: PASS
service_runtime_force_propagation: PASS
service_split_brain_guard: PASS
settings_mutation: ZERO
frontend_fetch_day_marker: PASS_LOCAL_DEV_3003_ONLY
frontend_calendar_marker: ABSENT
backend_exact_grace: PASS_4_OF_4
backend_focused: <count> PASS
backend_full: <counts>
frontend_focused: <count> PASS
frontend_full: <counts>
typecheck: PASS
contracts_check: PASS
prod_guard: PASS
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
head_origin: 933e749137d00c262c8f2cedec7b945582bf40d1_EQUAL
ports_3003_18092: ABSENT
services_env_main: UNCHANGED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
