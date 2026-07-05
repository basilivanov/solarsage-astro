# Real Data Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the mock-preview visual frontend into the real SolarSage Astro app while keeping all product data backed by real backend/sidecar contracts.

**Architecture:** Use a contract-first vertical-slice migration. FastAPI and SolarSage own facts, contracts, persistence, scoring, and access; the frontend renders typed view models and never calculates production astrology or falls back to runtime mocks. Port presentation from `/opt/solarsage-astro-mock-preview` only after the corresponding real contract exists.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.7, Vitest, Playwright, FastAPI, SQLAlchemy, Pydantic/OpenAPI contracts, PostgreSQL, systemd/Nginx runtime.

## Global Constraints

- Work only in `/opt/solarsage-astro-real-data-preview` on branch `codex/real-data-frontend-migration`.
- Do not implement on `/opt/solarsage-astro` `main`.
- Implementers use `gpt-5.5 high`; task reviewers and final reviewer use `gpt-5.5 xhigh`.
- Keep `/api/*` routed to FastAPI port `8000`; never port the mock-preview `app/api/[...path]/route.ts`.
- Keep production frontend on port `3002` untouched until final cutover.
- Port `3001` to the integration branch only after the branch has real API behavior and no runtime mock API.
- Keep Telegram production auth as Telegram WebApp HMAC -> `/api/auth/telegram`.
- Dev auth stays local-development only and must not be exposed on public hosts.
- SolarSage sidecar owns deterministic astronomical calculation.
- FastAPI owns orchestration, normalization, scoring, access control, persistence, and read-model shaping.
- LLM may phrase or interpret already-computed facts, but must not be the source of deterministic facts.
- Frontend production paths must not import `lib/demo-data`, `lib/demo-mode`, or `lib/mocks/*`.
- Test fixtures may use sample data under test-only paths.
- No production error path may fall back to mock/demo data.
- Do not parse display text such as `topFlags.summary` as structured data.
- Do not compute real astrology in frontend code from local approximations.
- Payment/paywall UI must be hidden or disabled until backed by real YooKassa/access fulfillment.
- Use `apply_patch` for manual file edits.
- Commit after every task with a focused message.
- Before reporting DONE, each implementer must self-review and write the required report file.

---

## Baseline Notes

Fresh worktree baseline:

- `pnpm exec vitest run`: 69 files passed, 786 tests passed, 1 skipped. Existing warnings from Vite CJS deprecation, `Paywall` act warnings, and guard logs are baseline noise.
- `cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q`: 599 passed, 2 skipped, 4 warnings. Existing warnings include Starlette/httpx deprecation and unawaited horary background coroutine warnings in tests.
- `npm run contracts:check`: currently fails because generated OpenAPI/TypeScript contracts are out of sync. The worktree currently contains the generated diff from running `contracts:generate` with `FastAPI 0.136.3`, matching `apps/api/poetry.lock`.

Task 1 owns the current generated-contract diff and must either commit it with the deterministic dependency fix or explicitly replace it with a different deterministic contracts fix.

---

### Task 1: Stabilize Contract Generation Baseline

**Files:**
- Modify: `.gitignore`
- Modify: `apps/api/pyproject.toml`
- Modify: `packages/contracts/openapi.json`
- Modify: `packages/contracts/_generated.ts`
- Test: `scripts/contracts/generate.sh`

**Interfaces:**
- Consumes: `scripts/contracts/generate.sh` uses `apps/api/.venv/bin/python` when present.
- Produces: `npm run contracts:check` passes in a fresh worktree after `python -m venv apps/api/.venv && apps/api/.venv/bin/pip install -e '.[dev]'`.

- [ ] **Step 1: Inspect the current contracts diff**

Run:

```bash
git status --short
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts | sed -n '1,220p'
```

Expected: generated OpenAPI and TypeScript files are modified from the baseline `contracts:check` run.

- [ ] **Step 2: Make backend dependency resolution deterministic**

