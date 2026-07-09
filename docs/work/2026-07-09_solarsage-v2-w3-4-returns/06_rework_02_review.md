# Architect Review — W3.4 Rework 02

Status: REWORK REQUIRED

Reviewed:

- `8bce95e docs(w3.4): finalize rework 02 report with sha 0b8ce6a`
- implementation commit: `0b8ce6a W3.4 Rework 02: iterative lunar scan, structured location, contract tests`

## What Is Accepted In Code Behavior

The main runtime blockers are fixed:

- lunar return now uses iterative crossing enumeration;
- `2026-08-12` now returns latest JD `2461264.375656118`;
- malformed `current_location` missing `lat` or `lon` returns 422 in manual endpoint probe;
- relocation changes return activation IDs and resolves equator as `PLACIDUS`;
- sidecar/API full suites pass in architect verification.

Fresh architect verification already run:

```text
sidecar targeted: 96 passed, 1 warning
sidecar full: 117 passed, 1 warning
API targeted: 28 passed
API full: 695 passed, 5 skipped, 1 warning
audit artifact: 133 activations, W3.4
hashseed: d78b174793f34de4d4bdcf7bb28da0b042f7519a97517f0f1d45c0f25a74a7d1 x3
```

## Finding 1 — P1: malformed `current_location` behavior is not covered by tests

Rework 02 required tests:

```text
valid current_location still works;
malformed current_location missing lat or lon returns request validation error, not internal 500.
```

Runtime behavior is correct in manual probe:

```text
{'lon': 0.0, 'tz': 'UTC'} -> 422
{'lat': 0.0, 'tz': 'UTC'} -> 422
```

But no committed test currently asserts this. Search confirms `current_location` tests cover valid relocation, not malformed request validation.

## Finding 2 — P1: no regression test asserts TodayService remains unwired

The report and grep prove:

```text
apps/api/app/services/today_service.py:245 sidecar_activation_layer=None
```

But Rework 02 required a test/invariant for this no-wiring contract. Add a focused API test so future work cannot silently wire sidecar activation layer during W3.4.

## Review Decision

Return for Rework 03. This should be test/report only unless adding the tests exposes a real code issue.
