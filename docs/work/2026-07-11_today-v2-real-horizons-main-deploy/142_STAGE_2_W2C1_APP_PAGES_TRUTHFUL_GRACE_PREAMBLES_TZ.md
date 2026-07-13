# Stage 2.W2C-1 — truthful GRACE preambles for app pages

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`
Parent: `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`

Статус: **AUTHORIZED COMMENT-ONLY APP-PAGE MIGRATION — NO COMMIT/PUSH**

## 1. Objective and exact expected gate delta

Fix only the 14 app-page paths that currently account for:

```text
17 violations = 14 missing maps + 2 missing contracts + 1 missing header
```

After this packet:

```text
all 14 authorized paths                     GRACE PASS
full active-slice remainder                 32 violations / 27 failing paths
remaining failures                          components/grace + lib/api + lib/grace only
```

No executable code or runtime behavior may change.

## 2. Mandatory preflight

Before editing:

1. read documents 141 and 142 completely;
2. prove branch/local/tracking/remote feature equal the base SHA above;
3. prove `main`/`origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor;
4. prove tracked worktree/index clean;
5. prove only five frozen unrelated untracked paths plus docs 141/142;
6. reproduce the marker baseline as 49 violations / 41 failing paths;
7. record SHA-256 and a copy under `/tmp/stage2-w2c1-before/` for all 14
   authorized paths and both architect docs;
8. prove canonical services unchanged and 3003/8001/18092 absent.

Frozen paths are untouchable:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Stop on mismatch. No reset/rebase/force operation.

## 3. Exact authorized paths

```text
app/(grace)/calendar/page.tsx
app/(grace)/chat/page.tsx
app/(grace)/checkin/page.tsx
app/(grace)/debug/page.tsx
app/(grace)/onboarding/page.tsx
app/(grace)/page.tsx
app/(grace)/profile/page.tsx
app/(grace)/readings/horary/[id]/page.tsx
app/(grace)/readings/horary/page.tsx
app/(grace)/readings/natal/[id]/page.tsx
app/(grace)/readings/natal/generating/page.tsx
app/(grace)/readings/natal/page.tsx
app/(grace)/readings/page.tsx
app/(grace)/today/page.tsx
```

Docs 141/142 remain unchanged and untracked. All other source/config/test files
remain read-only.

## 4. Canonical preamble format

For each authorized file, replace/consolidate only its leading documentation
preamble before the first directive/import with this structure:

```ts
// ############################################################################
// AI_HEADER: <NAME> — <one-line responsibility>
// ROLE: <who calls it and what it coordinates>
// ############################################################################

// START_MODULE_CONTRACT: <MODULE_ID>
// purpose: <truthful purpose>
// owns:
//   - <exact path>
// inputs: <truthful inputs>
// outputs: <truthful output>
// dependencies: <material dependencies>
// side_effects: <network/navigation/state/timers/logging or none>
// emitted_logs: <exact event names or none>
// invariants:
//   - <observable invariant one>
//   - <observable invariant two when needed>
// failure_policy: <actual behavior>
// END_MODULE_CONTRACT: <MODULE_ID>

// START_MODULE_MAP: <MODULE_ID>
// public_entrypoints:
//   - <actual exported entrypoint>
// semantic_blocks:
//   - <BLOCK_NAME>: <owned responsibility>
// owned_tests:
//   - <direct test or none direct>
// END_MODULE_MAP: <MODULE_ID>
```

Rules:

- use the exact IDs and field content specified below;
- one canonical `AI_HEADER`, one module contract and one module map per file;
- remove redundant legacy mini-header comments when present, but no other body
  comments;
- preserve existing START_BLOCK/function contracts byte-for-byte;
- comments may wrap for line length without changing meaning;
- first executable/directive/import line and everything after it remain
  byte-identical to the preflight copy.

## 5. Exact per-file contracts and maps

### 5.1 `app/(grace)/calendar/page.tsx`