Change `apps/api/pyproject.toml` dependency:

```toml
"fastapi==0.136.3",
```

Keep the existing `poetry.lock` entry at `0.136.3`; do not update unrelated dependencies.

- [ ] **Step 3: Ignore SDD scratch state**

Add this entry to `.gitignore`:

```gitignore
.superpowers/
```

This prevents controller ledger files from appearing in task diffs.

- [ ] **Step 4: Regenerate contracts**

Run:

```bash
npm run contracts:generate
```

Expected: `packages/contracts/openapi.json` and `packages/contracts/_generated.ts` are the only generated files touched.

- [ ] **Step 5: Verify contract check**

Run:

```bash
npm run contracts:check
```

Expected: PASS with no git diff after the generation check.

- [ ] **Step 6: Verify focused frontend contract tests**

Run:

```bash
pnpm exec vitest run __tests__/contracts/today.test.ts __tests__/contracts/calendar.test.ts __tests__/contracts/natal.test.ts __tests__/contracts/horary.test.ts __tests__/contracts/profile.test.ts
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add .gitignore apps/api/pyproject.toml packages/contracts/openapi.json packages/contracts/_generated.ts
git commit -m "chore: stabilize generated API contracts"
```

### Task 2: Remove Runtime Mock Data From Product Paths

**Files:**
- Modify: `lib/grace/api/client.ts`
- Modify: `lib/api/natal.ts`
- Modify: `lib/api/horary.ts`
- Modify: `lib/api/profile.ts`
- Modify: `lib/api/chat.ts`
- Modify: `hooks/use-telegram-auth.ts`
- Modify: `app/(grace)/readings/natal/generating/page.tsx`
- Modify: `app/(grace)/readings/natal/[id]/page.tsx`
- Modify: `__tests__/api/grace-client.test.ts`
- Modify: `__tests__/api/natal-report.test.ts`
- Modify: `__tests__/natal/natal-component-states.test.tsx`
- Modify: `__tests__/hooks/useTelegramAuth.test.ts`
- Create: `__tests__/guardrails/no-runtime-mocks.test.ts`

**Interfaces:**
- Consumes: real API clients use `apiFetch` or existing fetch wrappers.
- Produces: product runtime paths do not import `lib/demo-data`, `lib/demo-mode`, or `lib/mocks/*`.

- [ ] **Step 1: Write failing runtime-mock guardrail**

Create `__tests__/guardrails/no-runtime-mocks.test.ts` that scans these production roots:

```ts
const roots = ["app/(grace)", "components", "hooks", "lib/api", "lib/adapters", "lib/grace"]
const forbidden = [
  "lib/demo-data",
  "@/lib/demo-data",
  "lib/demo-mode",
  "@/lib/demo-mode",
  "lib/mocks",
  "@/lib/mocks",
]
```

The test must fail if a `.ts` or `.tsx` file under those roots contains a forbidden import path. Exclude test files only; do not exclude production natal, horary, profile, chat, day, or calendar code.

- [ ] **Step 2: Verify red**

Run:

```bash
pnpm exec vitest run __tests__/guardrails/no-runtime-mocks.test.ts
```

Expected: FAIL showing existing runtime imports in `lib/api/*`, `lib/grace/api/client.ts`, and natal pages.

- [ ] **Step 3: Remove day/calendar demo fallbacks**

Update `lib/grace/api/client.ts` so:

- it no longer imports `IS_DEMO_MODE`;
- it no longer imports `DEMO_TODAY_RESPONSE` or `DEMO_CALENDAR_RESPONSE`;
- `fetchDay()` always performs the real request;
- `fetchCalendar()` always performs the real request;
- API errors propagate as errors instead of falling back to sample data.

- [ ] **Step 4: Remove natal demo fallbacks**

Update `lib/api/natal.ts` so:

