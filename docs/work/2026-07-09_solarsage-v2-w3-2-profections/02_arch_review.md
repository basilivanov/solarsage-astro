# Architect Review: Wave W3.2 Profection Activations

Status: REWORK REQUIRED

Reviewed commits:

- `1b7674a` — W3.2 implementation
- `fb87f22` — W3.2 report traceability fix

## Summary

The implementation is a solid first pass:

- `annual_profection` and `monthly_profection` are emitted by sidecar;
- Basil golden values for `2026-07-08` match the TZ:
  - age `45`;
  - annual house `10`;
  - lord of year `MARS`;
  - completed month steps `8`;
  - monthly house `6`;
  - lord of month `JUPITER`;
- W3.2 artifact has 115 activations: 111 W3.1 transit + 4 profection;
- sidecar full and API full passed in the agent run;
- TodayService remains unwired to sidecar activation layer.

W3.2 cannot be accepted yet because monthly profection boundary logic drifts after a clamped month, and several explicit audit/debug requirements are incomplete.

## Blocking Findings

### P0. Monthly profection month-step calculation drifts after February clamp

TZ required monthly anniversaries from the annual year start:

```text
Count completed monthly anniversaries from that annual year start to target_local_date.
Use calendar-month addition with day clamp for months that do not have the birth day.
```

Current implementation chains the clamped date:

```python
probe = annual_year_start
while True:
    next_probe = _add_months_with_clamp(probe, 1)
    ...
    probe = next_probe
```

For annual year start `2025-10-30`, this produces:

```text
1 2025-11-30
2 2025-12-30
3 2026-01-30
4 2026-02-28
5 2026-03-28
6 2026-04-28
7 2026-05-28
8 2026-06-28
9 2026-07-28
```

Correct non-drifting anniversaries are based on the original annual start:

```text
1 2025-11-30
2 2025-12-30
3 2026-01-30
4 2026-02-28
5 2026-03-30
6 2026-04-30
7 2026-05-30
8 2026-06-30
9 2026-07-30
```

Impact:

- `2026-07-08` still happens to return `8`, so the Basil golden case passes.
- Boundary dates after February are wrong. Example: `2026-07-29` should still be step `8`, not step `9`.

Required fix:

- Count month anniversaries as `_add_months_with_clamp(annual_year_start, n)`, not by repeatedly adding one month to the prior clamped date.
- Add tests proving:
  - `2026-03-29` => completed steps `4`;
  - `2026-03-30` => completed steps `5`;
  - `2026-07-29` => completed steps `8`;
  - `2026-07-30` => completed steps `9`.

### P1. Debug payload is missing required `house_cusp_longitude`

W3.2 TZ required each profection activation debug to include:

```json
"house_cusp_longitude": 0.0
```

Current W3.2 artifact debug includes `house_cusp_sign`, but not `house_cusp_longitude`:

```json
{
  "house": 10,
  "house_cusp_sign": "Aries",
  "ruler": "MARS"
}
```

Required fix:

- Add `house_cusp_longitude` to annual house, annual lord, monthly house, and monthly lord activation debug.
- Add tests for the Basil golden fixture:
  - annual house cusp longitude `0.0`;
  - monthly house cusp longitude `240.0`;
  - signs remain `Aries` and `Sagittarius`.

### P1. W3.2 audit artifact metadata still says `wave: W3.1`

Current artifact:

```json
"_audit_meta": {
  "script": "audit_sidecar_activation.py",
  "wave": "W3.1"
}
```

This artifact is W3.2 and contains profection activations. The metadata is misleading.

Required fix:

- Update `scripts/audit_sidecar_activation.py` to emit accurate metadata for W3.2 when requested techniques include `annual_profection` or `monthly_profection`.
- Include the requested technique list in `_audit_meta`.
- Regenerate `artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json`.

### P1. Unknown sign ruler silently falls back to Saturn

Current code:

```python
return SIGN_RULERS.get(sign, "SATURN")
```

This hides corrupted or unexpected sign names as Saturn activations.

Required fix:

- Raise a clear `ValueError`/`KeyError` for unknown sign.
- Add a regression test.

### P2. Timezone/local-date boundary is not covered by tests

The TZ explicitly requested timezone/local-date boundary behavior. Current tests cover birthday date boundaries, but not that profection uses the provided target local date as the authoritative local date.

Required fix:

- Add a focused test showing that `target.date` is the local date used for profection boundaries, independent of host timezone.
- The test can use the birthday boundary around `2026-10-29`/`2026-10-30` with a non-Moscow target timezone, as long as the expected local-date behavior is explicit.

## Evidence To Preserve

Do not regress:

- W3.1 transit activations and Moon-Pluto evidence;
- Basil `2026-07-08` W3.2 golden values;
- all sidecar/API schema validation;
- W3.2 artifact count unless the fix intentionally changes only boundary behavior;
- `sidecar_activation_layer=None` in TodayService;
- no firdar/return/progression/eclipse techniques in W3.2 artifact.

## Required Rework

See `03_rework_01_TZ.md`.