```text
AI_HEADER name: APP_CALENDAR_PAGE — monthly calendar route and day-navigation adapter.
ROLE: Client Next.js page called by /calendar; binds access state and converts CalendarScreen date selections into canonical day routes.
MODULE_ID: M-APP-CALENDAR-PAGE
purpose: Render the monthly calendar route and bridge selected Date values to /day/YYYY-MM-DD navigation.
inputs: useAccess result and Date values emitted by CalendarScreen.onOpenDay.
outputs: CalendarScreen with access and onOpenDay props.
dependencies: React useCallback; next/navigation; CalendarScreen; useAccess; toDateParam.
side_effects: Reads access hook state and performs client router.push navigation.
emitted_logs: none.
invariants:
  - Selected days navigate only through toDateParam to /day/YYYY-MM-DD.
  - Calendar rendering and per-day access remain owned by CalendarScreen/API payloads.
failure_policy: Rendering/hook failures bubble to the route boundary; navigation failures are delegated to Next router.
public_entrypoints: CalendarPage (default).
semantic_blocks:
  - ACCESS_BINDING: obtain current access read model.
  - DAY_NAVIGATION: create stable canonical day-route callback.
  - PAGE_COMPOSITION: render CalendarScreen.
owned_tests:
  - e2e/calendar.spec.ts
```

### 5.2 `app/(grace)/chat/page.tsx`

```text
AI_HEADER name: APP_CHAT_PAGE — locked placeholder route for the future assistant.
ROLE: Client Next.js page called by /chat; exposes only a non-interactive coming-soon card.
MODULE_ID: M-APP-CHAT-PAGE
purpose: Render the locked chat placeholder without starting chat API or agent flows.
inputs: none.
outputs: LockedFeatureCard with stable title, description and badge.
dependencies: LockedFeatureCard.
side_effects: none.
emitted_logs: none.
invariants:
  - Route never calls chat APIs while the feature is locked.
  - Coming-soon copy and locked presentation are delegated to LockedFeatureCard.
failure_policy: Rendering errors bubble to the route boundary.
public_entrypoints: ChatPage (default).
semantic_blocks:
  - LOCKED_PLACEHOLDER: render the unavailable assistant state.
owned_tests:
  - none direct.
```

### 5.3 `app/(grace)/checkin/page.tsx`

```text
AI_HEADER name: APP_CHECKIN_PAGE — timezone-aware check-in route composition.
ROLE: Client Next.js page called by /checkin; resolves the target date from profile timezone/query state and hosts CheckinScreen navigation.
MODULE_ID: M-APP-CHECKIN-PAGE
purpose: Render the day check-in route for the canonical target date and navigate back or to the completed day.
inputs: target/date query parameters, current time, and profile current/birth timezone.
outputs: Accessible page shell with back control and CheckinScreen.
dependencies: React useMemo; next/navigation; lucide-react; CheckinScreen; useProfile; resolveCheckinTargetDate.
side_effects: Reads profile hook state and performs router.back/router.push navigation.
emitted_logs: none.
invariants:
  - Target date is resolved only by resolveCheckinTargetDate using the best available profile timezone.
  - Completion navigates to /day/<resolved targetDate>.
  - Icon-only back button retains aria-label=Назад.
failure_policy: Resolver/render failures bubble to the route boundary; submission failures remain owned by CheckinScreen.
public_entrypoints: CheckinPage (default).
semantic_blocks:
  - TARGET_RESOLUTION: derive timezone, query target and canonical date.
  - PAGE_NAVIGATION: back and completion navigation.
  - PAGE_COMPOSITION: render header and CheckinScreen.
owned_tests:
  - __tests__/app/checkin-page.test.tsx
```

### 5.4 `app/(grace)/debug/page.tsx`

