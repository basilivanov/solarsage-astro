# Review: pre-existing gates fix

Date: 2026-06-11
Status: ACCEPTED AFTER REBASE
Reviewed branch: `fix/pre-existing-gates`
Reviewed commit: `30b51ba83041d44296e610fdf26b53ff39d6d275`
Base observed: `main` at `893b520244acb9f0491df6f30bd24333b706bc4a`
Merge base observed: `c71aa5f9636eabb6e2bce46d018a87807bc02382`
Related TZ: `docs/work/2026-06-11_pre_existing_gates_fix_TZ.md`
Evidence: `docs/work/2026-06-11_pre_existing_gates_fix_evidence.md`

## 1. Scope reviewed

The branch fixes the pre-existing gates that were left outside the accepted natal full report work:

1. `test_solarsage_client ×2` — sidecar schema drift: `latitude` and house cusp key.
2. `test_llm_fallback` — day endpoint fallback test depending on live/unmocked sidecar paths.
3. `test_alembic_roundtrip` — hardcoded `.venv/bin/alembic` and SQLite constraint roundtrip problem.
4. TypeScript errors outside the natal feature gate.

Reviewed files included:

- `apps/api/app/schemas/natal.py`
- `apps/api/tests/test_solarsage_client.py`
- `apps/api/tests/integration/conftest.py`
- `apps/api/tests/test_llm_fallback.py`
- `apps/api/tests/test_alembic_roundtrip.py`
- `apps/api/alembic/versions/0016_add_natal_cache_and_reports.py`
- `components/profile/edit-sheet.tsx`
- `components/today/week-strip.tsx`
- `components/readings/natal/*`
- `lib/reducers/chat-reducer.ts`
- `__tests__/lib/chatReducer.test.ts`
- `docs/work/2026-06-11_pre_existing_gates_fix_evidence.md`

Evidence claims reviewed:

- `npx pnpm typecheck` — passed, 0 compile errors.
- `npx vitest run` — 745 passed, 1 skipped.
- API pytest — 455 passed, 2 skipped.
- sidecar pytest — 20 passed.
- golden Zhanna — 61 passed.

## 2. Verdict

ACCEPTED AFTER REBASE.

The implementation satisfies the technical goal: the listed pre-existing gates are repaired without changing natal full report business behavior. Before merging, rebase/update the branch on current `origin/main`, because the branch was observed as `ahead 1 / behind 1` relative to `main`.

Required before merge:

```bash
git fetch origin
git checkout fix/pre-existing-gates
git rebase origin/main
# rerun at least the touched gates or full checks
```

If rebase is clean and checks remain green, merge is approved.

## 3. Work package review

### A — `test_solarsage_client`

Status: ACCEPTED.

`SolarSagePlanetPosition` and `SolarSageTransitPlanet` now include:

```python
latitude: float | None = None
```

`SolarSageHouseCusp` now maps the sidecar key `cusp` into the internal field `longitude`:

```python
longitude: float = Field(..., alias="cusp")
```

This preserves the internal service expectation that house objects expose `.longitude`, while accepting the real sidecar payload that uses `cusp`.

`test_solarsage_client.py` now validates natal responses with `latitude`, house `cusp`, and non-empty validation behavior.

Acceptance result: OK.

### B — `test_llm_fallback`

Status: ACCEPTED WITH NOTE.

The integration fixture now patches the SolarSage client factory across the relevant namespaces:

- `app.clients.solarsage_client.get_solarsage_client`
- `app.services.natal_context_service.get_solarsage_client`
- `app.services.today_service.get_solarsage_client`
- `app.services.horary_service.get_solarsage_client`

The fallback test also directly patches natal/today sidecar factories and provides deterministic natal/transit payloads with `sign`, `cusp`, and `latitude` fields. This makes the LLM fallback test hermetic and prevents accidental live sidecar dependency.

Acceptance result: OK.

Note: `test_day_endpoint_returns_llm_data_when_available` remains skipped with reason `Cache collision with parallel xdist — passes standalone, skip in CI`. This is acceptable for this gates-fix branch because it is documented and unrelated to the original failing fallback gate. It should still be tracked as a separate cleanup item if the suite is expected to have zero non-known skips.

### C — `test_alembic_roundtrip`

Status: ACCEPTED.

The test no longer depends on `.venv/bin/alembic`; it now invokes Alembic portably via:

```python
[sys.executable, "-m", "alembic", *args]
```

Migration `0016` now wraps `today_payloads_cache` constraint changes in `op.batch_alter_table(...)`, which is the correct SQLite-compatible pattern for the roundtrip test.

Acceptance result: OK.

### D — TypeScript errors outside natal

Status: ACCEPTED.

The fixes are localized and mostly type-directed:

- `components/profile/edit-sheet.tsx`: `CityEditor` now stores `City | null` and formats on save.
- `components/today/week-strip.tsx`: async day statuses are loaded through `useEffect` + state instead of treating a Promise as a sync value.
- `components/readings/natal/*`: type imports now point to `@/lib/contracts/natal`; callback params are explicitly typed where needed.
- `__tests__/lib/chatReducer.test.ts`: tests now match the current `ChatEvent` state machine instead of obsolete thread/action contracts.
- smaller test/type fixes were applied to Telegram/auth/storage/horary/component tests.

A small amount of `as any` appears in tests where the test intentionally constructs invalid payloads or mutates `NODE_ENV`. This is acceptable and not production-code type erosion.

Acceptance result: OK.

## 4. Evidence review

`docs/work/2026-06-11_pre_existing_gates_fix_evidence.md` contains:

- initial failure list;
- applied fixes per work package;
- changed files;
- exact verification commands;
- final pass counts.

Acceptance result: OK.

## 5. Merge notes

### Required before merge

The branch was observed as `ahead 1 / behind 1` relative to `main`. Rebase on `origin/main` before merging:

```bash
git fetch origin
git checkout fix/pre-existing-gates
git rebase origin/main
```

Then rerun at least:

```bash
npx pnpm typecheck
npx vitest run
cd apps/api && .venv/bin/pytest
```

### Non-blocking notes

1. `pnpm-lock.yaml` changed. This is not automatically wrong, but reviewer/merger should confirm it came from package-manager normalization or a real dependency update. No functional blocker if checks stay green.
2. `test_day_endpoint_returns_llm_data_when_available` is skipped. The skip is documented, but if the project target is zero unexplained skips, create a follow-up for cache isolation under xdist.
3. The evidence says branch is based on `c71aa5f`; current `main` has advanced to `893b520`. Rebase resolves this bookkeeping mismatch.

## 6. Final decision

Accepted after rebase.

The implementation closes the requested pre-existing gates:

- sidecar schema drift fixed;
- fallback test hermetic;
- Alembic roundtrip portable and SQLite-compatible;
- TypeScript typecheck clean;
- evidence included.

No natal full report business regression was identified in the reviewed diff.