- it no longer imports `IS_DEMO_MODE`, `DEMO_NATAL_PREVIEW`, or `MOCK_NATAL_REPORT_READ`;
- `fetchNatalPreview()` always calls `GET /api/natal/preview`;
- `generateNatalReport()` always calls the backend generation endpoint;
- report fetch/section functions always call backend endpoints;
- `reportId === "demo"` is treated as a normal invalid report id path and returns the same not-found/error behavior as any invalid id.

Update natal API tests to assert real fetch behavior and remove tests that expect demo data in production clients.

- [ ] **Step 5: Remove horary/profile/chat demo fallbacks**

Update:

- `lib/api/horary.ts`: remove demo quota, demo question list, demo question detail, and demo create behavior.
- `lib/api/profile.ts`: remove `DEMO_PROFILE` fallback.
- `lib/api/chat.ts`: remove demo assistant reply behavior.

Tests should mock `fetch`, not runtime demo modules.

- [ ] **Step 6: Remove Telegram auth demo bypass**

Update `hooks/use-telegram-auth.ts` so production behavior uses Telegram HMAC auth and local development behavior uses the existing local dev-auth path. Remove `IS_DEMO_MODE` and any path that marks a session authenticated without a real backend session.

- [ ] **Step 7: Remove natal page demo branches**

Update:

- `app/(grace)/readings/natal/generating/page.tsx`
- `app/(grace)/readings/natal/[id]/page.tsx`

The generating page must use real preview data when available and render a loading/error state when it is not. It must not redirect to `/readings/natal/demo` or simulate completion from demo mode.

- [ ] **Step 8: Keep production guard only for environment safety**

Keep `lib/env/production-guard.*` and its tests if they still guard unsafe environment variables. The production guard may mention `NEXT_PUBLIC_DEMO_MODE`, but product runtime routes and API clients must not branch to demo data.

- [ ] **Step 9: Verify**

Run:

```bash
pnpm exec vitest run __tests__/guardrails/no-runtime-mocks.test.ts __tests__/api/grace-client.test.ts __tests__/api/natal-report.test.ts __tests__/api/profile-meta.test.ts __tests__/api/readings.test.ts __tests__/hooks/useTelegramAuth.test.ts
```

Expected: all selected tests pass.

- [ ] **Step 10: Commit**

Run:

```bash
git add app components hooks lib __tests__
git commit -m "refactor: remove runtime demo data from product paths"
```

### Task 3: Make Profile And Access Real-Data First

**Files:**
- Modify: `hooks/use-profile.ts`
- Modify: `lib/profile.ts`
- Modify: `lib/api/profile.ts`
- Modify: `components/profile/edit-sheet.tsx`
- Modify: `components/profile/profile-screen.tsx`
- Modify: `hooks/use-access.ts`
- Modify: `lib/api/access.ts`
- Create: `apps/api/app/api/access.py`
- Modify: `apps/api/app/api/__init__.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/schemas/access.py`
- Test: `__tests__/hooks/useProfile.test.ts`
- Test: `__tests__/lib/profile.test.ts`
- Test: `__tests__/api/access.test.ts`
- Test: `apps/api/tests/test_profile_endpoints.py` or create focused backend access tests

**Interfaces:**
- Consumes: existing `/api/profile` read/write behavior and access services.
- Produces: profile UI hydrates from backend first, persists edits through backend, and access state is not localStorage-synthetic.

- [ ] **Step 1: Write failing frontend tests**

Update tests so `useProfile`:

- calls `GET /api/profile` on mount;
- maps API birth date/time/place/gender/name into the UI profile model;
- does not return fake Kyiv/Lisbon defaults when backend profile is empty;
- calls `PUT /api/profile` when profile edits are saved;
- preserves latitude, longitude, timezone, and city display values.

- [ ] **Step 2: Write failing access tests**

Add or update tests so `useAccess` reads real API state via `lib/api/access.ts` and does not derive subscription/access from localStorage.

- [ ] **Step 3: Add backend access read model**