```text
AI_HEADER name: APP_DEBUG_PAGE — authenticated frontend/backend diagnostic route.
ROLE: Client Next.js diagnostic page; waits for Telegram auth, fetches /api/debug and renders API-provided session/environment status.
MODULE_ID: M-APP-DEBUG-PAGE
purpose: Display authenticated debug endpoint state for operational diagnosis without mutating user/session data.
inputs: useTelegramAuth state and text/JSON response from GET /api/debug.
outputs: Loading, frontend auth, backend session, user, request and environment diagnostic panels or an error panel.
dependencies: React useEffect/useState; useTelegramAuth; browser fetch/JSON parser.
side_effects: Performs credentialed GET /api/debug, writes React state and emits console.error on fetch/parse failure.
emitted_logs: none (console diagnostic only).
invariants:
  - Debug fetch starts only after auth loading completes.
  - Non-OK HTTP and invalid JSON become visible error state.
  - Page does not write profile, auth or backend data.
failure_policy: Fetch/parse errors are caught and rendered; unexpected render errors bubble to the route boundary.
public_entrypoints: DebugPage (default).
semantic_blocks:
  - AUTH_WAIT: defer diagnostics until authentication settles.
  - DEBUG_FETCH: fetch, parse and classify the backend response.
  - DEBUG_RENDER: render loading/auth/error/backend diagnostic panels.
owned_tests:
  - none direct.
```

### 5.5 `app/(grace)/onboarding/page.tsx`

```text
AI_HEADER name: APP_ONBOARDING_PAGE — onboarding completion and day-route adapter.
ROLE: Client Next.js page called by /onboarding; hosts OnboardingFlow and synchronizes successful completion with onboarded state and the current day route.
MODULE_ID: M-APP-ONBOARDING-PAGE
purpose: Render onboarding and transition a completed profile into the canonical current-day experience.
inputs: OnboardingFlow completion callback, useOnboarded setter and TODAY.
outputs: OnboardingFlow with a stable completion handler.
dependencies: React useCallback; next/navigation; OnboardingFlow; useOnboarded; TODAY; toDateParam.
side_effects: Persists onboarded state through the hook and performs router.replace navigation.
emitted_logs: none (logging is delegated to OnboardingFlow/useOnboarded).
invariants:
  - Successful completion marks onboarded before replacing the route.
  - Destination is /day/<toDateParam(TODAY)>.
failure_policy: Save failures remain in OnboardingFlow; navigation/render errors are delegated to Next/route boundary.
public_entrypoints: OnboardingPage (default).
semantic_blocks:
  - COMPLETION_TRANSITION: synchronize onboarded state and canonical redirect.
  - PAGE_COMPOSITION: render OnboardingFlow.
owned_tests:
  - __tests__/components/OnboardingFlow.test.tsx (indirect flow coverage).
```

### 5.6 `app/(grace)/page.tsx`

```text
AI_HEADER name: APP_HOME_PAGE — root-route redirect to the canonical day path.
ROLE: Client Next.js root page; redirects mounted users to /day/today while rendering a transient spinner.
MODULE_ID: M-APP-HOME-PAGE
purpose: Keep the root route as a compatibility entry that immediately replaces itself with /day/today.
inputs: component mount and Next router.
outputs: transient loading spinner until navigation completes.
dependencies: React useEffect; next/navigation; legacy frontend logger.
side_effects: Emits one structured legacy log envelope and performs router.replace.
emitted_logs: system.request.
invariants:
  - Root route always replaces, never pushes, /day/today.
  - No data/auth API is called by this page.
failure_policy: Router/render failures are delegated to Next/route boundary.
public_entrypoints: HomePage (default).
semantic_blocks:
  - ROOT_REDIRECT: log and replace the root route.
  - TRANSIENT_RENDER: show spinner during navigation.
owned_tests:
  - none direct.
```

### 5.7 `app/(grace)/profile/page.tsx`

```text
AI_HEADER name: APP_PROFILE_PAGE — profile screen data-composition route.
ROLE: Client Next.js page called by /profile; combines access hook state with asynchronously loaded profile meta for ProfileScreen.
MODULE_ID: M-APP-PROFILE-PAGE
purpose: Render ProfileScreen with current access and horary/referral metadata from the real API facade.
inputs: useAccess state and getProfileMeta response.
outputs: ProfileScreen with access, currentState and profileMeta.
dependencies: React useEffect/useState; ProfileScreen; useAccess; getProfileMeta; ProfileMeta.
side_effects: Performs one profile-meta request and updates React state.
emitted_logs: none.
invariants:
  - A complete zero/default ProfileMeta is available before the request resolves.
  - Fetch failure preserves the safe default instead of injecting mock data.
failure_policy: Profile-meta rejection is intentionally absorbed with the default; render errors bubble to the route boundary.
public_entrypoints: ProfilePage (default).
semantic_blocks:
  - DEFAULT_META: initialize honest empty horary/referral values.
  - META_LOAD: replace defaults only after a successful real API response.
  - PAGE_COMPOSITION: render ProfileScreen.
owned_tests:
  - __tests__/components/ProfileScreen.test.tsx (indirect screen contract).
```

