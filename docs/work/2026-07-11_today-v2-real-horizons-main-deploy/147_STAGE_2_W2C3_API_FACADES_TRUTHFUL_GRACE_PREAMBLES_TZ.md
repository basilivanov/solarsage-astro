# Stage 2.W2C-3 — truthful GRACE preambles for frontend API facades

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`
Predecessor: W2C-2 must be accepted, committed and pushed first.

Статус: **PREPARED NEXT WAVE — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Цель и deterministic gate progression

Заменить generic, тестовые и повреждённые leading GRACE preambles в 13
frontend API facade files на правдивые module contracts/maps. Runtime-код не
менять.

Ожидаемый baseline после принятого W2C-2:

```text
21 violations
16 failing paths
31 green paths
47 checked paths
remaining prefixes: lib/api + lib/grace
```

Ожидаемый остаток после W2C-3:

```text
3 violations
3 failing paths
44 green paths
47 checked paths
remaining prefix: lib/grace only
```

## 2. Exact edit allowlist

```text
lib/api/access.ts
lib/api/calendar.ts
lib/api/chat.ts
lib/api/checkin.ts
lib/api/cities.ts
lib/api/config.ts
lib/api/dev-auth-guard.ts
lib/api/horary.ts
lib/api/natal.ts
lib/api/profile-meta.ts
lib/api/profile.ts
lib/api/readings.ts
lib/api/today.ts
```

Edit exact 13 only. Нельзя менять `lib/api/geo.ts`, contracts, callers, hooks,
components, tests, configs, linters, manifests, scripts или docs.

No staging/commit/push. W2C-4 не начинать. После callback остановиться.

## 3. Hard comment-only invariant

Для всех 13 файлов:

- заменить только leading comments/adjacent blank lines до первой runtime
  directive/import/declaration;
- не менять import/export/type/interface/function/constant/string/URL/error
  text, fetch options, schema parsing, date math, logging metadata or aliases;
- не запускать formatter;
- сохранить все существующие body comments/docblocks после canonical preamble,
  если они описывают runtime semantics;
- runtime suffix from first non-comment statement must be byte-identical;
- comment-stripped source must be equivalent;
- imports/exports and existing function/block marker counts must not change.

Текущие повреждённые sequences вида:

```text
// ####// START_MODULE_CONTRACT
// END_MODULE_CONTRACT// AI_HEADER
```

удалить вместе с generic preamble, но не затрагивать следующий runtime/module
docblock.

## 4. Canonical preamble format

Каждый файл получает ровно один AI header в первых 30 строках, один paired
module contract и один paired module map с одним уникальным ID:

```ts
// ############################################################################
// AI_HEADER: <NAME> — <truthful one-line description>
// ROLE: <actual callers and responsibility>
// ############################################################################

// START_MODULE_CONTRACT: <ID>
// purpose: ...
// owns:
//   - exact/path.ts
// inputs: ...
// outputs: ...
// dependencies: ...
// side_effects: ...
// emitted_logs: <exact event or none.>
// invariants:
//   - ...
// failure_policy: ...
// END_MODULE_CONTRACT: <ID>

// START_MODULE_MAP: <same ID>
// public_entrypoints:
//   - ...
// semantic_blocks:
//   - ...
// owned_tests:
//   - exact test path, or none direct.
// END_MODULE_MAP: <same ID>
```

Forbidden generic phrases:

```text
n/a
Function args
Return values
local modules
log and raise
Tests for ... behavior
UI config — component
```

## 5. Exact truthful contracts by facade

Формулировки можно слегка выровнять грамматически, но факты, exports,
failure modes и event names ниже обязательны.

### 5.1. `lib/api/access.ts`

```text
ID: M-FRONTEND-API-ACCESS
AI_HEADER: FRONTEND_API_ACCESS
ROLE: Authenticated access client consumed by use-access and access UI types.
purpose: Fetch AccessSummary and map it into validated AccessInfo.
inputs: no function arguments; NEXT_PUBLIC_API_URL; authenticated browser session.
outputs: exported AccessInfo/AccessState types and Promise<AccessInfo> from getAccess.
dependencies: packages/contracts AccessSummary; lib/contracts/access validator;
              browser fetch and Date.
