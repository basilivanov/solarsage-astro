# Stage 1.W4.R1 — request-scoped full-content access for exact local preview

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Observed W4 blocker:

```text
real auth/day transport: 200/200
real identity: today.v2.1 / 3 / 10
backend horizons: long / medium / fast
chromium DOM: today-screen data-state=locked
mobile DOM: today-screen data-state=locked
strict result: 0 passed / 2 failed
```

Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO RUNTIME RESTART, NO COMMIT/PUSH**

## 1. Root cause

The API request-scoped V2 path is correct. The blocker is an independent access
boundary:

```text
/api/auth/dev identity has no active access ledger for 2026-07-08
AccessService.can_access_day -> preview/expired_access
TodayService returns the real V2 payload with access=preview
frontend adapter -> hasAccess=false
TodayScreen -> data-state=locked and hides the full V2 UI
```

The E2E correctly failed closed after identity/horizon assertions and before
declaring the DOM ready.

Do not weaken the E2E to accept `locked`. The goal is a real full-content review
path on 3003.

## 2. Architecture decision

Only an already-authorized local preview selection may receive request-scoped
full-content access:

```text
exact W2 guard authorization
  -> TodaySelectionContext(force_v2=true, source=local_dev_preview)
  -> pure access resolver
  -> ContentAccessState(
       state=full,
       reason=null,
       referralDaysLeft=null,
       subscriptionActive=null,
       accessUntil=null,
     )
```

Every other selection preserves the exact real AccessService result:

```text
missing/wrong marker       -> unchanged access
ordinary identity          -> unchanged access
public/invalid transport   -> unchanged access
production                 -> unchanged access
global V2 rollout source   -> unchanged access
local source with force_v2 false (invalid constructed context) -> unchanged
```

The resolver consumes the immutable `TodaySelectionContext`; it must not inspect
headers, env, settings, user, DB or global flags independently. This prevents a
second authorization truth source.

## 3. Why this design

Chosen:

- pure request-scoped access derivation;
- no AccessLedger writes;
- no fake subscription/referral row;
- no auth-dev hardcoded date grant;
- no global access bypass;
- no frontend hostname-based paywall bypass;
- no public contract enum expansion;
- no query selector;
- no cache identity/schema change.

Rejected:

1. Seeding a DB subscription in `/api/auth/dev`:
   persistent, date-dependent, duplicate-prone and creates setup state.
2. Granting access manually before each preview:
   exactly the operational «танцы с бубном» this path must remove.
3. Treating `locked` as E2E success:
   would hide the feature and make visual approval meaningless.
4. Frontend-only `hostname:3003` paywall bypass:
   duplicates backend authorization and makes UI/API access truth diverge.
5. Adding `local_dev_preview` to public access reason enum:
   unnecessary generated-contract expansion; the existing schema permits a
   full state with null commercial reason/metadata.
6. Pretending an active subscription/referral reason:
   false product semantics and can render a misleading trial banner.

## 4. Runtime safety before implementation

At task start required:

```text
branch/HEAD/origin = preview/... / 7d37acb...
tracked tree = clean
index = empty
3003/8001/18092 = absent
v2-preview tmux window = absent
API PID/start = 3887119 / Mon 2026-07-13 05:12:53 MSK
sidecar/frontend/nginx PID/start = unchanged W3 witnesses
```

Exact existing untracked paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/118_STAGE_1_W4_ARCH_ERRATA_NEXT_ENV_MTIME_NON_CONTRACT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/119_STAGE_1_W4_R1_REQUEST_SCOPED_FULL_ACCESS_PREVIEW_TZ.md
grace.db
skills/
```

Ignored Playwright failure artifacts under `test-results/`/`playwright-report/`
may exist and remain untouched. They are not product inputs.

## 5. Exact implementation allowlist

Allowed implementation/test paths only:

```text
apps/api/app/services/today_preview_access.py              NEW
apps/api/app/api/day.py                                    MOD
apps/api/tests/test_today_preview_access.py                 NEW
lib/adapters/today-payload.ts                               MOD
__tests__/lib/adapt-payload.test.ts                         MOD
components/today/today-screen.tsx                           MOD
__tests__/components/TodayScreen.test.tsx                   MOD
e2e/real-v2-preview.spec.ts                                 MOD
```

Architect docs 117–119 are already untracked and must remain byte-identical.

Any other path requires architect review before edit.

Explicitly forbidden without new architect authorization:

- existing 997-line `apps/api/tests/test_today_preview_transport.py`;
- guard/selection/cache/scoring/TodayService code;
- auth/access service or AccessLedger models;
- Pydantic access reason enums;
- generated OpenAPI/TypeScript/Zod contract files;
- package/lock/tsconfig/next-env;
- launcher/playwright config;
- systemd/env/nginx;
- fixtures/mocks.

## 6. Backend pure access resolver

Create:

```text
apps/api/app/services/today_preview_access.py
```

Required GRACE:

- `AI_HEADER`;
- `START_MODULE_CONTRACT`;
- `START_MODULE_MAP`;
- `START_BLOCK`;
- `START_FUNCTION_CONTRACT` for public resolver.

Recommended exact API:

```py
def resolve_today_access_for_selection(
    *,
    access_state: ContentAccessState,
    selection_context: TodaySelectionContext,
) -> ContentAccessState:
    ...
