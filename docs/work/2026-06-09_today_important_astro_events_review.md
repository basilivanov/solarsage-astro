# Review: W-TODAY-IMPORTANT-ASTRO-EVENTS

Date: 2026-06-09
Reviewed commit: `5ab56117d07a206b94e1f49e1fa13b0a7c4ddc2f`
Source TZ: `docs/work/2026-06-09_today_important_astro_events_TZ.md`
Scope: Today Important deterministic astro events, backend contract, frontend rendering, tests.

## Verdict

Status: **ACCEPTED WITH NOTES**

No blocker found in the reviewed diff.

The implementation matches the main product direction for the Today Important block: deterministic important events, no LLM narration for the block, typed backend/frontend contract, flat frontend event cards, and hide-when-empty behavior.

## Reviewed evidence

Changed files between previous main baseline `2ca3328ab89af3fffc3f13d78a9039273eaed432` and reviewed commit `5ab56117d07a206b94e1f49e1fa13b0a7c4ddc2f`:

- `apps/api/app/services/today_important_service.py`
- `apps/api/app/services/today_service.py`
- `apps/api/app/schemas/today.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/tests/test_today_important.py`
- `apps/api/tests/test_llm_context_accuracy.py`
- `apps/api/tests/test_pipeline_invariants.py`
- `components/today-important-accordion.tsx`
- `components/today/today-screen.tsx`
- `__tests__/components/TodayImportantAccordion.test.tsx`
- `__tests__/contracts/today.test.ts`
- `__tests__/hooks/useDay.test.ts`
- `lib/contracts/today.ts`
- `lib/today.ts`
- `lib/mocks/today.ts`
- `packages/contracts/_generated.ts`
- `packages/contracts/index.ts`
- `packages/contracts/openapi.json`
- minor unrelated prod-guard env files touched: `lib/env/production-guard.mjs`, `lib/env/production-guard.ts`

## What is accepted

### A1. Backend service moved to deterministic event calculation

`TodayImportantService` was rewritten and is now the owner of deterministic event selection for the Today Important block.

Accepted event families from this packet:

- Moon void of course;
- New Moon / Full Moon window;
- Solar / Lunar eclipse window;
- Mercury retrograde / Mercury station;
- Moon quarter window;
- Sun ingress;
- fast-planet aspects by whitelist.

This is acceptable for this TZ version.

### A2. LLM enrichment removed from Today Important runtime path

The previous risk was that important events could be selected or expanded through LLM narration. That would make the block slower, more expensive, and less deterministic.

The reviewed commit removes the Today Important LLM enrichment call from the Today service path. Search for `generate_important_today_details` only finds the LLM service definition/tests, not the Today runtime service.

### A3. Timezone behavior is implemented in Today service integration

The implementation now resolves user-local timezone for Today Important output from profile timezone data, with fallback behavior. This is the right place to do it because Today service already has the profile and constructs the final Today payload.

Accepted expectation:

- current/profile timezone first when available;
- birth timezone fallback;
- stable final fallback.

### A4. Contract migration is consistent

The backend schema and generated TS contract were updated to the new event shape.

Expected event shape is now flat and UI-friendly:

- `id`
- `kind`
- `tone`
- `title`
- `summary`
- `startsAt`
- `endsAt`
- `exactAt`
- `localTimeLabel`
- `timezone`
- `priority`

This is cleaner than the previous nested `ImportantTodayItem/details` model and better for the MVP UI.

### A5. Frontend rendering is MVP-suitable

`TodayImportantAccordion` was simplified from expandable detailed narration into a flat list of event cards.

Accepted behavior:

- event title is visible immediately;
- short summary is visible immediately;
- tone is visually represented;
- local time label is rendered when present;
- block hides when there are no important events.

This matches the product rule: the block should only appear when there is something genuinely important today.

### A6. Tests were updated

The commit updates backend tests, contract tests, component tests, hooks tests, and generated contracts.

Coder-reported evidence:

- backend tests: `237/237` green;
- frontend tests: `477/477` green;
- Next.js build passes.

I could not independently verify CI through GitHub status API because no workflow/status records were visible for the commit through the connector. This is a note, not a blocker, because the repository diff and test changes are consistent and the coder provided runner evidence.

## Notes / risks

### N1. CI status not visible through GitHub connector

GitHub workflow/status data was not available for reviewed commit `5ab56117d07a206b94e1f49e1fa13b0a7c4ddc2f` through the connector.

Keep the coder's local evidence in the task log:

- backend test output;
- frontend test output;
- Next.js build output.

### N2. Component test coverage became thinner

The frontend component tests were simplified together with the UI rewrite. This is acceptable for the new flat-card component, but follow-up hardening can add explicit tests for:

- hide-when-empty;
- tone label/class for caution/supportive;
- all supported `kind` values render without crashing;
- `localTimeLabel` absent does not leave dangling punctuation.

Not a blocker for acceptance.

### N3. Minor unrelated prod-guard files appear in the diff

The compare includes small changes to `lib/env/production-guard.mjs` and `lib/env/production-guard.ts`.

This is outside the Today Important scope. It looks minor, but should not be used to expand this packet. If more prod-guard work is needed, it should stay in the separate prod-guard task stream.

## Acceptance checklist

```text
[x] Backend deterministic Today Important service implemented.
[x] Important event selection is not LLM-driven.
[x] New event contract is reflected in Python schema.
[x] New event contract is reflected in generated TypeScript contracts.
[x] Frontend renders flat event cards.
[x] Frontend hides the block when there are no events.
[x] Local time label support exists in the contract/UI.
[x] Backend tests updated.
[x] Frontend tests updated.
[x] Build reported green by coder.
[!] CI/status not independently visible through connector.
```

## Final conclusion

`W-TODAY-IMPORTANT-ASTRO-EVENTS` can be accepted.

No rework is required before moving on.

Recommended next work after this:

1. `W-PROD-DEMO-GUARD` if not already merged/accepted in the current branch history.
2. `W-NATAL-FRONTEND-MVP`, because natal calculation exists but the frontend presentation is still missing.
