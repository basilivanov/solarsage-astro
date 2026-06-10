# Review blocked: R3.2 logging cleanup / guardrails not visible on main

Date: 2026-06-11
Requested scope: R3.2 logging cleanup review
Repository: `basilivanov/solarsage-astro`

## Verdict

**BLOCKED — R3.2 changes are not visible to reviewer on GitHub `main`.**

I cannot honestly review the claimed R3.2 implementation yet because the GitHub connector currently resolves `main` / `HEAD` to:

`8a933cf73d2496cbbd229a11725b07d567f7ee9d` — `docs: add structured logging fix review for e46e129`

That commit is only the previous review document, not the claimed R3.2 code cleanup / guardrails implementation.

## What I tried to verify

Expected R3.2 artifacts from the handoff:

- backend legacy cleanup in:
  - `apps/api/app/services/llm_service.py`
  - `apps/api/app/services/today_service.py`
  - `apps/api/app/services/natal_context_service.py`
  - `apps/api/app/services/horary_service.py`
  - `apps/api/app/services/natal_service.py`
- frontend console migration in:
  - `lib/api/cities.ts`
  - `components/onboarding/city-picker.tsx`
  - `components/today/week-strip.tsx`
  - `components/readings/horary/horary-screen.tsx`
  - `app/(grace)/readings/horary/[id]/page.tsx`
  - `components/onboarding/onboarding-flow.tsx`
  - `lib/grace/hooks/useDay.ts`
  - `components/correlation-init.tsx`
  - `lib/reducers/onboarding-reducer.ts`
- guardrail changes:
  - `scripts/check_logging_guardrails.py`
  - `scripts/guardrails.sh` strict-mode wiring

## Current evidence

- `main` / `HEAD` still points to the previous docs-only review commit `8a933cf73d2496cbbd229a11725b07d567f7ee9d`.
- Searching for `check_logging_guardrails.py` in the repository returned no result through the connector.
- Fetching commit/ref `R3.2` failed because there is no such commit/ref visible through the connector.
- No workflow runs are visible for the previously reviewed commits through the connector, so the stated `1333 tests pass` cannot be independently verified here.

## Review status

No code-level acceptance/rejection is issued for R3.2 yet.

The safe status is:

**WAITING FOR VISIBLE COMMIT / REF.**

## Next required input

Provide one of:

1. the actual R3.2 commit SHA;
2. the branch name containing R3.2;
3. or push/fast-forward `main` so `HEAD` includes the R3.2 files.

After that, review should check:

- no production `console.*` remains outside allowlisted debug/e2e files;
- no backend `logging.getLogger(__name__)` or `from app.core.logging import logger` remains in production feature code;
- `scripts/check_logging_guardrails.py` is wired into `scripts/guardrails.sh strict`;
- remaining R1/R2 items from the previous review are either closed or explicitly deferred;
- stated test counts are backed by CI logs, local evidence file, or committed verifier output.