side_effects: credentialed GET /api/access.
emitted_logs: none.
invariants:
  - trial/subscription map to hasAccess=true.
  - access dates preserve the existing T00:00:00 conversion.
  - daysLeft is referralDaysLeft only for trial; otherwise zero.
  - mapped data passes validateAccessInfo.
failure_policy: throw detail string, detail.message, or generic Failed to get access.
public_entrypoints: AccessInfo, AccessState, getAccess.
semantic_blocks: DATE_PARSE; ACCESS_MAPPING; ACCESS_FETCH.
owned_tests:
  - __tests__/api/access.test.ts
  - __tests__/hooks/useAccess.test.ts
```

### 5.2. `lib/api/calendar.ts`

```text
ID: M-FRONTEND-API-CALENDAR
AI_HEADER: FRONTEND_API_CALENDAR
ROLE: Calendar/day-status facade used by day, calendar and week-strip consumers.
purpose: Fetch one-day status or validated monthly calendar and derive status maps.
inputs: Date; zero-based year/month pair.
outputs: exported calendar/status types; day status; month status map;
         CalendarPayloadReadModel; existing Async aliases.
dependencies: lib/contracts/calendar; packages/contracts CalendarPayload; fetch.
side_effects: credentialed GET /api/day/:date and /api/calendar?month=YYYY-MM.
emitted_logs: none.
invariants:
  - supportive and tense pass through; steady maps to even; other values map null.
  - month argument remains zero-based and is converted with +1.
  - monthly payload remains validated by validateCalendarPayloadReadModel.
  - aliases remain reference-equal to canonical functions.
failure_policy: throw `API error <status>` for non-ok HTTP responses.
public_entrypoints: DayStatus, DayStatusMap, CalendarPayload, getDayStatus,
                    getMonthStatuses, getMonthCalendar and three Async aliases.
semantic_blocks: STATUS_NORMALIZATION; DAY_FETCH; MONTH_STATUS_DERIVATION;
                 MONTH_FETCH; COMPATIBILITY_ALIASES.
owned_tests:
  - __tests__/api/calendar.test.ts
  - __tests__/components/CalendarScreen.test.tsx
  - __tests__/components/WeekStrip.test.tsx
  - __tests__/app/day-page.test.tsx
```

### 5.3. `lib/api/chat.ts`

```text
ID: M-FRONTEND-API-CHAT
AI_HEADER: FRONTEND_API_CHAT
ROLE: Single chat integration facade consumed by use-chat.
purpose: Create a backend thread, send one user message and yield assistant content.
inputs: history, message, context and optional AbortSignal; history/context remain
        compatibility inputs even though current transport does not serialize them.
outputs: AsyncGenerator yielding zero or one assistant content string.
dependencies: lib/contracts/chat; fetch; JSON.
side_effects: credentialed POST /api/chat/threads, then POST its messages endpoint.
emitted_logs: none.
invariants:
  - AbortSignal is passed to both requests.
  - message body contains existing `{ content }` shape.
  - snake_case or camelCase assistant message is accepted.
  - generator yields only when assistant content exists.
failure_policy: throw existing status-bearing Error before yielding when either
                request is non-ok; network/abort errors propagate.
public_entrypoints: ChatContext, ChatMessage, sendMessage.
semantic_blocks: THREAD_CREATE; MESSAGE_SEND; ASSISTANT_YIELD.
owned_tests:
  - __tests__/hooks/useChat.test.ts
```

### 5.4. `lib/api/checkin.ts`

```text
ID: M-FRONTEND-API-CHECKIN
AI_HEADER: FRONTEND_API_CHECKIN
ROLE: Check-in date helpers and credentialed CRUD/metrics facade.
purpose: Resolve local check-in dates and call create/read/yesterday/metrics endpoints.
inputs: Date/timezone/target; CheckinCreate; date key; optional metric range.
outputs: date keys and typed check-in response models.
dependencies: packages/contracts check-in types; Intl; URLSearchParams; fetch.
side_effects: credentialed GET/POST check-in API calls.
emitted_logs: none.
invariants:
  - no-timezone formatting uses local Date getters.
  - timezone formatting uses Intl parts.
  - explicit YYYY-MM-DD target wins; `yesterday` shifts local key by one UTC-safe day.
  - `{checkin:null}` response maps to null.
  - metrics query includes only provided from/to.
