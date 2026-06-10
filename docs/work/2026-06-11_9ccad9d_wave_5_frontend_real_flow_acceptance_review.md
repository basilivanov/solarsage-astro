# Acceptance Review: 9ccad9d — Wave 5 Frontend Real Flow Fixes

Date: 2026-06-11
Status: ACCEPTED
Reviewed commit: `9ccad9d18e2347e59516140e4f04b6516aaed525`
Branch: `feat/natal-full-report`
Previous Wave 5 review: `docs/work/2026-06-11_57c5056_wave_5_frontend_real_flow_review.md`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Scope reviewed

This review checks commit `9ccad9d` against the 3 blockers and 4 risks from the previous Wave 5 review:

1. Generating-page retry must start a new generation with `forceRegenerate=true`.
2. Production `/readings/natal/demo` must not render mock report data.
3. Report-page retry must handle `GENERATING` / `PENDING` responses.
4. API client should runtime-validate backend report/generate/section payloads with Zod.
5. `fetchNatalReportSection()` should support demo mode and production demo guard.
6. Preview CTA comment/logic should be accurate.
7. Focused tests should cover retry, demo isolation, Zod validation, and status handling.

Files reviewed:

- `lib/api/natal.ts`
- `app/(grace)/readings/natal/generating/page.tsx`
- `app/(grace)/readings/natal/[id]/page.tsx`
- `app/(grace)/readings/natal/page.tsx`
- `__tests__/api/natal-report.test.ts`

Commit message reports: 20 tests added for Wave 5 fix coverage.

## 2. Verdict

ACCEPTED.

The previously identified Wave 5 blockers are closed by code inspection. The remaining notes are minor and do not block Wave 5 acceptance.

## 3. Blocker closure review

### BLOCKER 1 — Generating-page retry must call `fetchNatalGenerate(true)`

Status: RESOLVED.

The retry handler now does:

```ts
setGenState({ status: "starting" })
const result = await fetchNatalGenerate(true)
```

and handles all backend statuses:

- `READY` → `router.replace(/readings/natal/${reportId})`
- `GENERATING` / `PENDING` → `setGenState({ status: "generating", reportId, attempt: 0 })`
- `FAILED_RETRYABLE` → shows retryable failure
- `FAILED_PERMANENT` → shows permanent failure
- client error → error state

This fixes the previous bug where retry only restarted polling for the old failed report id.

Test coverage reviewed:

- API test verifies `fetchNatalGenerate(true)` sends `{ forceRegenerate: true }`.
- Component-specific click test is not present, but the component code itself now calls the correct function with the correct argument.

Acceptance result: OK.

### BLOCKER 2 — Production `demo` report id must not return mock

Status: RESOLVED.

`fetchNatalReport()` now gates mock report data only by `IS_DEMO_MODE`:

```ts
if (IS_DEMO_MODE) {
  return { ok: true, data: MOCK_NATAL_REPORT_READ }
}
if (reportId === "demo") {
  return { ok: false, error: { type: "not_found", message: "Report not found" } }
}
```

This closes the production direct URL leak for `/readings/natal/demo`.

Test coverage reviewed:

- demo mode returns mock;
- production `fetchNatalReport("demo")` returns `not_found`;
- production real id calls backend.

Acceptance result: OK.

### BLOCKER 3 — Report-page retry must handle `GENERATING` / `PENDING`

Status: RESOLVED.

Report page retry now calls `fetchNatalGenerate(true)` and handles:

- `READY` → fetches full report and renders it;
- `GENERATING` / `PENDING` → transitions to `generating` state;
- `FAILED_RETRYABLE` → retryable failed state;
- `FAILED_PERMANENT` → non-retryable failed state;
- unexpected status → explicit error.

This fixes the previous false generic failure when the backend returned async generation status.

Acceptance result: OK.

## 4. Risk closure review

### RISK 1 — Zod schemas defined but not used

Status: RESOLVED.

The API client now parses successful backend responses with:

```ts
NatalGenerateResponseSchema.parse(raw)
NatalReportReadSchema.parse(raw)
NatalReportSectionReadSchema.parse(raw)
```

Zod failures are surfaced as:

```text
Invalid response format from server
```

Test coverage reviewed:

- valid generate response parses;
- invalid generate response fails;
- valid report response parses;
- invalid report response fails;
- valid section response parses;
- invalid section response fails.

Acceptance result: OK.

### RISK 2 — Section fetch had no demo handling

Status: RESOLVED.

`fetchNatalReportSection()` now:

- in demo mode, finds section in `MOCK_NATAL_REPORT_READ.sections`;
- in production, rejects `reportId === "demo"` as `not_found`;
- otherwise calls backend and Zod-validates the response.

Acceptance result: OK.

### RISK 3 — Preview CTA misleading branch/comment

Status: RESOLVED.

`handleOpenReport()` is simplified to one clear route:

```ts
router.push("/readings/natal/generating")
```

The comment now accurately says the generating page handles both cases: existing READY report or new generation via backend idempotency.

Acceptance result: OK.

### RISK 4 — No focused frontend test evidence

Status: RESOLVED ENOUGH FOR WAVE 5.

A new `__tests__/api/natal-report.test.ts` file was added with focused API-client-level tests for:

- demo isolation;
- section demo handling;
- Zod validation;
- force regeneration request body;
- `GENERATING` / `PENDING` / failed status responses.

This is not full component render coverage, but combined with code inspection it is adequate for this Wave 5 fix gate.

## 5. Non-blocking notes

### NOTE 1 — Component click behavior is still not tested directly

The tests validate API client behavior and the code inspection verifies component handlers. If the frontend grows more stateful, add render-level tests for:

- clicking retry on generating page;
- clicking retry on report page;
- direct `/readings/natal/demo` production route.

Not blocking this acceptance.

### NOTE 2 — `fetchNatalPreview()` still does not Zod-parse preview payload

Wave 5 fixed Zod parsing for full-report generate/report/section payloads. Preview parsing remains typed but not runtime-validated. This was not part of the Wave 5 blocker set, but could be a later consistency improvement.

### NOTE 3 — Demo-mode section fetch ignores report id

In demo mode, `fetchNatalReportSection(reportId, sectionId)` looks up section by `sectionId` only. That is acceptable for one demo report, but if multiple demo reports are introduced later, this should check `reportId` too.

## 6. Acceptance decision

Accepted.

Wave 5 frontend real flow now satisfies the reviewed acceptance points:

- production flow starts real generation;
- retry performs real forced regeneration;
- async generation statuses are handled;
- production demo route no longer leaks mock content;
- full-report API responses are runtime-validated;
- section fetch has demo/prod guards;
- preview CTA logic/comment is accurate.
