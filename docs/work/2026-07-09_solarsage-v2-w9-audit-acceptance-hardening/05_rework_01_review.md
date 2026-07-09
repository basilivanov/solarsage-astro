# W9 Rework 01 Architect Review

Status: REWORK REQUIRED
Reviewed commit: `eee6346`
Date: 2026-07-09

## Findings

### P1 — V2-selected payload/cache identity still depends on the frontend flag

Evidence:

- Rework TZ requires V2 selected path to emit:
  - `calculation_version="ss-calc-1.1.0"`
  - `activation_layer_version="al-1.0"`
  - `scoring_version="ss-scoring-2.0"`
  - `payload_version="today.v2"`
  - `frontend_payload_version=2`
- `apps/api/app/services/today_service.py:321-340` detects `v2_selected`, but still sets:
  - `frontend_payload_version=1` when `settings.solarsage_v2_frontend_enabled` is false;
  - `payload_version="today.v1"` when `settings.solarsage_v2_frontend_enabled` is false.
- Existing new regression only covers V1-only mode (`test_v1_only_payload_and_cache_identity_not_polluted_by_v2_calc`). It does not cover `SOLARSAGE_V2_ENABLED=true` with `SOLARSAGE_V2_FRONTEND_ENABLED=false`.

Impact:

A run can select V2 scoring (`ss-scoring-2.0`) while the payload/cache identity still claims `today.v1` and frontend payload version `1`. That contradicts W9's version-identity contract and can create misleading cache/debug/audit evidence for a real V2 production payload.

Required fix:

When `v2_selected` is true, force the V2 identity regardless of the frontend flag:

- `calculation_version="ss-calc-1.1.0"`
- `activation_layer_version="al-1.0"`
- `scoring_version="ss-scoring-2.0"`
- `payload_version="today.v2"`
- `frontend_payload_version=2`

Add regression coverage for a V2-selected path where:

- `settings.solarsage_v2_enabled=True`;
- `settings.solarsage_v2_frontend_enabled=False`;
- returned `TodayPayload.meta` still has `payload_version="today.v2"` and `frontend_payload_version=2`;
- cache key write identity matches those meta fields.

Keep the V1-only regression from Rework 01.

## Checks

Already verified after Rework 01:

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Result: both passed.

The previous P0 whitespace issue and frozen-baseline payload issue are not reopened. Rework 02 should only address the V2-selected identity gap above plus evidence/report updates.

## Decision

W9 remains not accepted at `eee6346`.
