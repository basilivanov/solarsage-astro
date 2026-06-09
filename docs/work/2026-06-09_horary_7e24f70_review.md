# Review: W-HORARY-UX-GENERATION-REPAIR

Date: 2026-06-09
Reviewed commit: 7e24f70c6cc616baf859a91818fbda121ead4250
Base commit: 2584c46c1251ca3dcbae4654bcc8e5b3025bed51
Verdict: REJECTED

## Scope reviewed

Changed files in commit:

- app/(grace)/readings/horary/[id]/page.tsx
- apps/api/alembic/versions/0014_add_horary_failure_fields.py
- apps/api/app/api/day.py
- apps/api/app/api/horary.py
- apps/api/app/api/profile.py
- apps/api/app/db/models.py
- apps/api/app/schemas/horary.py
- apps/api/app/schemas/profile.py
- apps/api/app/services/horary_service.py
- apps/api/app/services/llm_service.py
- apps/api/app/services/today_service.py
- components/app-shell.tsx
- components/profile-reset.tsx
- components/readings/horary/horary-form.tsx
- components/readings/horary/horary-processing-card.tsx
- components/readings/horary/horary-question-card.tsx
- components/readings/horary/horary-screen.tsx
- hooks/use-onboarded.ts
- lib/api/horary.ts
- packages/contracts/_generated.ts

## Positive findings

1. Inline processing UX was added.
   - New `HoraryProcessingCard` has orbit animation, steps, progress bar, and long-running copy.
   - Main history screen now inserts the returned question into local `questions` immediately after `createHoraryQuestion`.
   - History cards now have clearer processing/answered/failed visual states.

2. Detail page now polls processing questions.
   - It no longer loads a processing question once and then waits forever without refresh.
   - It has a long-running fallback with link back to history.

3. Backend stores failure metadata.
   - Migration 0014 adds `failure_stage`, `failure_code`, `failure_message`, `public_error_code`, `public_error_message`.
   - Generator writes stage/code/message on profile/sidecar/engine/LLM failures.

4. LLM answer quality gate was strengthened.
   - Minimum block count is enforced.
   - Lead/confidence/timing/advice text length is enforced.
   - Required block types are enforced.
   - Thin answers now fail generation instead of being saved as successful.

These are directionally correct and match the UX/failure-handling packet.

## Blockers

### B1 — API client now hides server errors as empty data / not found

Status: BLOCKER

`lib/api/horary.ts` now returns `[]` for any non-OK response from `listHoraryQuestions`, and `null` for any non-OK response from `getHoraryQuestion`.

This means a backend outage, auth problem, 500, bad gateway, or contract error can look to the user like:

- there is no question history;
- a specific question does not exist;
- detail page shows “Вопрос не найден”.

This violates `docs/FAILURE_HANDLING_CANON.md`: we must not replace failures with plausible successful empty states.

Required fix:

- `listHoraryQuestions` should return `[]` only for a deliberately supported empty 200 response, not for non-OK HTTP.
- On non-OK, throw a typed/user-safe error.
- `getHoraryQuestion` should return `null` only for 404.
- For 401/403/500/network/contract errors, throw typed errors and render an honest load error.

### B2 — out-of-scope day calculation now falls back to `birthday_location` as birth coordinates

Status: BLOCKER

This commit changed onboarding/day readiness and Today calculation to treat `birthday_lat/birthday_lon` as a fallback for missing `birth_lat/birth_lon`.

That is unsafe because `birthday_location` is not necessarily the birth place; it is a separate profile location concept. Using it for natal calculation can build the user’s natal/day chart with the wrong coordinates instead of blocking incomplete birth data.

Affected logic:

- `apps/api/app/api/day.py` now passes onboarding readiness if either birth coords or birthday coords exist.
- `apps/api/app/services/today_service.py` now passes `profile.birth_lat or profile.birthday_lat or 0` and same for longitude into the natal calculation.

Required fix:

- Remove `birthday_lat/birthday_lon` fallback from natal/day calculation.
- Day readiness must require real birth coordinates for natal chart.
- If old production profiles are missing birth coordinates, fix migration/profile data flow explicitly instead of silently substituting birthday/current coordinates.
- Add regression test: missing birth coords + present birthday coords must remain NOT_ONBOARDED / profile incomplete for natal/day calculation.

### B3 — schema strictness was weakened for required horary blocks

Status: MAJOR RISK / likely blocker for contract safety

`VerdictCardBlock.confidence_label`, `VerdictCardBlock.confidence_explanation`, and `TimingBlock.status` became optional in `apps/api/app/schemas/horary.py`.

The LLM quality validator still requires these fields, so the service path is strict. But the public response schema now allows malformed stored/manual data that the UI is not really designed for.

Risk:

- malformed blocks can pass Pydantic response validation;
- UI renders fallback-ish labels or missing intro text;
- tests may miss contract regressions because the schema no longer fails them.

Required fix:

- Keep these fields required in the response schema.
- If backward compatibility is needed for old stored rows, repair/migrate old rows or normalize before response, do not weaken the contract.

### B4 — no changed tests in a test-heavy feature

Status: BLOCKER for acceptance evidence

The commit changes async polling, UI states, backend failure persistence, LLM quality validation, schema contracts, generated contracts, and a migration, but the changed-file list contains no backend or frontend tests.

The requested packet required tests for:

- inline processing card insertion;
- processing-to-answered transition;
- processing-to-failed transition;
- detail page polling;
- failure metadata persistence;
- short/thin LLM answer rejection and retry/fail/refund;
- user-safe error mapping.

Required fix:

- Add backend tests for failure metadata and quality gate.
- Add frontend tests for the new processing card and polling states.
- Add regression tests for the API client not hiding non-OK responses as empty/not-found states.
- Add regression test for no `birthday_location` fallback into natal/day calculation.

## Non-blocking notes

1. `HoraryScreen` still stops main-list polling after 60 seconds and only resumes on reload/revisit or state changes. This may be acceptable for MVP, but product copy says the user can close and answer will appear later. Consider periodic refresh or a stable “long-running saved” card that can re-poll on visibility/focus.
2. `getHoraryQuestion` returning `null` for 404 can be fine, but only 404 should map to null.
3. Failure metadata currently exposes only generic public code/message. This is good for user safety, but internal logs/admin tooling should include enough detail for diagnosis.

## Verification evidence

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `7e24f70c6cc616baf859a91818fbda121ead4250`.
- No combined GitHub status checks were visible for the commit.

Local/coder evidence was not provided in the user message.

## Final decision

REJECTED.

The UX direction is correct, and the main requested pieces are partially implemented. But the commit currently hides API failures as empty/not-found states, introduces an unsafe birthday-location fallback into natal/day calculation, weakens strict horary response schemas, and lacks test changes for a complex async/failure-handling feature.

After fixing B1–B4, this should be re-reviewed.