### 5.8 `app/(grace)/readings/horary/[id]/page.tsx`

```text
AI_HEADER name: APP_HORARY_ANSWER_PAGE — horary answer loading, polling and error-state route.
ROLE: Client Next.js dynamic page; resolves one question id, polls non-terminal questions and renders progress, answer or honest failure states.
MODULE_ID: M-APP-HORARY-ANSWER-PAGE
purpose: Load and present a single horary question through its complete pending/answered/failed/error lifecycle.
inputs: promised route id and getHoraryQuestion results/errors.
outputs: HoraryProgress, HoraryAnswerView, retryable error UI or terminal failure UI.
dependencies: React hooks/use; next/link; horary view/progress components; getHoraryQuestion; HoraryQuestionRead; logEvent.
side_effects: Performs initial/retry/poll API requests, owns a two-second interval, updates React state and logs classified failures.
emitted_logs: system.error.
invariants:
  - Polling runs only for non-terminal status and retains one 30-second lifecycle per id/status.
  - answered, failed and expired stop polling.
  - Auth/server/network/not-found failures remain visibly distinct.
failure_policy: API failures are classified into route UI states; unexpected render errors bubble to the route boundary.
public_entrypoints: HoraryAnswerPage (default).
semantic_blocks:
  - INITIAL_LOAD: load the question by route id.
  - STATUS_POLLING: poll stable pending status with timeout and cleanup.
  - RETRY: retry recoverable server/network failures.
  - STATE_RENDER: select progress, error, terminal or answer UI.
owned_tests:
  - __tests__/horary/horary-error-state.test.tsx
```

### 5.9 `app/(grace)/readings/horary/page.tsx`

```text
AI_HEADER name: APP_HORARY_PAGE — horary question flow route wrapper.
ROLE: Client Next.js page called by /readings/horary; delegates the complete interactive flow to HoraryScreen.
MODULE_ID: M-APP-HORARY-PAGE
purpose: Expose HoraryScreen at the canonical horary route without duplicating its business logic.
inputs: none at page level.
outputs: HoraryScreen.
dependencies: HoraryScreen.
side_effects: none at page level; delegated to HoraryScreen.
emitted_logs: none at page level.
invariants:
  - Route remains a thin wrapper around the canonical HoraryScreen.
failure_policy: Flow/render failures are delegated to HoraryScreen and the route boundary.
public_entrypoints: HoraryPage (default).
semantic_blocks:
  - PAGE_COMPOSITION: render HoraryScreen.
owned_tests:
  - __tests__/horary/horary-screen-flow.test.tsx (indirect flow coverage).
```

### 5.10 `app/(grace)/readings/natal/[id]/page.tsx`

```text
AI_HEADER name: APP_NATAL_REPORT_PAGE — full natal report state and section route.
ROLE: Client Next.js dynamic page; loads one report id, maps backend generation/failure states, supports retry and renders typed report blocks.
MODULE_ID: M-APP-NATAL-REPORT-PAGE
purpose: Present the full natal report lifecycle and ready report sections for a specific report id.
inputs: promised route id, fetchNatalReport results and forced fetchNatalGenerate retry results.
outputs: loading, not-found, generating, retryable/permanent failure or ready full-report UI.
dependencies: React hooks/use; next/link; framer-motion; lucide-react; natal API facade; shared natal contracts; mapCalloutTone.
side_effects: Performs report/generation requests and updates local page/section state.
emitted_logs: none.
invariants:
  - Backend statuses map to explicit PageState variants without demo fallback.
  - Retry is offered only for retryable failures.
  - Ready sections and backend blocks render from typed contract data.
failure_policy: API result errors become honest page states; unexpected rendering errors bubble to the route boundary.
public_entrypoints: NatalReportPage (default).
semantic_blocks:
  - REPORT_LOAD: fetch and classify report state.
  - RETRY_GENERATION: force retry and transition to returned backend state.
  - STATE_RENDER: render loading/error/generating/ready branches.
  - SECTION_NAVIGATION: select and move between report sections.
  - BLOCK_RENDERING: render typed backend paragraph/callout/list/pros-cons blocks.
owned_tests:
  - __tests__/natal/natal-component-states.test.tsx
```

