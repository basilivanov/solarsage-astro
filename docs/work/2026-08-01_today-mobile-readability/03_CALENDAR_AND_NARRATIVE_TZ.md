# Packet 03 — calendar tone and narrative reliability

## Packet title

Calendar readable day signals and Today narrative degraded mode

## Phase / Wave

W-TODAY-MOBILE-READABILITY / 03

## Modules

- M-CALENDAR-SERVICE
- M-CALENDAR-API
- M-API-DAY
- M-TODAY-CONVERGENCE-PROJECTION
- M-TODAY-NARRATIVE

## Goal

Expose the deterministic day tone needed for a compact, accessible calendar icon and make the narrative failure path preserve useful event facts. Investigate and correct the current repeated `schema_invalid` path without weakening claim validation.

## Exact write scope

- `apps/api/app/schemas/calendar.py`
- `apps/api/app/services/calendar_service.py`
- `apps/api/app/api/calendar.py` only if required by schema wiring
- `apps/api/app/services/today_convergence_projection.py`
- `apps/api/app/services/today_narrative_service.py` only if the root validation defect is local and proven
- matching generated contracts via the repository generation command
- focused backend/frontend tests for these contracts

## Frozen / out of scope

- No weakening of narrative source-event binding or sanitizer rules.
- No deletion of unavailable/pending states.
- No changes to calculation, ephemeris, or sphere technique semantics.
- No baseline PNG changes.

## Must preserve

- `dayState` remains `hero|ordinary|not-computed`.
- Today wire validation remains fail-closed for malformed LLM claims.
- Deterministic snapshot payload and event ledger remain immutable.
- Generated contracts are regenerated, never hand-edited.

## Verification

`cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_convergence_api.py tests/test_today_convergence_projection.py tests/test_calendar_service.py -q`

Plus `pnpm contracts:check`, `python3 scripts/grace_lint.py apps/api/app`, and the focused calendar Vitest file.

## Expected evidence

Root cause and redacted test fixture for `schema_invalid`, deterministic facts preserved for unavailable narrative, generated contract diff, and focused tests green.

## Escalation

If the provider contract cannot be corrected safely from repository evidence, stop with the exact failing shape and implement only the deterministic degraded UI path.

## No-commit rule

Do not commit or push. The reviewer will integrate and commit.