failure_policy: throw detail string, detail.message/detail.reason or endpoint fallback.
public_entrypoints: formatDateInTimeZone, resolveCheckinTargetDate, createCheckin,
                    getCheckin, getYesterdayCheckin, getCheckinMetrics.
semantic_blocks: ERROR_DECODE; JSON_RESPONSE; DATE_FORMAT; DATE_SHIFT;
                 TARGET_RESOLUTION; CHECKIN_ENDPOINTS; METRICS_QUERY.
owned_tests:
  - __tests__/api/checkin.test.ts
  - __tests__/components/CheckinScreen.test.tsx
```

### 5.5. `lib/api/cities.ts`

```text
ID: M-FRONTEND-API-CITIES
AI_HEADER: FRONTEND_API_CITIES
ROLE: City catalog/search adapter consumed by onboarding city picker.
purpose: Provide static popular cities and adapt GeoSuggestion results to City.
inputs: query and optional limit.
outputs: City exports and sync/async city arrays.
dependencies: lib/contracts/city; lib/api/geo; lib/log logEvent.
side_effects: async GeoNames-backed request through searchGeoNames; structured
              ui.fetch_failed log on caught search failure.
emitted_logs: ui.fetch_failed.
invariants:
  - synchronous searchCities intentionally remains an empty compatibility result.
  - popular city list and coordinates/timezones remain unchanged.
  - GeoSuggestion fields map to current City fallback/optional fields.
  - failure log meta remains slice=W-GEO, module=M-CITIES-API,
    block=SEARCH_CITIES and contains no personal data.
failure_policy: async search catches/logs and returns []; popular APIs do not throw.
public_entrypoints: City, searchCities, getPopularCities, searchCitiesAsync,
                    getPopularCitiesAsync.
semantic_blocks: GEO_ADAPTER; SYNC_COMPAT_SEARCH; POPULAR_CATALOG;
                 ASYNC_SEARCH; ASYNC_POPULAR_ALIAS.
owned_tests:
  - __tests__/api/cities.test.ts
```

### 5.6. `lib/api/config.ts`

```text
ID: M-FRONTEND-API-CONFIG
AI_HEADER: FRONTEND_API_CONFIG
ROLE: Canonical frontend API base constant; no fixtures or mock transport.
purpose: Resolve API_BASE_URL from NEXT_PUBLIC_API_BASE_URL with /api fallback.
inputs: build/runtime public environment.
outputs: API_BASE_URL string constant.
dependencies: process.env only.
side_effects: none.
emitted_logs: none.
invariants:
  - fallback remains exactly /api.
  - module contains no fixture/mock/stub selection.
failure_policy: missing env uses fallback and does not throw.
public_entrypoints: API_BASE_URL.
semantic_blocks: API_BASE_RESOLUTION.
owned_tests: none direct.
```

### 5.7. `lib/api/dev-auth-guard.ts`

```text
ID: M-FRONTEND-API-DEV-AUTH-GUARD
AI_HEADER: FRONTEND_API_DEV_AUTH_GUARD
ROLE: Security-critical local-host and proxy-origin validation used only by
      dev auth/dev fixture route handlers.
purpose: Fail closed for non-local hosts and untrusted forwarding metadata.
inputs: Host header or Web Request.
outputs: boolean local-host and unsafe-proxy decisions.
dependencies: Web Headers/Request/URL; fixed local/allowed header sets.
side_effects: none.
emitted_logs: none.
invariants:
  - only localhost, 127.0.0.1 and ::1 host forms are local.
  - Forwarded/x-real-ip and unknown x-forwarded-* are unsafe.
  - forwarded host/port/proto must agree with the request.
  - every x-forwarded-for address must be in the fixed local allowlist.
  - absence of suspicious forwarding metadata remains safe.
failure_policy: malformed or mismatched forwarding state returns unsafe=true;
                missing/non-local host returns false from isLocalDevHost.
