# Architect Review: Rework 08

Status: REWORK REQUIRED

Branch: main
Reviewed commit: 1ba6101638d166ff6637cc93b22ed81bcd22d897

## Summary

Rework 08 fixed the previous live-output isolation issue for the W0 audit harness. The targeted W0 gates pass, including `make audit-day`, oracle comparison, canonical artifact stability, and live mode isolation.

However, W0 cannot be accepted yet because the full canonical backend suite from `apps/api` is not green. The failures are contract fallout from the W0 retrograde hardening and one test import path issue.

## Blocking Findings

### P0. Full API suite is red after W0 schema hardening

Command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Observed result:

```text
10 failed, 613 passed, 5 skipped, 26 errors
```

The dominant failure class is:

```text
pydantic_core.ValidationError: retrograde Field required
```

Examples:

- `apps/api/tests/test_natal_report_service.py:74`
- `apps/api/tests/test_natal_report_service.py:107`
- `apps/api/tests/test_natal_report_service.py:733`
- `apps/api/tests/test_natal_report_service.py:809`
- `apps/api/tests/test_natal_report_service.py:884`
- `apps/api/tests/test_natal_report_service.py:1101`
- `apps/api/tests/test_natal_report_service.py:1183`

Root cause:

W0 correctly changed `NatalChartPlanet.retrograde` / `NatalPreviewChartPlanet.retrograde` from silent default `False` to required. Old test fixtures still construct `NatalChartPlanet(...)` without `retrograde`, so they now fail at setup.

Architectural decision:

Do not weaken the schema back to `retrograde: bool = False`. W0 explicitly requires that audited paths never silently mask missing retrograde as false. Update fixtures/tests to carry explicit retrograde values.

### P0. Sidecar validation tests still use old planet fixtures without speed/retrograde

Failing example:

```text
apps/api/tests/test_natal_context_service.py::TestSidecarValidation::test_solar_sage_natal_accepts_valid_response
Value error, Both retrograde and speed are missing
```

Root cause:

`SolarSagePlanetPosition` and `SolarSageTransitPlanet` now correctly reject sidecar planets when both `retrograde` and `speed` are missing. Old tests still define "valid" sidecar payloads without either field.

Architectural decision:

Keep the strict validator. Update valid fixtures to include either:

- explicit `retrograde`; or
- `speed`, proving derivation works.

For rejection tests that are supposed to assert empty houses/planets, make the non-target fields valid enough that the intended validation error is reached.

### P1. New audit helper unit tests only pass from repository root

Failing command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_default tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_live -q -vv
```

Observed result:

```text
ModuleNotFoundError: No module named 'scripts'
```

Root cause:

The tests import `from scripts.audit_today import resolve_audit_output_dirs`, which works when pytest is launched from repo root, but not from canonical API cwd `apps/api`.

Architectural decision:

Fix the test import path or load the script module by absolute path from repo root. The canonical backend test command must work from `apps/api`.

### P2. Cleanup: duplicate/unused imports in `scripts/audit_today.py`

Observed:

```python
from typing import Any
from typing import Any, NamedTuple
from dataclasses import dataclass, field
```

`NamedTuple` and `field` are unused, and `Any` is imported twice. This is not the root cause of the red suite, but clean it up in the same rework.

## Passing Evidence From Review

The following W0-specific gates passed before the full-suite failure was found:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

Result:

```text
43 passed, 1 warning
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py tests/test_services.py -q
```

Result:

```text
5 passed
```

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Result: exit code 0.

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Result: exit code 0, no canonical artifact diff.

```bash
apps/api/.venv/bin/python scripts/audit_today.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --out artifacts/audit/2026-07-08 \
  --live-llm-sample
git diff --exit-code -- artifacts/audit/2026-07-08
```

Result: exit code 0, live output isolated under `artifacts/audit/2026-07-08/live/<timestamp>/`, no canonical diff. Temporary live output was removed after review.

```bash
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' \
  artifacts/audit/2026-07-08/14_claims_audit.md \
  artifacts/audit/2026-07-08/11_final_today_payload.json
```

Result: exit code 1, no forbidden fallback strings.

## Required Rework

See `27_rework_09_TZ.md`.