### 5.11 `app/(grace)/readings/natal/generating/page.tsx`

```text
AI_HEADER name: APP_NATAL_GENERATING_PAGE — natal preview, generation and polling route.
ROLE: Client Next.js generation page; loads real preview context, starts generation, polls report status and routes ready reports.
MODULE_ID: M-APP-NATAL-GENERATING-PAGE
purpose: Coordinate the asynchronous natal full-report generation lifecycle with preview context and recoverable failure UI.
inputs: fetchNatalPreview, fetchNatalGenerate and fetchNatalReport results plus user retry/back actions.
outputs: preview-backed starting/generating/retryable/permanent/error UI or redirect to the ready report.
dependencies: React hooks; next/navigation; natal API facade; NatalPreviewRead.
side_effects: Performs preview/generate/poll requests, owns timeout handles, updates React state and navigates with router.replace/back.
emitted_logs: none.
invariants:
  - Poll cadence is 3 seconds with at most 60 attempts.
  - READY routes to /readings/natal/<reportId>.
  - Timeout and retryable/permanent failures remain distinguishable.
  - Timers and cancelled async work are cleaned up.
failure_policy: Typed API failures become explicit GenState/PreviewState UI; unexpected render errors bubble to the route boundary.
public_entrypoints: NatalGeneratingPage (default).
semantic_blocks:
  - PREVIEW_LOAD: load real preview context.
  - GENERATION_START: request or resume report generation.
  - STATUS_POLLING: poll bounded report status with cleanup.
  - RETRY_AND_BACK: handle recovery/navigation actions.
  - STATE_RENDER: render generation and preview states.
owned_tests:
  - __tests__/natal/natal-component-states.test.tsx
```

### 5.12 `app/(grace)/readings/natal/page.tsx`

```text
AI_HEADER name: APP_NATAL_PREVIEW_PAGE — real natal preview route and state renderer.
ROLE: Client Next.js page called by /readings/natal; loads the real preview contract and composes all preview states and sections.
MODULE_ID: M-APP-NATAL-PREVIEW-PAGE
purpose: Fetch and render the natal preview, including incomplete-profile, failure and ready states.
inputs: fetchNatalPreview result and retry action.
outputs: stable natal-preview screen with loading, profile-incomplete, error or ready content.
dependencies: React hooks; next/link; natal preview components/chart; fetchNatalPreview; NatalPreviewRead.
side_effects: Performs preview API requests and updates React state.
emitted_logs: none.
invariants:
  - data-testid=natal-preview-screen exposes data-state for every state.
  - Ready content uses only the real typed preview response.
  - Retry reuses the same canonical load callback.
failure_policy: Profile/API failures become explicit accessible UI; unexpected render errors bubble to the route boundary.
public_entrypoints: NatalReadingPage (default).
semantic_blocks:
  - PREVIEW_LOAD: fetch and classify preview result.
  - STATE_ATTRIBUTES: expose stable screen state contract.
  - READY_COMPOSITION: render hero, insights, chart, spheres, planets, locked chapters and CTA.
owned_tests:
  - __tests__/natal/natal-component-states.test.tsx
  - __tests__/natal/natal-no-english.test.tsx
```

### 5.13 `app/(grace)/readings/page.tsx`