public_entrypoints: isLocalDevHost, hasUnsafeProxyOriginHeaders.
semantic_blocks: LOCAL_ALLOWLISTS; HOST_NORMALIZATION; HOST_PORT_PARSE;
                 FORWARDING_VALIDATION.
owned_tests:
  - __tests__/api/dev-auth-route.test.ts
  - __tests__/guardrails/preview-isolation.test.ts
```

### 5.8. `lib/api/horary.ts`

```text
ID: M-FRONTEND-API-HORARY
AI_HEADER: FRONTEND_API_HORARY
ROLE: Typed quota/question CRUD facade consumed by horary screens/pages.
purpose: Fetch quota/list/detail and create horary questions with schema validation.
inputs: pagination, question id or HoraryQuestionCreate.
outputs: HoraryQuotaRead, question arrays/detail/null, created question;
         HoraryApiError for typed failures.
dependencies: packages/contracts; lib/contracts/horary Zod schemas; fetch; Response.
side_effects: credentialed horary API GET/POST requests.
emitted_logs: none.
invariants:
  - detail 404 maps to null.
  - 402/NO_HORARY_CREDITS and 409/IDEMPOTENCY_CONFLICT retain Russian messages.
  - list/detail/create responses remain schema-validated.
  - custom error preserves HTTP status and optional backend code.
failure_policy: quota throws existing generic Error; other non-ok responses throw
                HoraryApiError; schema/network errors propagate.
public_entrypoints: HoraryApiError, getHoraryQuota, listHoraryQuestions,
                    getHoraryQuestion, createHoraryQuestion.
semantic_blocks: ERROR_BODY; TYPED_ERROR; ERROR_MESSAGE_PARSE; ERROR_BUILD;
                 QUOTA_FETCH; QUESTION_LIST; QUESTION_DETAIL; QUESTION_CREATE.
owned_tests:
  - __tests__/horary/horary-screen-flow.test.tsx
  - __tests__/horary/horary-error-state.test.tsx
```

### 5.9. `lib/api/natal.ts`

```text
ID: M-FRONTEND-API-NATAL
AI_HEADER: FRONTEND_API_NATAL
ROLE: Typed-result natal preview/generation/report/section client.
purpose: Call natal endpoints, validate success payloads and normalize HTTP,
         contract and network failures into discriminated result objects.
inputs: optional forceRegenerate, reportId and sectionId.
outputs: exported error interfaces and `{ok:true,data}|{ok:false,error}` results.
dependencies: lib/contracts/natal types and Zod schemas; fetch.
side_effects: credentialed natal GET/POST requests.
emitted_logs: none.
invariants:
  - public functions resolve typed results instead of throwing expected failures.
  - 409/501/502/401/404 mappings and existing English wire-facing messages remain.
  - successful payloads remain Zod-validated.
  - Zod failures remain Invalid response format; other caught failures Network error.
  - no payment client or access grant is introduced.
failure_policy: catches request/schema failures and returns current typed error;
                does not log or expose raw response bodies.
public_entrypoints: NatalPreviewError, NatalReportError, NatalGenerateError,
                    fetchNatalPreview, fetchNatalGenerate, fetchNatalReport,
                    fetchNatalReportSection.
semantic_blocks: ERROR_MODELS; ERROR_BODY_PARSE; PREVIEW; GENERATE; REPORT; SECTION.
owned_tests:
  - __tests__/api/natal-report.test.ts
  - __tests__/natal/natal-component-states.test.tsx
  - __tests__/natal/natal-no-english.test.tsx
```

### 5.10. `lib/api/profile-meta.ts`

```text
ID: M-FRONTEND-API-PROFILE-META
AI_HEADER: FRONTEND_API_PROFILE_META
ROLE: Fail-soft aggregator for horary quota and referral profile metadata.
purpose: Fetch quota/referral concurrently and assemble ProfileMeta defaults/partials.
inputs: authenticated browser session.
outputs: Promise<ProfileMeta> and compatibility alias.
dependencies: lib/profile-meta type; Promise.all; fetch.
side_effects: parallel credentialed GET /api/horary/quota and /api/referral.
emitted_logs: none.
invariants:
  - network/non-ok responses preserve existing defaults instead of throwing.
  - successful endpoint data can populate independently of the other endpoint.
  - bonusDays remains referralCount * rewardDays; default rewardDays remains 14.
  - Async alias remains reference-equal.
