# Review: 57c5056 — Wave 5 Frontend Real Flow

Date: 2026-06-11
Status: CHANGES REQUESTED
Reviewed commit: `57c505630224773c9c564244f611117c484df27d`
Branch: `feat/natal-full-report`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`
Previous accepted Wave 4 review: `docs/work/2026-06-11_0a93abe_wave_4_full_report_backend_acceptance_review.md`

## 1. Scope reviewed

Wave 5 target:

- frontend uses real natal full-report API client;
- preview CTA enters real generation flow;
- generating page calls `POST /api/natal/generate`;
- report page fetches real report by id;
- demo/mock path is isolated to demo mode;
- frontend contracts match backend `NatalReportRead` / `NatalGenerateResponse`;
- report renderer supports backend block types.

Changed files reviewed:

- `lib/api/natal.ts`
- `lib/contracts/natal.ts`
- `lib/mocks/natal.ts`
- `packages/contracts/index.ts`
- `app/(grace)/readings/natal/page.tsx`
- `app/(grace)/readings/natal/generating/page.tsx`
- `app/(grace)/readings/natal/[id]/page.tsx`

Commit message says TypeScript changed files compile cleanly with 0 new errors.

## 2. Verdict

CHANGES REQUESTED.

The direction is correct: the production report page no longer blindly renders `MOCK_NATAL_REPORT`, the generating page calls the backend, and the frontend now has backend-aligned report types.

But there are production-flow blockers around retry behavior and demo isolation.

## 3. What is good

### GOOD 1 — API client now has real full-report methods

`lib/api/natal.ts` adds:

- `fetchNatalGenerate(forceRegenerate?)`
- `fetchNatalReport(reportId?)`
- `fetchNatalReportSection(reportId, sectionId)`

All use credentials and backend routes aligned with `apps/api/app/api/natal.py`.

### GOOD 2 — Generating page starts backend generation

`/readings/natal/generating` now calls:

```ts
fetchNatalGenerate(false)
```

on mount in production mode. It redirects to `/readings/natal/{reportId}` when generation returns `READY`.

### GOOD 3 — Report page fetches backend report by id

`/readings/natal/[id]` now calls:

```ts
fetchNatalReport(id)
```

and handles `READY`, `GENERATING`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`, `not_found`, and generic error states.

### GOOD 4 — BackendBlockRenderer covers backend block types

The renderer handles:

- `lead`
- `paragraph`
- `heading`
- `list`
- `callout`
- `pros_cons`
- `quote`
- `divider`
- `highlights`
- `bullets`

It also correctly expects `pros_cons.pros/cons` as `{ title, text }[]`, not old string arrays.

### GOOD 5 — Preview CTA no longer directly routes to mock report

The preview CTA now routes to `/readings/natal/generating` in all cases, letting the generating page decide whether an existing READY report can be reused.

## 4. Blockers

### BLOCKER 1 — Retry on generating page does not start a new generation

When the generating page reaches `failed_retryable`, the retry button calls:

```ts
const handleRetry = useCallback(async () => {
  if (genState.status !== "failed_retryable") return
  const { reportId } = genState

  setGenState({ status: "generating", reportId, attempt: 0 })
}, [genState])
```

This only starts polling the same failed report id again. It does **not** call:

```ts
fetchNatalGenerate(true)
```

Impact:

- Backend has already persisted that report as `FAILED_RETRYABLE`.
- Polling `GET /api/natal/report/{oldFailedId}` will keep returning `FAILED_RETRYABLE`.
- The retry button appears functional but cannot actually trigger regeneration.

Required fix:

Change retry to call generation with force regeneration:

```ts
const handleRetry = useCallback(async () => {
  setGenState({ status: "starting" })
  const result = await fetchNatalGenerate(true)
  if (!result.ok) {
    setGenState({ status: "error", message: result.error.message })
    return
  }
  const { reportId, status } = result.data
  if (status === "READY") {
    router.replace(`/readings/natal/${reportId}`)
    return
  }
  if (status === "GENERATING" || status === "PENDING") {
    setGenState({ status: "generating", reportId, attempt: 0 })
    return
  }
  if (status === "FAILED_RETRYABLE") {
    setGenState({ status: "failed_retryable", reportId, message: result.data.errorMessage || "Generation failed" })
    return
  }
  if (status === "FAILED_PERMANENT") {
    setGenState({ status: "failed_permanent", message: result.data.errorMessage || "Generation failed permanently" })
  }
}, [router])
```

Acceptance test required:

- In `failed_retryable` state, clicking retry calls `fetchNatalGenerate(true)` and then routes/polls the new report id.