Add `GET /api/access` returning the access summary needed by `useAccess`. Source it from the existing backend access service rather than frontend state.

- [ ] **Step 4: Implement profile API mapping**

Update `lib/profile.ts`, `lib/api/profile.ts`, and `hooks/use-profile.ts` so API fields are the source of truth. Local storage may cache the last successful real profile for display continuity, but it must not create fake identities or fake birth locations.

- [ ] **Step 5: Persist edits**

Update `components/profile/edit-sheet.tsx` and `components/profile/profile-screen.tsx` so saving calls the profile hook/API write path and surfaces backend validation errors.

- [ ] **Step 6: Hide dev access controls outside development**

Ensure `components/profile/dev-mode-switcher.tsx` is not shown outside local development.

- [ ] **Step 7: Regenerate contracts**

Run:

```bash
npm run contracts:generate
```

- [ ] **Step 8: Verify**

Run:

```bash
pnpm exec vitest run __tests__/hooks/useProfile.test.ts __tests__/lib/profile.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_profile_endpoints.py -q
npm run contracts:check
```

Expected: all selected tests and contract check pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add app components hooks lib apps/api packages/contracts __tests__
git commit -m "feat: load profile and access from real API"
```

### Task 4: Add Day And Calendar Real Read Models

**Files:**
- Modify: `apps/api/app/schemas/today.py`
- Modify: `apps/api/app/schemas/calendar.py`
- Modify: `apps/api/app/services/today_service.py`
- Modify: `apps/api/app/services/calendar_service.py`
- Modify: `apps/api/app/services/astro_utils.py`
- Modify: `lib/contracts/today.ts`
- Modify: `lib/contracts/calendar.ts`
- Modify: `lib/adapters/today-payload.ts`
- Modify: `lib/api/calendar.ts`
- Test: `apps/api/tests/test_day_endpoints.py`
- Test: `apps/api/tests/test_calendar_endpoints.py`
- Test: `__tests__/lib/adapt-payload.test.ts`
- Test: `__tests__/api/calendar.test.ts`
- Test: `__tests__/contracts/today.test.ts`
- Test: `__tests__/contracts/calendar.test.ts`

**Interfaces:**
- Consumes: existing natal context, transits, normalization, scoring, and current calendar endpoint.
- Produces: typed day/calendar payload fields needed by migrated UI, without client astrology calculations.

- [ ] **Step 1: Add failing backend tests for `dayChart`**

Extend day endpoint tests to assert `/api/day/{date}` includes a nullable or populated `dayChart` object with:

- `houses[]` containing house number, cusp longitude, and sign;
- `transitPlanets[]` containing name, longitude, sign, retrograde/motion data when available, and computed house when possible;
- `aspects[]` containing planet names, aspect type, orb, and strength when available;
- `source: "solarsage"`.

- [ ] **Step 2: Add failing backend tests for calendar real fields**

Extend calendar endpoint tests to assert `CalendarPayload.days[]` preserves per-day `access`, exposes a deterministic status from backend scoring, and exposes nullable lunar fields when the lunar service cannot compute them yet. The test must not accept the existing neutral 5-day rotation as a real implementation.

- [ ] **Step 3: Add schemas**

Add explicit Pydantic schemas for day chart, planet influence/sphere score fields, and calendar lunar fields. Use `None` when the backend lacks data rather than inventing facts.

- [ ] **Step 4: Build day chart from existing real sources**

In `TodayService`, use the existing natal context and sidecar transit result already retrieved during day calculation. Map longitudes to houses through backend utility code when sidecar does not provide house. Do not make an extra sidecar call for the same day request unless the existing data is absent.

- [ ] **Step 5: Replace calendar rotation with backend-derived status**

Update `CalendarService` so day status comes from real scoring/read-model data. If full day calculation per month is too expensive, add a constrained backend summary path using existing scoring primitives and cache it; do not use the old neutral rotation.

- [ ] **Step 6: Regenerate and wire contracts**

Run:

```bash
npm run contracts:generate
```

Update frontend contract shims and adapters to expose the new fields without `any`.

- [ ] **Step 7: Verify**

Run:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_endpoints.py tests/test_calendar_endpoints.py tests/test_today_important.py -q
pnpm exec vitest run __tests__/lib/adapt-payload.test.ts __tests__/api/calendar.test.ts __tests__/contracts/today.test.ts __tests__/contracts/calendar.test.ts
npm run contracts:check
```

