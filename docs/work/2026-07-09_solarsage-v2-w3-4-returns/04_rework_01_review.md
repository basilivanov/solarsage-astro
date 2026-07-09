# Architect Review — W3.4 Rework 01

Status: REWORK REQUIRED

Reviewed:

- `f954957 docs(w3.4): finalize rework 01 report with sha b5c8bcd`
- implementation commit: `b5c8bcd W3.4 Rework 01: fix return location, lunar latest, house_system`
- report: `docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md`

## What Improved

- `current_location` now changes return chart houses/ASC/MC.
- Low-latitude relocation resolves return houses as `PLACIDUS`.
- `calculate_houses_cusps` now accepts `house_system`.
- Missing return strength key tests were added.

## Finding 1 — P0: lunar return is still not guaranteed to be the latest crossing

The rework fixed the specific `2026-07-16` regression, but the algorithm still does not enumerate all crossings in the last 30 days. It calls `mooncross_ut()` once from several starts around `target_jd - 28 + offset`, then sorts those first crossings. If the first crossing after the search start is not the latest crossing before target, the latest crossing is skipped.

Current code:

- `apps/solarsage/solarsage/services/returns.py:328`
- `apps/solarsage/solarsage/services/returns.py:332`
- `apps/solarsage/solarsage/services/returns.py:353`

Repro evidence:

```text
target 2026-08-12 12:00 Europe/Moscow
current function return_jd: 2461236.9515122585
independent latest valid return_jd: 2461264.375656118
diff: -27.42414385965094 days
```

So W3.4 still violates the original requirement:

```text
find the most recent UT moment at or before target JD
choose the latest valid crossing, not an arbitrary crossing
```

## Finding 2 — P1: solar return precision is not enforced at the required threshold

The TZ requires longitude residual `<= 0.001°`. Current solar code only attempts refinement when residual is `> 0.01`, and never raises if the final residual remains above `0.001`.

See:

- `apps/solarsage/solarsage/services/returns.py:221`
- `apps/solarsage/solarsage/services/returns.py:227`

Swiss Ephemeris usually returns a precise value, but the code invariant should still enforce the contract.

## Finding 3 — P1: `current_location` request contract is still untyped

The sidecar endpoint still declares:

```python
current_location: dict | None
```

The TZ specified a structured object:

```text
current_location:
  lat: float
  lon: float
  tz: str | null
```

Use a Pydantic model so malformed current-location requests fail at request validation instead of becoming runtime `KeyError`/500 behavior.

## Finding 4 — P1: verification/report is still incomplete

The report lists:

- sidecar targeted;
- API targeted;
- artifact/hashseed in summary.

It does not include the required fresh full sidecar suite, full API suite, hash SHA values, combined W3.4 elapsed time, or exact command results from the full `00_TZ.md` gate.

Do not accept W3.4 until these full gates are present.

## Review Decision

Return for Rework 02. Main fix is not to tune offsets; implement an iterative lunar crossing scan that actually enumerates candidates until the next crossing is after target.