### BLOCKER 2 — Production direct `/readings/natal/demo` still returns mock report

`fetchNatalReport()` currently returns mock data when:

```ts
if (IS_DEMO_MODE || reportId === "demo") {
  return { ok: true, data: MOCK_NATAL_REPORT_READ }
}
```

Impact:

- Even when `IS_DEMO_MODE=false`, a direct URL `/readings/natal/demo` renders the demo report.
- This violates the production mock isolation rule from earlier waves: production must not serve mock full reports outside demo mode.
- The generating page may not route to `/demo` in production, but the report route itself still permits it.

Required fix:

Only allow `demo` id inside demo mode:

```ts
if (IS_DEMO_MODE) {
  return { ok: true, data: MOCK_NATAL_REPORT_READ }
}
if (reportId === "demo") {
  return { ok: false, error: { type: "not_found", message: "Report not found" } }
}
```

or let it call backend and receive a real 404.

Acceptance test required:

- With `IS_DEMO_MODE=false`, `fetchNatalReport("demo")` does not return `MOCK_NATAL_REPORT_READ`.
- `/readings/natal/demo` in production shows not-found/error, not mock content.

### BLOCKER 3 — Report page retry handles only immediate READY and treats async generation as failure

Report page retry does call:

```ts
fetchNatalGenerate(true)
```

But after that it immediately calls:

```ts
fetchNatalReport(result.data.reportId)
```

and only handles `READY`. If the backend returns `GENERATING` or `PENDING`, the page falls through to:

```ts
setState({ status: "error", message: "Retry failed. Please try again." })
```

Impact:

- If the backend becomes asynchronous, or if `generate` returns `GENERATING`, report-page retry falsely reports failure.
- This conflicts with the frontend state model which otherwise supports `GENERATING`.

Required fix:

After `fetchNatalGenerate(true)`, handle statuses the same way as the generating page:

- `READY` → fetch/render or route to report;
- `GENERATING`/`PENDING` → route to `/readings/natal/generating` or set generating state;
- `FAILED_RETRYABLE` → failed retryable;
- `FAILED_PERMANENT` → permanent failure.

Acceptance test required:

- `fetchNatalGenerate(true)` returning `GENERATING` does not show generic retry failed; it transitions to generating/polling flow.

## 5. Major risks

### RISK 1 — Backend-aligned Zod schemas are defined but not used in the API client

`lib/contracts/natal.ts` defines `NatalReportReadSchema` and `NatalGenerateResponseSchema`, but `lib/api/natal.ts` does:

```ts
const data: NatalReportRead = await res.json()
return { ok: true, data }
```

and similarly for generate response.

Impact:

- Runtime backend/frontend contract drift will not be caught at the API boundary.
- The renderer may receive malformed data and fail later in a UI component.
- The commit claims backend-aligned contracts, but they are mostly compile-time annotations unless parsed.

Recommended fix:

Use the validators at the API boundary:

```ts
const raw = await res.json()
const data = NatalReportReadSchema.parse(raw)
```

or import `validateNatalReportRead(raw)`.

Add graceful error mapping if validation fails.

### RISK 2 — `fetchNatalReportSection()` has no demo-mode handling

The section fetch method calls backend even in demo mode. It may be unused today because the report page loads full mock report, but if section-level lazy loading is introduced, demo mode will break.

Not a blocker for this Wave 5 flow, but should be consistent.

### RISK 3 — Preview CTA comment says “fetch directly”, but implementation always routes to generating

`handleOpenReport()` has a branch for `fullReportAvailable`, but both branches currently do:

```ts
router.push("/readings/natal/generating")
```

This is not functionally wrong because generating page calls `POST /generate`, and backend idempotency can return existing READY report. But the comment is misleading.

Either simplify:

```ts
router.push("/readings/natal/generating")
```

or actually fetch existing report directly if that is desired.

### RISK 4 — No frontend test evidence found in the commit

Commit message reports TypeScript compile status, but I did not see tests for:

- retry button behavior;
- production `demo` route isolation;
- backend report block rendering for all block types;
- error states for failed/permanent/generating.

This is not automatically a blocker if the project accepts manual evidence, but Wave 5 is UI state-heavy and should have at least focused tests for retry/demo gating.

## 6. Acceptance decision

Do not accept Wave 5 yet.

Accept after:

- generating-page retry calls `POST /api/natal/generate` with `forceRegenerate=true`;
- production direct `/readings/natal/demo` no longer renders mock report;
- report-page retry handles `GENERATING/PENDING` instead of generic failure;
- ideally API client validates backend responses with the new Zod schemas, or the claim is reduced to “types only”.