failure_policy: catches transport failures silently and returns defaults/partials.
public_entrypoints: getProfileMeta, getProfileMetaAsync.
semantic_blocks: DEFAULTS; PARALLEL_FETCH; QUOTA_MAPPING; REFERRAL_MAPPING;
                 PROFILE_META_ASSEMBLY; COMPATIBILITY_ALIAS.
owned_tests:
  - __tests__/api/profile-meta.test.ts
```

### 5.11. `lib/api/profile.ts`

```text
ID: M-FRONTEND-API-PROFILE
AI_HEADER: FRONTEND_API_PROFILE
ROLE: Credentialed profile read/update facade used by profile/onboarding hooks.
purpose: GET or PUT the canonical profile and preserve backend error detail.
inputs: no args for get; ProfileWrite for update; NEXT_PUBLIC_API_URL.
outputs: exported profile types and Promise<ProfileRead>.
dependencies: packages/contracts profile types; fetch; JSON.
side_effects: credentialed GET/PUT /api/profile.
emitted_logs: none.
invariants:
  - update remains PUT with JSON body.
  - success response remains returned without local shape rewriting.
  - error priority remains detail string, detail.message, validation msg array,
    then endpoint fallback.
failure_policy: throw decoded Error on non-ok; network/JSON errors propagate.
public_entrypoints: BirthData, ProfileRead, ProfileWrite, getProfile, updateProfile.
semantic_blocks: ERROR_DECODE; PROFILE_READ; PROFILE_UPDATE.
owned_tests:
  - __tests__/hooks/useProfile.test.ts
  - __tests__/components/OnboardingFlow.test.tsx
  - __tests__/components/OnboardingWelcome.test.tsx
```

### 5.12. `lib/api/readings.ts`

```text
ID: M-FRONTEND-API-READINGS
AI_HEADER: FRONTEND_API_READINGS
ROLE: Past-day reading aggregator and static readings catalog provider.
purpose: Build unlocked reading previews from recent day payloads and expose
         available/coming reading products.
inputs: limit and offset for history; authenticated session.
outputs: ReadingsList; ReadingsCatalog; async catalog alias.
dependencies: readings contracts/catalog types; TodayPayload; lucide icons;
              Date; Promise.all; fetch.
side_effects: parallel credentialed GET /api/day/:date calls for history.
emitted_logs: none.
invariants:
  - requested dates remain prior days derived from offset/limit.
  - failed/non-ok day fetches and locked payloads are omitted.
  - preview remains first reading paragraph or empty string.
  - hasMore remains entries.length === limit.
  - stable catalog keys/copy/icons/order remain unchanged.
failure_policy: per-day transport/non-ok failures return null and are omitted;
                catalog functions do not throw.
public_entrypoints: getReadingsList, listReadings, listReadingsAsync.
semantic_blocks: HISTORY_DATE_PLAN; DAY_FETCH_FAIL_SOFT; HISTORY_ASSEMBLY;
                 PRODUCT_CATALOG; ASYNC_CATALOG_ALIAS.
owned_tests:
  - __tests__/api/readings.test.ts
  - __tests__/components/ReadingsScreen.test.tsx
```

### 5.13. `lib/api/today.ts`

```text
ID: M-FRONTEND-API-TODAY
AI_HEADER: FRONTEND_API_TODAY
ROLE: Minimal date-to-TodayPayload fetch facade and compatibility alias.
purpose: Fetch the canonical day payload for one Date.
inputs: Date.
outputs: Promise<TodayPayload> and getTodayPayloadAsync alias.
dependencies: packages/contracts TodayPayload; fetch.
side_effects: credentialed GET /api/day/YYYY-MM-DD.
emitted_logs: none.
invariants:
  - date path remains UTC ISO YYYY-MM-DD derived by toISOString.
  - success payload is returned unchanged.
  - Async alias remains reference-equal.
failure_policy: non-ok throws detail.message when available, otherwise
                `API error <status>`; network/JSON failures propagate.