```

Closed behavior:

```py
is_local_preview = (
    selection_context.force_v2 is True
    and selection_context.source is TodaySelectionSource.LOCAL_DEV_PREVIEW
)

if not is_local_preview:
    return access_state

return ContentAccessState(
    state="full",
    reason=None,
    referral_days_left=None,
    subscription_active=None,
    access_until=None,
)
```

Equivalent Pydantic keyword aliases are allowed; wire result must be exact.

Invariants:

- no mutation of input object;
- denied/global/default returns the same object instance;
- local preview returns a new immutable-use value;
- no settings/env/DB/header/user imports;
- no logging and no side effects;
- a malformed constructed context `source=LOCAL_DEV_PREVIEW, force_v2=False`
  fails closed by preserving access;
- global `force_v2=True, source=GLOBAL_FLAGS` never changes access.

The module may import only:

```text
__future__
app.schemas.access.ContentAccessState
app.services.today_selection_context.TodaySelectionContext/TodaySelectionSource
```

No FastAPI, Request, settings, AccessService or database.

## 7. Route integration

In `apps/api/app/api/day.py`:

1. keep existing guard resolution exactly once;
2. keep existing immutable selection context exactly once;
3. call real `AccessService.can_access_day` exactly once;
4. pass its result and the same `selection_context` into the new pure resolver;
5. pass the resolved access to `TodayService.get_today_payload`;
6. pass the same selection context to TodayService;
7. do not branch directly on headers/settings/user a second time;
8. do not mutate settings or AccessService result;
9. no DB writes.

Required flow:

```py
real_access_state = await access_service.can_access_day(user.id, target_date)
access_state = resolve_today_access_for_selection(
    access_state=real_access_state,
    selection_context=selection_context,
)
payload = await today_service.get_today_payload(
    ...,
    access_state=access_state,
    selection_context=selection_context,
)
```

Variable names may differ but ownership/order must not.

Update day module contract dependencies/invariants to state:

- exact authorized local preview derives full-content access request-locally;
- ordinary/global/denied requests preserve real AccessService result;
- no access ledger/global mutation.

No new logs/events are needed.

## 8. Backend test file

Create a separate file:

```text
apps/api/tests/test_today_preview_access.py
```

Do not grow the existing 997-line transport test.

Required GRACE complete and file <= 700 lines.

### 8.1 Pure resolver matrix

At minimum:

1. preview baseline + exact local context -> exact full/null metadata;
2. locked baseline + exact local context -> exact full/null metadata;
3. full commercial baseline + exact local context -> exact full/null metadata;
4. preview + default global V1 context -> same object, unchanged;
5. preview + global V2 context -> same object, unchanged;
6. preview + malformed local source/force false -> same object, unchanged;
7. input model remains byte/model-dump identical after override;
8. two concurrent resolver calls with local/global contexts are independent;
9. resolver result contains no user/header/profile data;
10. module static imports/ambient/global mutation guard.

### 8.2 ASGI route matrix

Build isolated FastAPI app with dependency overrides and self-contained route
doubles in the new file.

The AccessService double must return `preview/expired_access` by default so the
test reproduces the real blocker.

TodayService recorder must store both:

- received `selection_context`;
- received `access_state`.

It must return a schema-valid response whose `access` equals the received access
and whose V1/V2 identity equals the received selection.

Required route cases:

1. exact direct local marker/identity/transport:
   context local/force V2, access full/null metadata, V2 identity;
2. canonical Next rewrite headers:
   same exact result;
3. missing marker:
   context global/V1, access remains preview/expired;
4. wrong marker:
   access remains preview;
5. ordinary identity:
   access remains preview;
6. public forwarded address/host:
   access remains preview;
7. wrong port:
   access remains preview;
8. production env:
   access remains preview;
9. query-only preview attempt:
   access remains preview;
10. global V2 flag without local preview:
    V2 identity but access remains preview;
11. real baseline locked access + exact local preview:
    full/null override;
12. baseline commercial full + ordinary request:
    exact commercial metadata preserved;
13. overlapping exact preview and ordinary calls:
    local gets full; ordinary gets preview; same globals unchanged;
14. AccessService called once per request;
15. no route/DB global state mutation.

### 8.3 Fail-closed/static assertions

- route source does not inspect query/cookies for access override;
- route access resolver consumes selection context, not raw marker;
- calendar route/client unchanged;
- source contains no `setattr(settings`, AccessLedger insert/grant, ContextVar,
  thread-local or ambient current request;
- full preview reason/subscription/referral/accessUntil all null;
- global V2 source is explicitly covered as no access override.

## 9. Frontend adapter semantics

In `lib/adapters/today-payload.ts`, refine `buildAccess` without any hostname,
query or environment check.

Required mapping:

```text
API full + active subscription markers -> UI subscription
API full + referral markers            -> UI trial
API full + no commercial/trial markers -> UI subscription/unmetered
API preview                             -> UI expired, hasAccess=false
API locked                              -> UI none, hasAccess=false
```

Recommended predicates:

```ts
const isSubscription = subscriptionActive === true || reason === "active_subscription"
const isTrial = reason === "active_referral_days" || referralDaysLeft != null

if (state === "full" && isSubscription) subscription
else if (state === "full" && isTrial) trial
else if (state === "full") subscription
...
```

Order matters. `subscriptionActive=true` wins even if `referralDaysLeft=0`.

No public access contract shape change. No new enum. No generated files.

Update function/module contract if necessary to state unmetered full access maps
to non-trial UI state.

### Adapter tests

In `__tests__/lib/adapt-payload.test.ts` add/adjust:

1. full referral with days -> trial;
2. full reason active_referral_days -> trial;
3. full subscriptionActive -> subscription;
4. full active_subscription reason -> subscription;
5. full with all reason/referral/subscription null -> subscription, hasAccess true,
   daysLeft 0 and accessible;
6. preview/locked unchanged;
7. no mutation of raw access object.

## 10. TodayScreen commercial banner correctness

In `components/today/today-screen.tsx`, render `TrialBanner` only for real UI
state `trial`:

```tsx
access.state === "trial" ? <TrialBanner ... /> : null
```

Do not render a trial banner for `subscription`/unmetered full access. The
current `trial || subscription` condition is misleading for paid/unmetered
users and would show «Осталось 0 дней» in local review.

Update module contract/map wording from generic access card to trial-only access
card if applicable.

Do not hide paywall for `expired`/`none`; accessibility still comes only from
`hasAccess`/`isDayAccessible`.

### TodayScreen tests

In `__tests__/components/TodayScreen.test.tsx`:

- default subscription fixtures must not expect `access-card`;
- section order expectations remove `access-card` for subscription;
- add explicit subscription/unmetered test: ready screen, no access-card, no
  trial-banner;
- retain explicit trial test: banner present with real daysLeft;
- retain locked/paywall tests unchanged;
- prove `data-state=ready` for subscription/unmetered full;
- no arbitrary text-only assertions as sole semantic gate; use testids/states.

Do not broadly rewrite unrelated component tests.

## 11. Strict E2E strengthening

In `e2e/real-v2-preview.spec.ts`, do not weaken any existing assertion.

Add before DOM proof:

```text
payload.access.state = full
payload.access.reason = null
payload.access.referralDaysLeft = null
payload.access.subscriptionActive = null
payload.access.accessUntil = null
```

Add DOM assertion:

```text
today-screen data-state = ready
access-card count = 0
```

The redacted network proof may add only a non-sensitive access summary:

```json
"access": { "state": "full", "commercialReason": false }
```

This addition is optional. If added, update exact artifact validation later.
Never include accessUntil, user identity or raw payload.

Keep:

- exact versions/horizons;
- no interception/fixtures;
- technical disclosures;
- sphere navigation;
- screenshots.

## 12. Security and cache invariants

Implementation must preserve:

- preview access is derived only after the exact existing guard;
- production absolute deny remains first in the guard;
- global V2 rollout does not imply access bypass;
- ordinary request after preview receives its own real access;
- settings and AccessLedger never mutate;
- no new cookie/query selector;
- cache key/hash/version identity unchanged;
- cached payload access is still replaced from current request access by
  existing TodayService behavior;
- prefetch remains context-free and receives no preview access override;
- calendar remains real access-controlled and marker-free;
- no personal data in logs.

## 13. Required implementation gates

Run from repo root.

### 13.1 Exact scope and diff hygiene

```bash
git diff --name-only
git diff --check
git status --short
```

Only exact eight implementation/test paths plus architect docs/frozen paths.

### 13.2 Backend focused

```bash
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/today_preview_access.py \
  apps/api/app/api/day.py \
  apps/api/tests/test_today_preview_access.py

apps/api/.venv/bin/ruff check \
  apps/api/app/services/today_preview_access.py \
  apps/api/app/api/day.py \
  apps/api/tests/test_today_preview_access.py

PYTHONPATH=apps/api apps/api/.venv/bin/mypy --follow-imports=skip \
  apps/api/app/services/today_preview_access.py \
  apps/api/app/api/day.py

apps/api/.venv/bin/python -m py_compile \
  apps/api/app/services/today_preview_access.py \
  apps/api/app/api/day.py \
  apps/api/tests/test_today_preview_access.py

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_access_service.py \
  -q
```

Exact GRACE must pass `3/3`. Focused pytest zero failures.

### 13.3 Full backend

```bash
cd apps/api
source .venv/bin/activate
python -m pytest tests/ -q
```

Zero failures; record exact passed/skipped counts.

### 13.4 Frontend focused

```bash
npx vitest run \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/scripts/preview-v2-real.test.ts

pnpm typecheck
```

Zero failures. Launcher remains 31 passed.

### 13.5 Full frontend and guards

```bash
npx vitest run
pnpm guardrails:prod
pnpm guardrails:frontend
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
```

Important: contract generation must produce zero generated diff because no
public schema changes are authorized.

### 13.6 Isolated build

```bash
NEXT_DIST_DIR=.next-stage1-w4-r1-build pnpm build
```

After success remove only the ignored candidate dist. Do not touch running
production `.next`/`.next-prod` or `.next-v2-real-preview` unless it is already
absent from stopped cleanup.

Prove next-env/tsconfig exact tracked content after build. `next-env` mtime is
non-contractual per 118; bytes/mode/git diff are strict.

## 14. Runtime and git final state

Before callback:

```text
3003 absent
8001 absent
18092 absent
v2-preview window absent
API/sidecar/frontend/nginx PID/start unchanged
tracked implementation diff only exact eight paths
index empty
no commit/push
architect docs 117–119 byte-identical
five frozen unrelated paths untouched
```

Do not restart API. The new backend route code is not live until a later
accepted commit/push + controlled restart wave.

## 15. Success callback

```text
READY_STAGE_1_W4_R1_ACCESS_ARCH_REVIEW
base_sha: 7d37acbaa31118a8545987a39a5fabe18fbb6e32
changed_paths: EXACT_8_IMPLEMENTATION_TEST
new_backend_module: today_preview_access.py
resolver_matrix: PASS
local_preview_access: FULL_NULL_COMMERCIAL_METADATA
ordinary_access: PRESERVED
global_v2_access: PRESERVED
production_denial_access: PRESERVED
concurrency_access_isolation: PASS
access_ledger_writes: ZERO
frontend_unmetered_mapping: SUBSCRIPTION_READY
trial_banner_trial_only: PASS
e2e_access_assertions: STRICT_FULL_AND_NO_ACCESS_CARD
backend_grace: PASS_3_OF_3
backend_focused: <exact>
backend_full: <exact passed/skipped>
frontend_focused: <exact>
frontend_full: <exact>
launcher_unit: 31_PASS
typecheck: PASS
prod_guard: PASS
frontend_guard: PASS
contracts_generated_diff: ZERO
contracts_check: PASS_<exact>
isolated_build: PASS
isolated_dist_removed: YES
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
ports_3003_8001_18092: ABSENT
services_pid_start: UNCHANGED
architect_docs: UNCHANGED_117_TO_119
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
```

Blocked callback:

```text
BLOCKED_STAGE_1_W4_R1_ACCESS
failed_gate: <exact>
safe_observed: <no secrets/personal/raw payload>
runtime_services: UNCHANGED
commit_push: NOT_PERFORMED
```

После callback остановиться. No commit/push/restart/3003 retry until architect
review and a separate acceptance instruction.
