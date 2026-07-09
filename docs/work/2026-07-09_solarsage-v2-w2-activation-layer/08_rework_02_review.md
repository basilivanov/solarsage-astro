# Architect Review: Wave W2 Rework 02

Status: REWORK REQUIRED

Reviewed commit:

- `3921fef` — W2 Rework 02 behavioral TodayService mock tests

## Summary

Rework 02 removed the `inspect.getsource(...)` assertion and added runtime tests. That is the right direction.

However, the fresh/full TodayService test still does not fully prove the W2 contract from `06_rework_02_TZ.md`:

- it can still depend on a live sidecar through `NatalContextService`;
- it does not control the normalized signal list used by TodayService;
- it does not strictly prove the `ScoringService.score_day(...)` call shape;
- it leaves unused/stale test data that suggests the intended natal mock is not actually used.

Targeted tests pass, but the test evidence is still weaker than the acceptance gate.

## Evidence

Architect rerun:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_meta_versions.py tests/test_activation_layer_contract.py tests/test_day_endpoints.py -q
```

Result:

```text
19 passed, 1 warning in 0.64s
```

Architect grep:

```bash
rg -n "mock_natal_data|NatalContextService|score_day\.assert_called_once|call_args|len\(call_args\)" apps/api/tests/test_today_meta_versions.py
```

Relevant current assertions:

```python
call_args, call_kwargs = mock_scoring.score_day.call_args
assert len(call_args) >= 1
assert isinstance(call_args[0], list)
assert "activation_layer" not in call_kwargs
```

This allows extra positional arguments, multiple calls, and wrong signal contents.

## Blocking Findings

### P1. Fresh/full test still leaks live natal-context behavior

`TodayService` calls:

```python
context_service = NatalContextService(self.db)
natal_context = await context_service.get_or_build_natal_context(user_id)
```

Current test only patches:

```python
patch("app.services.today_service.get_solarsage_client")
```

That does not patch `app.services.natal_context_service.get_solarsage_client`, and it does not patch `NatalContextService.get_or_build_natal_context`.

The test also defines `mock_natal_data`, but this data is not used by the TodayService path being tested. This means the behavioral test can accidentally depend on the sidecar/systemd runtime or an existing natal cache instead of a deterministic test fixture.

Required fix:

- Patch `app.services.today_service.NatalContextService.get_or_build_natal_context` to return a valid `NatalContextData`, or pre-seed a valid `NatalChartCache` and prove no sidecar natal call is used.
- Prefer direct patching of `NatalContextService.get_or_build_natal_context` for this unit-level service contract.
- Remove unused `mock_natal_data`.

### P1. Scoring input guard is too weak

Rework 02 TZ required proving:

- `ScoringService.score_day(...)` is called exactly once;
- it receives exactly the day-scored transit signal list;
- it receives no `activation_layer` positional or keyword argument.

Current test only checks:

```python
len(call_args) >= 1
isinstance(call_args[0], list)
"activation_layer" not in call_kwargs
```

This would still pass if scoring received:

- extra positional args;
- an unfiltered all-signals list with static natal background;
- multiple calls;
- a wrong transit list.

Required fix:

- Use deterministic `AstroSignal` fixtures by patching `NormalizationService.normalize_day(...)`.
- Include at least:
  - `Transit_Moon` aspect to natal `Pluto`;
  - `Transit_Mars` planet-in-house;
  - one static/non-transit background signal that must not reach scoring.
- Patch `TodayService._get_yesterday_signals` to return `None` or `[]` so `DayDeltaService` does not rewrite the fixture list.
- Assert:
  - `mock_scoring.score_day.call_count == 1`;
  - `len(call_args) == 1`;
  - `call_kwargs == {}`;
  - `call_args[0]` equals the expected day-scored transit-only signal list;
  - no activation layer is passed as positional or keyword scoring input.

### P2. Rework 02 report does not include required broader gate results

`06_rework_02_TZ.md` asked to run broader W2 gates after the focused command set is clean. The report only lists:

- `pytest apps/api/tests/test_today_meta_versions.py -q`;
- `pytest apps/api/tests/ -q`.

Required fix:

- After test corrections, run and report the exact required gates from the new rework TZ.

## Required Rework

See `09_rework_03_TZ.md`.