Expected: all selected tests and contract check pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add apps/api lib packages/contracts __tests__
git commit -m "feat: expose real day and calendar read models"
```

### Task 5: Port Day And Calendar Presentation To Real Data

**Files:**
- Create or modify: `components/today/day-chart.tsx`
- Create or modify: `components/today/day-energy-meter.tsx`
- Create or modify: `components/today/day-summary-card.tsx`
- Modify: `components/today/today-screen.tsx`
- Modify: `components/calendar/calendar-screen.tsx`
- Create or modify: `components/calendar/lunar-calendar-strip.tsx`
- Modify: `app/globals.css`
- Test: `__tests__/components/TodayScreen.test.tsx`
- Create: `__tests__/components/CalendarScreen.test.tsx`
- Modify: `e2e/today.spec.ts`
- Create: `e2e/calendar.spec.ts`

**Interfaces:**
- Consumes: Task 4 `dayChart`, influence fields, per-day calendar access, and lunar fields.
- Produces: migrated day/calendar UI with no static astrology, no topFlags text parsing, and no mock-preview API.

- [ ] **Step 1: Port presentation components as pure renderers**

Use mock-preview files only as visual reference:

- `/opt/solarsage-astro-mock-preview/components/today/day-chart.tsx`
- `/opt/solarsage-astro-mock-preview/components/today/day-energy-meter.tsx`
- `/opt/solarsage-astro-mock-preview/components/today/day-summary-card.tsx`
- `/opt/solarsage-astro-mock-preview/components/calendar/lunar-calendar-strip.tsx`

Do not port `deriveChartAndEnergy`, static natal arrays, date-offset planet motion, `lib/moon.ts`, `lib/retrograde.ts`, or `lib/planetary-day.ts`.

- [ ] **Step 2: Write failing component tests**

Tests must verify:

- `DayChart` renders non-empty SVG content from supplied real chart props;
- `DayChart` renders an unavailable state when chart data is absent;
- `DayEnergyMeter` renders supplied structured influence scores;
- day summary renders backend lunar/summary facts and does not compute them locally;
- calendar uses per-day access and lunar fields from API view models.

- [ ] **Step 3: Wire `TodayScreen`**

Update `components/today/today-screen.tsx` so it passes adapted real fields into the new presentation components. Keep existing loading/error/auth behavior.

- [ ] **Step 4: Wire calendar**

Update `components/calendar/calendar-screen.tsx` to use full `CalendarPayload.days[]`, per-day access, backend status, and backend lunar fields. The lunar strip/toggle must hide or show an unavailable state when lunar fields are absent.

- [ ] **Step 5: Port only necessary CSS**

From mock-preview `app/globals.css`, port only classes needed by the migrated components, such as chart/energy/header/section/toggle classes. Do not replace global theme, auth layout, or full CSS file.

- [ ] **Step 6: Verify**

Run:

```bash
pnpm exec vitest run __tests__/components/TodayScreen.test.tsx __tests__/lib/adapt-payload.test.ts __tests__/api/calendar.test.ts
pnpm exec tsc --noEmit
```

Run the day/calendar Playwright smoke with `E2E_BASE_URL` pointed at the local preview server started for this task.

- [ ] **Step 7: Commit**

Run:

```bash
git add app components lib __tests__ e2e
git commit -m "feat: port day and calendar UI to real data"
```

### Task 6: Add Check-In Real Contract And UI

**Files:**
- Modify: `apps/api/app/db/models.py`
- Create or modify Alembic migration under `apps/api/alembic/versions/`
- Modify: `apps/api/app/schemas/checkin.py`
- Modify: `apps/api/app/services/checkin_service.py`
- Modify: `apps/api/app/api/checkin.py`
- Create: `lib/api/checkin.ts`
- Create or modify: `app/(grace)/checkin/page.tsx`
- Create or modify check-in components from mock-preview as pure UI
- Modify: `components/profile/profile-screen.tsx`
- Create or modify: `components/profile/checkin-statistics.tsx`
- Test: `apps/api/tests/test_checkin_endpoints.py`
- Test: frontend check-in tests

**Interfaces:**
- Consumes: user profile timezone when available.
- Produces: real check-in write/read/yesterday/metrics flow and profile check-in statistics.

- [ ] **Step 1: Write failing backend tests**

Tests must cover:

- POST check-in with numeric `mood`, `accuracy`, `energy`, `tags`, `note`, and local `targetDate`;
- same user/date upsert behavior;
- `GET /api/checkin/{target_date}`;
- `GET /api/checkin/yesterday`;
- `GET /api/checkin/metrics`;
- local/profile timezone date semantics.

- [ ] **Step 2: Extend database and schemas**

Add fields for numeric mood, accuracy, energy, tags, note, filled-at timestamp, and streak/metric support. Preserve readable migration behavior for existing rows with old string `mood` and `notes`.

- [ ] **Step 3: Implement service and API endpoints**

Implement the extended check-in service and endpoints. Do not derive dates with UTC `toISOString().split("T")[0]` semantics.

- [ ] **Step 4: Add frontend API client and tests**

Create `lib/api/checkin.ts` with real HTTP calls only. Add tests for request payloads, local date handling, and error handling.

- [ ] **Step 5: Port check-in UI**

Port check-in selectors and screen UX from mock-preview only as presentation. Wire all submit/load/stats behavior to `lib/api/checkin.ts`.

- [ ] **Step 6: Wire profile stats**

Port `components/profile/checkin-statistics.tsx` and show it only from real `/api/checkin/metrics` data.

- [ ] **Step 7: Regenerate contracts and verify**

Run:

```bash
npm run contracts:generate
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py -q
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx __tests__/hooks/useProfile.test.ts
npm run contracts:check
```

- [ ] **Step 8: Commit**

Run:

```bash
git add app components lib apps/api packages/contracts __tests__
git commit -m "feat: add real check-in flow"
```

### Task 7: Add Natal Chart Preview Contract And UI

**Files:**
- Modify: `apps/api/app/schemas/natal.py`
- Modify: `apps/api/app/services/natal_service.py`
- Modify: `apps/api/app/services/natal_report_service.py`
- Modify: `apps/api/app/api/natal.py`
- Modify: `lib/contracts/natal.ts`
- Modify: `lib/api/natal.ts`
- Create or modify: `components/readings/natal-chart-wheel.tsx`
- Modify: `app/(grace)/readings/natal/page.tsx`
- Test: `apps/api/tests/test_natal_endpoints.py`
- Test: `__tests__/contracts/natal.test.ts`
- Test: `__tests__/api/natal-report.test.ts`
- Test: natal component tests

**Interfaces:**
- Consumes: `NatalContextData` real planets, houses, aspects, angles.
- Produces: `NatalPreviewRead.chart` and a real-data `NatalChartWheel`.

- [ ] **Step 1: Write failing backend tests for preview chart**

Assert `GET /api/natal/preview` includes `chart` with planets, houses, aspects, angles, and house system from real natal context. The chart may be `null` only for profile-incomplete/error states.

- [ ] **Step 2: Add invalid report id backend handling**

Add a test for non-UUID report IDs and implement a stable 404/422 response instead of uncaught `uuid.UUID(report_id)` errors.

- [ ] **Step 3: Extend schemas and service**

Add `NatalPreviewChart` schemas and populate from `NatalContextData`. Do not include demo report IDs or mock report fallbacks.

- [ ] **Step 4: Port chart wheel**

Use `/opt/solarsage-astro-mock-preview/components/readings/natal-chart-wheel.tsx` as visual reference. The production component must render only supplied `preview.chart`; it must not import `DEMO_NATAL_RESPONSE` or compute fake chart data.

- [ ] **Step 5: Keep radar gated**

Do not port the planetary strength radar unless backend-computed planet strength data is added in this task. If not added, leave that UI hidden.

- [ ] **Step 6: Verify**

Run:

```bash
npm run contracts:generate
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_natal_endpoints.py -q
pnpm exec vitest run __tests__/contracts/natal.test.ts __tests__/api/natal-report.test.ts __tests__/natal/natal-component-states.test.tsx
npm run contracts:check
```

- [ ] **Step 7: Commit**

Run:

```bash
git add app components lib apps/api packages/contracts __tests__
git commit -m "feat: render natal chart from real preview data"
```

### Task 8: Add Horary Chart Snapshot Contract And UI

**Files:**
- Modify: `apps/api/app/db/models.py`
- Create or modify Alembic migration under `apps/api/alembic/versions/`
- Modify: `apps/api/app/schemas/horary.py`
- Modify: `apps/api/app/services/horary_service.py`
- Modify: `apps/api/app/api/horary.py`
- Modify: `lib/contracts/horary.ts`
- Modify: `lib/api/horary.ts`
- Create or modify: `components/readings/horary/horary-chart.tsx`
- Modify: `components/readings/horary/horary-answer-view.tsx`
- Test: `apps/api/tests/test_horary_endpoints.py`
- Test: `__tests__/contracts/horary.test.ts`
- Test: horary component tests

**Interfaces:**
- Consumes: real horary chart generated during question creation.
- Produces: immutable persisted chart snapshot returned in `HoraryQuestionRead` and rendered in answer view.

- [ ] **Step 1: Write failing backend tests for chart snapshot**

Assert that when horary answer generation computes a chart, the chart snapshot is persisted and later returned by get/list endpoints. Include houses, planets, aspects, location/time metadata, and source.

- [ ] **Step 2: Add persistence**

Add a JSON chart snapshot column or normalized storage following existing model conventions. Preserve existing rows by returning `chart: null` for old questions.

- [ ] **Step 3: Store chart from real generation path**

Update `HoraryService` so it persists the actual generated chart, not a reconstructed chart from `createdAt`.

- [ ] **Step 4: Port chart UI**

Use `/opt/solarsage-astro-mock-preview/components/readings/horary/horary-chart.tsx` as visual reference only. Remove pseudo data derivation and render only the backend chart snapshot.

- [ ] **Step 5: Fix purchase refresh semantics if touched**

If horary purchase UI is modified, ensure success is not inferred from pre-existing credits and quota refreshes after confirmed payment/credit changes.

- [ ] **Step 6: Verify**

Run:

```bash
npm run contracts:generate
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_horary_endpoints.py -q
pnpm exec vitest run __tests__/contracts/horary.test.ts __tests__/horary/horary-answer-view.test.tsx __tests__/horary/horary-screen-flow.test.tsx
npm run contracts:check
```

- [ ] **Step 7: Commit**

Run:

```bash
git add app components lib apps/api packages/contracts __tests__
git commit -m "feat: render horary charts from persisted snapshots"
```

### Task 9: Gate Payment/Paywall UI Until Real Fulfillment Exists

**Files:**
- Modify: `components/monetization/paywall.tsx`
- Modify: `components/paywall.tsx`
- Modify: `components/readings/horary/horary-purchase-sheet.tsx`
- Modify: `components/readings/natal-preview/cta-button.tsx`
- Modify: `lib/api/natal.ts`
- Modify: `apps/api/app/api/payment.py`
- Modify: `apps/api/app/services/payment_service.py`
- Test: payment/paywall frontend tests
- Create: `apps/api/tests/test_payment_endpoints.py`

**Interfaces:**
- Consumes: current MVP payment backend.
- Produces: no live purchase path is shown unless backend supports real catalog, YooKassa confirmation, webhook verification, idempotent fulfillment, and access/credit grant.

- [ ] **Step 1: Write failing UI tests for gating**

Add tests that assert paywall/purchase surfaces are hidden or disabled when the backend does not expose real products/fulfillment state.

- [ ] **Step 2: Remove mock-preview subscription assumptions**

Do not port `/api/payment/subscription/start`, `/status`, `/cancel`, `/products`, or `/purchase/start` clients unless the backend endpoints are actually implemented with real YooKassa semantics.

- [ ] **Step 3: Gate horary and natal purchase CTAs**

Horary and natal screens may show unavailable/coming-soon or disabled paid states. They must not promise a completed purchase flow unless the backend can fulfill it.

- [ ] **Step 4: Add credential hygiene check**

Update guardrails or tests so tracked docs do not contain real-looking YooKassa live credentials. If real-looking credentials are present, redact them in docs and note that rotation is required operationally.

- [ ] **Step 5: Verify**

Run:

```bash
pnpm exec vitest run __tests__/components/Paywall.test.tsx __tests__/horary/horary-purchase-sheet.test.tsx
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_payment_endpoints.py -q
```

- [ ] **Step 6: Commit**

Run:

```bash
git add app components lib apps/api docs __tests__ scripts
git commit -m "fix: gate payment UI behind real fulfillment"
```

### Task 10: Real-Data Preview Runtime And Final Acceptance

**Files:**
- Create or modify: `infra/systemd/solarsage-frontend-preview-3001.service`
- Create or modify: `scripts/preview-3001-smoke.sh`
- Modify: `docs/superpowers/specs/2026-07-05-real-data-frontend-migration-design.md`
- Test: unit/backend/contracts/e2e acceptance

**Interfaces:**
- Consumes: all previous migrated contracts and UI.
- Produces: port `3001` can run the integration branch against API `8000` without mock-preview runtime.

- [ ] **Step 1: Add preview service artifact**

Create a repo-tracked systemd unit template for `solarsage-frontend-preview-3001.service` that:

- uses `WorkingDirectory=/opt/solarsage-astro-real-data-preview`;
- runs production build/start or a controlled preview start on `127.0.0.1:3001`;
- keeps `/api/*` behavior routed to FastAPI `8000` through Next/Nginx, not a mock API.

Do not edit `/etc/systemd/system` from the implementer task.

- [ ] **Step 2: Add preview smoke script**

Create `scripts/preview-3001-smoke.sh` that verifies:

- `http://127.0.0.1:3001/day/2026-07-05` returns app HTML;
- `http://127.0.0.1:3001/calendar` returns app HTML;
- Next static assets referenced by the HTML return 200;
- `/api/health` still resolves to FastAPI when accessed through the configured public route, if a route is available.

- [ ] **Step 3: Run full local acceptance**

Run:

```bash
pnpm exec vitest run
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
npm run contracts:check
pnpm exec tsc --noEmit
npm run build
```

Expected: all commands pass. Baseline warnings already listed in this plan may remain; new warnings from this task must be fixed or justified in the report.

- [ ] **Step 4: Run real-HMAC Playwright smoke where available**

Use the existing generator:

```bash
python3 scripts/generate-telegram-test-initdata.py
```

Then run the existing Playwright smoke suite against `3001` if the preview server is running:

```bash
E2E_BASE_URL=http://127.0.0.1:3001 pnpm exec playwright test --project=chromium
```

If the environment cannot run the preview server or browser, report the exact blocker and the closest smoke commands that did run.

- [ ] **Step 5: Commit**

Run:

```bash
git add infra scripts docs
git commit -m "chore: add real-data preview runtime checks"
```
