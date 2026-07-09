# Architect Acceptance — W3.4 Returns

Status: ACCEPTED

Accepted scope:

- `solar_return`
- `lunar_return`
- return location policy and structured request contract
- return ActivationEvidence output
- W3.4 audit artifact and deterministic output

Not included:

- W3.5 progressions/solar arc
- eclipse window
- scoring v2
- TodayService sidecar wiring
- frontend
- push/deploy

## Accepted Commits

- `576f93c docs(w3.4): request return activations`
- `b754259 W3.4: solar return + lunar return activations`
- `05cca74 docs(w3.4): finalize report with sha b754259`
- `588a891 docs(w3.4): request rework 01 for returns`
- `b5c8bcd W3.4 Rework 01: fix return location, lunar latest, house_system`
- `f954957 docs(w3.4): finalize rework 01 report with sha b5c8bcd`
- `402ced1 docs(w3.4): request rework 02 for returns`
- `0b8ce6a W3.4 Rework 02: iterative lunar scan, structured location, contract tests`
- `8bce95e docs(w3.4): finalize rework 02 report with sha 0b8ce6a`
- `6713213 docs(w3.4): request rework 03 for returns`
- `6f5660c W3.4 Rework 03: test-contract closure`
- `3190d90 docs(w3.4): finalize rework 03 report with sha 6f5660c`

## Architecture Acceptance

- Return astronomy remains in the sidecar.
- Solar return uses exact Swiss Ephemeris Sun crossing.
- Lunar return iteratively enumerates crossings and selects the latest valid JD at or before target.
- Return houses/ASC/MC use `current_location` when supplied, otherwise birth location with one deterministic warning.
- `current_location` is a typed Pydantic request model.
- Requested house system is explicit; unsupported values fail clearly.
- High-latitude Placidus resolution remains Whole Sign and is exposed in debug.
- Every return activation uses `ActivationEvidence`, stable IDs, deterministic ordering, explicit frames, canon strengths, and valid indexes.
- `TodayService` remains unwired with `sidecar_activation_layer=None`.

## Fresh Architect Verification

```text
sidecar targeted: 96 passed, 1 warning
sidecar full after Rework 03: 121 passed, 1 warning
API targeted: 28 passed
API Rework 03 targeted: 12 passed
API full after Rework 03: 696 passed, 5 skipped, 1 warning
```

Independent runtime probes:

```text
2026-07-16 lunar return:
  function == independent latest == 2461236.9515122585

2026-08-12 lunar return:
  function == independent latest == 2461264.375656118

malformed current_location without lat -> 422
malformed current_location without lon -> 422

equator relocation:
  fallback IDs != relocated IDs
  resolved return house system = PLACIDUS
  no fallback warning
```

Audit artifact:

```text
artifacts/audit/2026-07-08/20_sidecar_activation_layer_w3_4_returns.json
wave: W3.4
total activations: 133
solar_return: 9
lunar_return: 7
fallback warning count: 1
unsupported W3.5/W3.6 activations: 0
```

Hashseed:

```text
d78b174793f34de4d4bdcf7bb28da0b042f7519a97517f0f1d45c0f25a74a7d1
d78b174793f34de4d4bdcf7bb28da0b042f7519a97517f0f1d45c0f25a74a7d1
d78b174793f34de4d4bdcf7bb28da0b042f7519a97517f0f1d45c0f25a74a7d1
```

Other gates:

- artifact regeneration produced no diff;
- required debug fields are present on every return activation;
- `git diff ... --check` passed;
- `git show --check HEAD` passed;
- only pre-existing untracked workspace files remain;
- push/deploy not attempted.

## Decision

W3.4 is accepted. The next implementation wave may build on this contract.