public_entrypoints: getTodayPayload, getTodayPayloadAsync.
semantic_blocks: DATE_PATH; DAY_FETCH; COMPATIBILITY_ALIAS.
owned_tests: none direct; canonical day behavior is covered by contract/lib tests.
```

## 6. Mandatory preflight

Before edits:

1. read 141 and 147 completely;
2. prove W2C-2 commit is local/tracking/remote HEAD and main remains ancestor;
3. prove tracked worktree/index clean except frozen untracked paths;
4. run full marker and require exact baseline `21/16/31/47`;
5. require exact 13 allowlisted paths account for 18 violations;
6. save all 13 to `/tmp/stage2-w2c3-before/` preserving relative paths and hashes;
7. record existing imports/exports and body marker counts;
8. prove runtime/services unchanged and ports `3003/8001/18092` absent.

Stop on mismatch. Never reset/rebase/stash/force.

## 7. Mechanical equivalence proof

After edits require for every file:

```text
diff changed lines             comments/adjacent blanks only
runtime suffix SHA             unchanged
comment-stripped source        equivalent
imports/exports                unchanged
public names                   unchanged
existing body markers          unchanged
formatter                      not run
```

Also require:

```text
13 unique paired IDs
one AI_HEADER per file in first 30 lines
canonical fields present 13/13
generic/garbled preamble text absent
cities emitted_logs exactly ui.fetch_failed
all other emitted_logs exactly none
```

## 8. Required gates

### 8.1. GRACE and negative harness

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  lib/api/access.ts \
  lib/api/calendar.ts \
  lib/api/chat.ts \
  lib/api/checkin.ts \
  lib/api/cities.ts \
  lib/api/config.ts \
  lib/api/dev-auth-guard.ts \
  lib/api/horary.ts \
  lib/api/natal.ts \
  lib/api/profile-meta.ts \
  lib/api/profile.ts \
  lib/api/readings.ts \
  lib/api/today.ts
bash scripts/grace/check-negative.sh
```

Expected: self-tests 11 PASS; facade slice 13 clean; negative 6/0 exact reasons.

### 8.2. Static gates

```bash
pnpm lint
pnpm typecheck
```

### 8.3. API/security/downstream regression selection

```bash
npx vitest run \
  __tests__/api/access.test.ts \
  __tests__/api/calendar.test.ts \
  __tests__/api/checkin.test.ts \
  __tests__/api/cities.test.ts \
  __tests__/api/dev-auth-route.test.ts \
  __tests__/api/natal-report.test.ts \
  __tests__/api/profile-meta.test.ts \
  __tests__/api/readings.test.ts \
  __tests__/hooks/useAccess.test.ts \
  __tests__/hooks/useChat.test.ts \
  __tests__/hooks/useProfile.test.ts \
  __tests__/horary/horary-screen-flow.test.tsx \
  __tests__/guardrails/preview-isolation.test.ts
```

Record exact file/test totals; all must pass.

### 8.4. Full marker and aggregate diagnostic

Full marker must prove exactly:

```text
violations=3
failing_paths=3
green_paths=44
checked_paths=47
lib/api failing paths=0
remaining prefix=lib/grace_ONLY
```

`pnpm guardrails:frontend` may be non-zero only on this exact final W2C-4
marker remainder, after ESLint/typecheck succeed.

Run `git diff --check` and exact scope/index/runtime audit.

## 9. Frozen state

Never touch/stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

No systemd/nginx/env/database operations. No commit/push. No W2C-4.

## 10. Required callback

```text
READY_STAGE_2_W2C3_API_FACADES_REVIEW
tracked_scope: EXACT_13_API_FACADES
comment_only_equivalence: PASS_13
runtime_suffix_hashes: UNCHANGED_13
module_ids: UNIQUE_AND_PAIRED_13
authorized_paths_grace: PASS_13
grace_linter_self_tests: 11_PASS
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO
typecheck: PASS
targeted_tests: PASS_<EXACT_FILES_AND_TESTS>
remaining_grace: 3_VIOLATIONS_3_FAILING_44_GREEN_47_CHECKED
remaining_prefixes: LIB_GRACE_ONLY
guardrails_frontend: EXPECTED_FINAL_MARKER_REMAINDER_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
```

После callback остановиться. W2C-4 не начинать.