```text
AI_HEADER name: APP_READINGS_PAGE — readings catalogue route wrapper.
ROLE: Client Next.js page called by /readings; delegates catalogue UI and navigation to ReadingsScreen.
MODULE_ID: M-APP-READINGS-PAGE
purpose: Expose the canonical readings catalogue without duplicating screen logic.
inputs: none at page level.
outputs: ReadingsScreen.
dependencies: ReadingsScreen.
side_effects: none at page level; delegated to ReadingsScreen.
emitted_logs: none at page level.
invariants:
  - Route remains a thin wrapper around ReadingsScreen.
failure_policy: Screen/render failures are delegated to ReadingsScreen and the route boundary.
public_entrypoints: ReadingsPage (default).
semantic_blocks:
  - PAGE_COMPOSITION: render ReadingsScreen.
owned_tests:
  - none direct.
```

### 5.14 `app/(grace)/today/page.tsx`

```text
AI_HEADER name: APP_TODAY_REDIRECT_PAGE — legacy /today compatibility redirect.
ROLE: Server Next.js page called by /today; redirects all requests to the canonical migrated /day/today route.
MODULE_ID: M-APP-TODAY-REDIRECT-PAGE
purpose: Preserve old /today links while maintaining one canonical real-data day route.
inputs: route request only.
outputs: Next redirect response to /day/today; no rendered page body.
dependencies: next/navigation redirect.
side_effects: Performs server-side navigation control flow.
emitted_logs: none.
invariants:
  - Every invocation redirects exactly to /day/today.
  - Route contains no fixture, auth, API or rendering branch.
failure_policy: Next redirect intentionally terminates rendering through framework control flow.
public_entrypoints: TodayPage (default).
semantic_blocks:
  - COMPATIBILITY_REDIRECT: issue the canonical redirect.
owned_tests:
  - __tests__/app/today-redirect.test.ts
  - __tests__/grace-discipline.test.ts
```

## 6. Comment-only proof

After edits, prove all 14 tracked diffs are documentation-only:

1. every added/deleted nonblank line in `git diff -U0` begins with `//`;
2. first directive/import and all following executable source are byte-identical
   to `/tmp/stage2-w2c1-before/<path>` after removing only the old/new leading
   preamble region;
3. no string literal, import, type, JSX, selector, function body or existing
   body comment changed;
4. no duplicate/unpaired module markers exist;
5. existing block/function markers remain paired.

Do not run a formatter.

## 7. Required gates

Run linter self-tests:

```bash
python3 scripts/test_grace_front_lint.py
```

Run the GRACE linter explicitly against all 14 authorized paths and require
zero violations. Then run:

```bash
pnpm lint
pnpm typecheck
bash scripts/grace/check-negative.sh
npx vitest run \
  __tests__/app/checkin-page.test.tsx \
  __tests__/app/today-redirect.test.ts \
  __tests__/horary/horary-error-state.test.tsx \
  __tests__/natal/natal-component-states.test.tsx \
  __tests__/natal/natal-no-english.test.tsx
git diff --check
```

Run full marker gate and capture:

```text
/tmp/stage2-w2c1-full-marker.log
```

Required exact full remainder:

```text
32 violations / 27 failing paths / 20 green paths / 47 checked paths
no app/(grace) failing path remains
remaining failing prefixes only components/grace/, lib/api/, lib/grace/
```

Run `pnpm guardrails:frontend` diagnostically. ESLint/typecheck must pass and it
must stop only at that exact remaining marker inventory.

## 8. Final state and callback

Tracked diff exact 14 authorized app paths. Index empty. Docs 141/142 unchanged.
Frozen paths untouched. No commit/push/runtime/build.

```text
READY_STAGE_2_W2C1_APP_PREAMBLES_REVIEW
tracked_scope: EXACT_14_COMMENT_ONLY
authorized_paths_grace: PASS_14
comment_only_equivalence: PASS
grace_linter_self_tests: PASS
eslint: PASS_ZERO
typecheck: PASS
negative_guard: PASS
targeted_tests: <exact count> PASS
remaining_grace: 32 violations / 27 failing / 47 checked
remaining_prefixes: COMPONENTS_LIB_API_LIB_GRACE_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_docs: UNCHANGED_141_142
```

Then stop for architect review. Do not begin W2C-2.
