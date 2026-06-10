# Acceptance Review: 0609502 — Wave 5 Non-blocking Follow-ups

Date: 2026-06-11
Status: ACCEPTED
Reviewed commit: `060950232b42fe457132f51def6c73e682cbb778`
Branch: `feat/natal-full-report`
Previous Wave 5 acceptance review: `docs/work/2026-06-11_9ccad9d_wave_5_frontend_real_flow_acceptance_review.md`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Scope reviewed

This follow-up closes the three non-blocking notes from the Wave 5 acceptance review:

1. Add component render tests for retry/demo/generation states.
2. Add runtime Zod parsing for preview payloads.
3. Tighten demo-mode section fetch so mock sections are served only for `reportId === "demo"`.

Files reviewed:

- `__tests__/natal/natal-component-states.test.tsx`
- `__tests__/api/natal-report.test.ts`
- `lib/api/natal.ts`
- `lib/contracts/natal.ts`

Commit message reports: `51 natal tests passing (24 API + 22 contract + 5 component)`.

## 2. Verdict

ACCEPTED.

All three prior non-blocking notes are closed. This does not change the prior Wave 5 acceptance status; it strengthens it with render-level tests and preview-contract validation.

## 3. Follow-up closure review

### NOTE 1 — Component render tests

Status: RESOLVED.

New component tests in `__tests__/natal/natal-component-states.test.tsx` cover:

- generating page retry after `FAILED_RETRYABLE`;
- retry calls `fetchNatalGenerate(true)`;
- retry redirects to the new READY report;
- report page `/demo` in production shows `Отчёт не найден`;
- report page retry with `GENERATING` transitions to `Отчёт ещё генерируется`;
- report page retry with `FAILED_PERMANENT` removes the retry button;
- initial report load with `GENERATING` shows generating state.

Acceptance result: OK.

### NOTE 2 — Preview Zod parsing

Status: RESOLVED.

`lib/contracts/natal.ts` now defines preview schemas:

- `NatalPreviewMetaSchema`
- `NatalPreviewHighlightSchema`
- `NatalPreviewSphereSchema`
- `NatalPreviewPlanetSchema`
- `NatalPreviewChapterSchema`
- `NatalCalculationStatsSchema`
- `NatalPreviewReadSchema`

`fetchNatalPreview()` now does:

```ts
const raw = await res.json()
const data = NatalPreviewReadSchema.parse(raw)
```

and maps Zod failures to:

```text
Invalid response format from server
```

API tests cover:

- valid preview response parses;
- invalid preview response fails;
- missing required `meta.birthDate` fails.

Acceptance result: OK.

### NOTE 3 — Demo section reportId guard

Status: RESOLVED.

`fetchNatalReportSection()` now returns mock section only when:

```ts
IS_DEMO_MODE && reportId === "demo"
```

For demo mode with non-demo report id, it falls through to backend. In production, `reportId === "demo"` still returns `not_found`.

Tests cover:

- demo mode + `demo` report id returns mock/not_found section result;
- demo mode + non-demo report id calls backend;
- production + `demo` report id returns `not_found`.

Acceptance result: OK.

## 4. Remaining notes

### NOTE 1 — CI status not independently fetched

Commit message reports 51 natal tests passing. I reviewed the relevant code and tests, but did not independently fetch CI logs.

### NOTE 2 — Demo preview path still bypasses Zod intentionally

`fetchNatalPreview()` still returns `DEMO_NATAL_PREVIEW as unknown as NatalPreviewRead` in demo mode. This is acceptable because the follow-up was about backend preview payload validation. If demo fixtures should be contract-checked too, add a fixture validation test.

## 5. Acceptance decision

Accepted.

Wave 5 is now accepted with the three previous non-blocking follow-ups closed:

- component render state coverage exists;
- preview API payload is runtime-validated;
- section demo mock path is correctly scoped by `reportId === "demo"`.
