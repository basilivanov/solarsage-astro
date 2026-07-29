# Reusable TodayFocus Canary Fixtures

## Schema & Format
This directory contains reusable, sanitized test fixtures for `TodayFocus` calculations.

### Factor Fixtures (`factors/`)
Top-level allowlist:
- `fixtureVersion` (string, e.g. `"today-focus-factor.v1"`)
- `caseId` (string, e.g. `"convergence-20260728-a"`)
- `targetDate` (string `YYYY-MM-DD`)
- `timezone` (string IANA timezone, e.g. `"Europe/Moscow"`)
- `factors` (list of sanitized `TodayFactor` dicts)
- `valenceAssessments` (dict of product sphere key -> `{verdict, confidence}`)
- `expected` (dict with `state`, `convergence`, `events`, `featuredSpheres`, `contentState`, `decisionRequired` optional for Case J)

Allowed fields in each factor:
- `factorId`, `activationIds`, `technique`, `techniqueFamily`, `sourceKey`, `targetKey`, `targetType`, `aspectType`, `themeKeys`, `productSpheres`, `polarity`, `strength`, `salience`, `activeFrom`, `exactAt`, `activeUntil`, `phase`, `temporalRole`, `house`

### Public Focus Fixtures (`public/`)
Top-level allowlist:
- `fixtureVersion` (string, e.g. `"today-focus-public.v1"`)
- `caseId` (string, e.g. `"convergence-20260728-a"`)
- `meta` (object containing version info)
- `focus` (object matching `TodayFocusResult` schema)

## Privacy Rules & Denylist
Strictly forbidden across all files in this directory:
`tg`, `telegram`, `username`, `userId`, `UUID`, `birthday`, `coordinates`, `initData`, `cookie`, `token`, `profile`, `prompt`, `response`, raw natal chart data, raw sidecar payload.

Max file size: 64 KB per fixture file.

## Regeneration & Normalization Policy
Run `python3 scripts/contracts/normalize_today_focus_fixture.py apps/api/tests/fixtures/today_focus` to format keys and assert allowlist invariants.
